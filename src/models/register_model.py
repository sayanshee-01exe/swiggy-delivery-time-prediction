import json
import logging
from pathlib import Path

import dagshub
import mlflow
from mlflow import MlflowClient


# ---------------------------
# Logger configuration
# ---------------------------
logger = logging.getLogger("register_model")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# ---------------------------
# DagsHub / MLflow setup
# ---------------------------
dagshub.init(
    repo_owner="sayanshee-01exe",
    repo_name="swiggy-delivery-time-prediction",
    mlflow=True,
)

MLFLOW_TRACKING_URI = (
    "https://dagshub.com/"
    "sayanshee-01exe/"
    "swiggy-delivery-time-prediction.mlflow"
)

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def load_model_information(file_path: Path) -> dict:
    """Load MLflow run information from JSON."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Run information file not found: {file_path}"
        )

    with file_path.open("r") as file:
        return json.load(file)


def register_model(
    model_uri: str,
    registered_model_name: str,
):
    """Register an already logged MLflow model."""

    logger.info("Registering model from URI: %s", model_uri)

    model_version = mlflow.register_model(
        model_uri=model_uri,
        name=registered_model_name,
    )

    return model_version


if __name__ == "__main__":
    root_path = Path(__file__).resolve().parents[2]

    run_info_path = root_path / "run_information.json"

    run_info = load_model_information(run_info_path)

    model_uri = run_info["model_uri"]
    registered_model_name = run_info["registered_model_name"]

    model_version = register_model(
        model_uri=model_uri,
        registered_model_name=registered_model_name,
    )

    version = str(model_version.version)

    logger.info(
        "Registered model '%s' as version %s",
        registered_model_name,
        version,
    )

    client = MlflowClient()

    client.set_registered_model_alias(
        name=registered_model_name,
        alias="candidate",
        version=version,
    )

    client.set_model_version_tag(
        name=registered_model_name,
        version=version,
        key="validation_status",
        value="pending",
    )

    logger.info(
        "Alias 'candidate' assigned to model version %s",
        version,
    )