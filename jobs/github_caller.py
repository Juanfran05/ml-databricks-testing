# Databricks notebook source
"""_summary_
"""
import requests
import logging
import json
import os


to_stage = json.loads(dbutils.widgets.get("event_message"))["to_stage"]
choosen_env = to_stage.lower()
model_name = json.loads(dbutils.widgets.get("event_message"))["model_name"]
model_version = json.loads(dbutils.widgets.get("event_message"))["version"]


def compliance_checks_approved(model_name, model_version):
    """_summary_

    Args:
        model_name (_type_): _description_
        model_version (_type_): _description_
    """
    return True


def promote_to_staging(name, version):
    job_payload = {
        "name": name,
        "version": version,
        "stage": "Staging",
        "archive_existing_versions": False,
        "comment": "Staging version of this model",
    }

    resp = requests.post(
        f'{dbutils.secrets.get(scope="modelregistery", key="modelregistery-host")}api/2.0/mlflow/databricks/model-versions/transition-stage',
        json=job_payload,
        headers={
            "Authorization": f'Bearer {dbutils.secrets.get(scope="modelregistery", key="modelregistery-token")}'
        },
    )

    print(resp.status_code)


def load_current_production_model(model_name):
    job_payload = {"filter": f"name='{model_name}'"}

    resp = requests.get(
        f'{dbutils.secrets.get(scope="modelregistery", key="modelregistery-host")}api/2.0/mlflow/model-versions/search',
        json=job_payload,
        headers={
            "Authorization": f'Bearer {dbutils.secrets.get(scope="modelregistery", key="modelregistery-token")}'
        },
    )

    list_model_in_prod_versions = []
    list_model_in_prod_cretion = []
    for elem in json.loads(resp.text)["model_versions"]:
        if elem["current_stage"] == "Production":
            list_model_in_prod_versions.append(elem["version"])
            # list_model_in_staging_cretion.append(elem["last_updated_timestamp"])
            list_model_in_prod_cretion.append(elem["creation_timestamp"])

    index_last_model = list_model_in_prod_cretion.index(max(list_model_in_prod_cretion))
    last_model_version = list_model_in_prod_versions[index_last_model]

    return last_model_version


def test_against_current_production(model_name, model_version):
    model = load_current_production_model(model_name)
    pass


def request_to_prod_transition(name, version):
    job_payload = {
        "name": name,
        "version": version,
        "stage": "Production",
        "comment": "Production version of this model",
    }

    resp = requests.post(
        f'{dbutils.secrets.get(scope="modelregistery", key="modelregistery-host")}api/2.0/mlflow/transition-requests/create',
        json=job_payload,
        headers={
            "Authorization": f'Bearer {dbutils.secrets.get(scope="modelregistery", key="modelregistery-token")}'
        },
    )

    print(resp.status_code)


def archived_model(name, version):
    job_payload = {
        "name": name,
        "version": version,
        "stage": "Archived",
        "comment": "Staging version of this model",
    }

    resp = requests.post(
        f'{dbutils.secrets.get(scope="modelregistery", key="modelregistery-host")}api/2.0/mlflow/databricks/model-versions/transition-stage',
        json=job_payload,
        headers={
            "Authorization": f'Bearer {dbutils.secrets.get(scope="modelregistery", key="modelregistery-token")}'
        },
    )

    print(resp.status_code)


if choosen_env == "staging":
    """
    # Call github from databrick job

    job_payload = {
        "ref": "main",
        "inputs": {
            "choosenEnv": choosen_env,
            "stageChangeRequested": "true",
            "modelName": model_name,
            "modelVersion": model_version,
            "toStage": to_stage,
        },
    }
    resp = requests.post(
        "https://api.github.com/repos/lgriva-ext/ml_solution/actions/workflows/cd_databricks_staging.yml/dispatches",
        json=job_payload,
        headers={
            "Authorization": f'Bearer {dbutils.secrets.get(scope="github", key="github-token")}'
        },
    )

    print(resp.status_code)
    """
    # Run compliance checks before approve "to Staging" transition
    logging.info("Running compliance checks")
    if compliance_checks_approved(model_name, model_version):
        logging.info(
            f"Promoting model {model_name}, version {model_version} to Staging"
        )
        promote_to_staging(model_name, model_version)
        logging.info("Test registered model against last production registered model")
        to_prod_stage = test_against_current_production(model_name, model_version)
        if to_prod_stage:
            request_to_prod_transition(model_name, model_version)
        else:
            logging.info(
                "Model accuracy is not better than current production model accuracy, it will be archived"
            )
            archived_model(model_name, model_version)
    else:
        logging.info("Model did not pass compliance checks, it will be archived")
        archived_model(model_name, model_version)
