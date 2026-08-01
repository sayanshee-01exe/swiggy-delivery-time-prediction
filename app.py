# from fastapi import FastAPI
# from pydantic import BaseModel
# from requests import get
# from sklearn.pipeline import Pipeline
# import uvicorn
# import pandas as pd
# import mlflow
# import json
# import joblib
# from mlflow import MlflowClient
# from sklearn import set_config
# from scripts.data_clean_utils import perform_data_cleaning

# # set the output as pandas
# set_config(transform_output='pandas')

# # initialize dagshub
# import dagshub
# import mlflow.client

# dagshub.init(repo_owner='sayanshee-01exe', 
#              repo_name='swiggy-delivery-time-prediction', 
#              mlflow=True)

# # set the mlflow tracking server
# mlflow.set_tracking_uri("https://dagshub.com/sayanshee-01exe/swiggy-delivery-time-prediction.mlflow")


# class Data(BaseModel): 
#     age: int
#     ratings: float
#     pickup_time_minutes: int
#     distance: float
#     distance_type: str
#     order_time_of_day: str
#     is_weekend: int
#     weather: str
#     traffic: str
#     vehicle_condition: int
#     type_of_order: str
#     type_of_vehicle: str
#     multiple_deliveries: int
#     festival: str
#     city_type: str

    
    
# def load_model_information(file_path):
#     with open(file_path) as f:
#         run_info = json.load(f)
        
#     return run_info


# def load_transformer(transformer_path):
#     transformer = joblib.load(transformer_path)
#     return transformer



# # columns to preprocess in data
# num_cols = ["age",
#             "ratings",
#             "pickup_time_minutes",
#             "distance"]

# nominal_cat_cols = ['weather',
#                     'type_of_order',
#                     'type_of_vehicle',
#                     "festival",
#                     "city_type",
#                     "is_weekend",
#                     "order_time_of_day"]

# ordinal_cat_cols = ["traffic","distance_type"]

# # mlflow client
# client = MlflowClient()

# # load model information
# run_info = load_model_information("run_information.json")

# # registered model name
# model_name = run_info["registered_model_name"]

# # model alias
# alias = "candidate"

# # model registry path
# model_path = f"models:/{model_name}@{alias}"

# # load model from registry
# model = mlflow.sklearn.load_model(model_path)

# # #mlflow client
# # client = MlflowClient()

# # # load the model info to get the model name
# # model_name = load_model_information("run_information.json")['registered_model_name']
# # # stage of the model
# # # load registered model using alias
# # alias = "candidate"

# # model_path = f"models:/{model_name}@{alias}"

# # model = mlflow.sklearn.load_model(model_path)

# # load the preprocessor
# preprocessor_path = "models/preprocessor.joblib"
# preprocessor = load_transformer(preprocessor_path)

# # build the model pipeline
# model_pipe = Pipeline(steps=[
#     ('preprocess',preprocessor),
#     ("regressor",model)
# ])

# # create the app
# app = FastAPI()

# # create the home endpoint
# @app.get(path="/")
# def home():
#     return "Welcome to the Swiggy Food Delivery Time Prediction App"

# # create the predict endpoint
# @app.post(path="/predict")
# def do_predictions(data: Data):
#     pred_data = pd.DataFrame({
#         'age': data.age,
#         'ratings': data.ratings,
#         'pickup_time_minutes': data.pickup_time_minutes,
#         'distance': data.distance,
#         'distance_type': data.distance_type,
#         'order_time_of_day': data.order_time_of_day,
#         'is_weekend': data.is_weekend,
#         'weather': data.weather,
#         'traffic': data.traffic,
#         'vehicle_condition': data.vehicle_condition,
#         'type_of_order': data.type_of_order,
#         'type_of_vehicle': data.type_of_vehicle,
#         'multiple_deliveries': data.multiple_deliveries,
#         'festival': data.festival,
#         'city_type': data.city_type
#         },index=[0]
#     )
#     # clean the raw input data
#     cleaned_data = perform_data_cleaning(pred_data)
#     # get the predictions
#     predictions = model_pipe.predict(cleaned_data)[0]
#     return predictions

# if __name__ == "__main__":
#     uvicorn.run(app="app:app",host="0.0.0.0",port=8000)



# raw, dirty data

