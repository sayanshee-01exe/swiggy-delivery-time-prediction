# import pytest
# import mlflow
# from mlflow import MlflowClient
# import dagshub
# import json

# dagshub.init(repo_owner='sayanshee-01exe', 
#              repo_name='swiggy-delivery-time-prediction', 
#              mlflow=True)

# # set the mlflow tracking server
# mlflow.set_tracking_uri("https://dagshub.com/sayanshee-01exe/swiggy-delivery-time-prediction.mlflow")


# def load_model_information(file_path):
#     with open(file_path) as f:
#         run_info = json.load(f)
        
#     return run_info

# # set model name
# model_name = load_model_information("run_information.json")["registered_model_name"]



# @pytest.mark.parametrize(argnames="model_name, stage",
#                          argvalues=[(model_name, "Staging")])
# def test_load_model_from_registry(model_name,stage):
#     client = MlflowClient()
#     latest_versions = client.get_latest_versions(name=model_name,stages=[stage])
#     latest_version = latest_versions[0].version if latest_versions else None
    
#     assert latest_version is not None, f"No model at {stage} stage"
    
#     # load the model
#     model_path = f"models:/{model_name}/{stage}"

#     # load the latest model from model registry
#     model = mlflow.sklearn.load_model(model_path)
    
#     assert model is not None, "Failed to load model from registry"
#     print(f"The {model_name} model with version {latest_version} was loaded successfully")
    



import pytest
import mlflow
import dagshub
import json
from mlflow import MlflowClient


dagshub.init(
    repo_owner="sayanshee-01exe",
    repo_name="swiggy-delivery-time-prediction",
    mlflow=True
)

mlflow.set_tracking_uri(
    "https://dagshub.com/"
    "sayanshee-01exe/"
    "swiggy-delivery-time-prediction.mlflow"
)


def load_model_information(file_path):
    with open(file_path) as f:
        return json.load(f)


run_info = load_model_information("run_information.json")

model_name = run_info["registered_model_name"]


@pytest.mark.parametrize(
    "model_name, alias",
    [(model_name, "candidate")]
)
def test_load_model_from_registry(model_name, alias):

    client = MlflowClient()

    model_version = client.get_model_version_by_alias(
        name=model_name,
        alias=alias
    )

    assert model_version is not None, (
        f"No model found with alias '{alias}'"
    )

    model_path = f"models:/{model_name}@{alias}"

    model = mlflow.sklearn.load_model(model_path)

    assert model is not None, (
        "Failed to load model from registry"
    )

    print(
        f"{model_name} version {model_version.version} "
        f"with alias '{alias}' loaded successfully"
    )