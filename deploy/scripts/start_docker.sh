# #!/bin/bash
# # Log everything to start_docker.log
# exec > /home/ubuntu/start_docker.log 2>&1

# echo "Logging in to ECR..."
# aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 891377050051.dkr.ecr.ap-south-1.amazonaws.com

# echo "Pulling Docker image..."
# docker pull 891377050051.dkr.ecr.ap-south-1.amazonaws.com/food_delivery_time_prediction:latest

# echo "Checking for existing container..."
# if [ "$(docker ps -q -f name=delivery_time_pred)" ]; then
#     echo "Stopping existing container..."
#     docker stop delivery_time_pred
# fi

# if [ "$(docker ps -aq -f name=delivery_time_pred)" ]; then
#     echo "Removing existing container..."
#     docker rm delivery_time_pred
# fi

# echo "Starting new container..."
# docker run -d -p 80:8000 --name delivery_time_pred -e DAGSHUB_USER_TOKEN=0b44756fc3f18f453afbddad59dec563ff9e691c 891377050051.dkr.ecr.ap-south-1.amazonaws.com/food_delivery_time_prediction:latest

# echo "Container started successfully." 


#!/bin/bash
set -e

exec > /home/ubuntu/start_docker.log 2>&1

AWS_REGION="ap-southeast-2"
AWS_ACCOUNT_ID="241077340105"
ECR_REPOSITORY="swiggy-delivery-time-prediction"

IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"

echo "Logging in to ECR..."

aws ecr get-login-password --region "$AWS_REGION" | \
docker login \
  --username AWS \
  --password-stdin \
  "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Pulling Docker image..."
docker pull "$IMAGE"

echo "Removing existing container..."
docker rm -f delivery_time_pred 2>/dev/null || true

echo "Starting new container..."
docker run -d \
  --name delivery_time_pred \
  -p 8000:8000 \
  "$IMAGE"

echo "Container started successfully"
docker ps