from fastapi import FastAPI
from pydantic import BaseModel
from sklearn.pipeline import Pipeline
import uvicorn
import pandas as pd
import mlflow
import json
import joblib
from mlflow import MlflowClient
from sklearn import set_config
from scripts.data_clean_utils import perform_data_cleaning
from fastapi import FastAPI, HTTPException

# set the output as pandas
set_config(transform_output='pandas')

# initialize dagshub
import dagshub
import mlflow.client

dagshub.init(repo_owner='sayanshee-01exe', 
             repo_name='swiggy-delivery-time-prediction', 
             mlflow=True)

# set the mlflow tracking server
mlflow.set_tracking_uri("https://dagshub.com/sayanshee-01exe/swiggy-delivery-time-prediction.mlflow")


class Data(BaseModel):  
    ID: str
    Delivery_person_ID: str
    Delivery_person_Age: str
    Delivery_person_Ratings: str
    Restaurant_latitude: float
    Restaurant_longitude: float
    Delivery_location_latitude: float
    Delivery_location_longitude: float
    Order_Date: str
    Time_Orderd: str
    Time_Order_picked: str
    Weatherconditions: str
    Road_traffic_density: str
    Vehicle_condition: int
    Type_of_order: str
    Type_of_vehicle: str
    multiple_deliveries: str
    Festival: str
    City: str

    
    
def load_model_information(file_path):
    with open(file_path) as f:
        run_info = json.load(f)
        
    return run_info


def load_transformer(transformer_path):
    transformer = joblib.load(transformer_path)
    return transformer



# columns to preprocess in data
num_cols = ["age",
            "ratings",
            "pickup_time_minutes",
            "distance"]

nominal_cat_cols = ['weather',
                    'type_of_order',
                    'type_of_vehicle',
                    "festival",
                    "city_type",
                    "is_weekend",
                    "order_time_of_day"]

ordinal_cat_cols = ["traffic","distance_type"]

# mlflow client
client = MlflowClient()

# load model information
run_info = load_model_information("run_information.json")

# registered model name
model_name = run_info["registered_model_name"]

# model alias
alias = "candidate"

# model registry path
model_path = f"models:/{model_name}@{alias}"

# load model from registry
model = mlflow.sklearn.load_model(model_path)

# load the preprocessor
preprocessor_path = "models/preprocessor.joblib"
preprocessor = load_transformer(preprocessor_path)

# build the model pipeline
model_pipe = Pipeline(steps=[
    ('preprocess',preprocessor),
    ("regressor",model)
])

# create the app
app = FastAPI()

# create the home endpoint
@app.get(path="/")
def home():
    return "Welcome to the Swiggy Food Delivery Time Prediction App"

# create the predict endpoint
@app.post(path="/predict")
def do_predictions(data: Data):
    pred_data = pd.DataFrame({
        'ID': data.ID,
        'Delivery_person_ID': data.Delivery_person_ID,
        'Delivery_person_Age': data.Delivery_person_Age,
        'Delivery_person_Ratings': data.Delivery_person_Ratings,
        'Restaurant_latitude': data.Restaurant_latitude,
        'Restaurant_longitude': data.Restaurant_longitude,
        'Delivery_location_latitude': data.Delivery_location_latitude,
        'Delivery_location_longitude': data.Delivery_location_longitude,
        'Order_Date': data.Order_Date,
        'Time_Orderd': data.Time_Orderd,
        'Time_Order_picked': data.Time_Order_picked,
        'Weatherconditions': data.Weatherconditions,
        'Road_traffic_density': data.Road_traffic_density,
        'Vehicle_condition': data.Vehicle_condition,
        'Type_of_order': data.Type_of_order,
        'Type_of_vehicle': data.Type_of_vehicle,
        'multiple_deliveries': data.multiple_deliveries,
        'Festival': data.Festival,
        'City': data.City
        },index=[0]
    )
    cleaned_data = perform_data_cleaning(pred_data)

    if cleaned_data.empty:
        raise HTTPException(
        status_code=400,
        detail="Input row is invalid after data cleaning"
    )

    predictions = model_pipe.predict(cleaned_data)[0]

    return {"prediction": predictions}

if __name__ == "__main__":
    uvicorn.run(app="app:app",host="0.0.0.0",port=8000)