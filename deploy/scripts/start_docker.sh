#!/bin/bash
set -e

exec > /home/ubuntu/start_docker.log 2>&1

AWS_REGION="ap-southeast-2"
AWS_ACCOUNT_ID="241077340105"
ECR_REPOSITORY="swiggy-delivery-time-prediction"

IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"

echo "Getting DagsHub token from Parameter Store..."

DAGSHUB_USER_TOKEN=$(aws ssm get-parameter \
  --name "/swiggy/dagshub-token" \
  --with-decryption \
  --region us-east-1 \
  --query "Parameter.Value" \
  --output text)

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
  -p 8001:8001 \
  -e DAGSHUB_USER_TOKEN="$DAGSHUB_USER_TOKEN" \
  "$IMAGE"

echo "Container started successfully"

docker ps