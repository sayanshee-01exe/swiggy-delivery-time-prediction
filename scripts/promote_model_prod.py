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
    "https://dagshub.com/sayanshee-01exe/"
    "swiggy-delivery-time-prediction.mlflow"
)


def load_model_information(file_path):
    with open(file_path) as f:
        return json.load(f)


# load model information
run_info = load_model_information("run_information.json")

# registered model name
model_name = run_info["registered_model_name"]

# create MLflow client
client = MlflowClient()

# get the model currently marked as candidate
candidate_model = client.get_model_version_by_alias(
    name=model_name,
    alias="candidate"
)

candidate_version = candidate_model.version

print(
    f"Candidate model version: {candidate_version}"
)

# promote candidate to champion
client.set_registered_model_alias(
    name=model_name,
    alias="champion",
    version=candidate_version
)

# optional tag
client.set_model_version_tag(
    name=model_name,
    version=candidate_version,
    key="deployment_status",
    value="production"
)

print(
    f"Model '{model_name}' version {candidate_version} "
    f"promoted to champion"
)