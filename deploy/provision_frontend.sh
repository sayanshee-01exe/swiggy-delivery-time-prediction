#!/usr/bin/env bash
#
# Provisions the v1 frontend hosting: a private S3 bucket for the SPA and one
# CloudFront distribution that serves it AND forwards /api/* to the EC2 API.
#
# Why both live behind one distribution:
#   * A page served over HTTPS cannot call http://<ec2-ip>:8001 -- browsers
#     block it as mixed active content, and JavaScript cannot work around it.
#     CloudFront terminates TLS and talks plain HTTP to the origin.
#   * Sharing an origin means there is no CORS configuration to get wrong.
#   * The default *.cloudfront.net certificate is free, so no ACM cert,
#     no Route 53 and no domain are needed for v1.
#
# NOT runnable with the sayan-dvc-user credentials: that user is denied
# cloudfront:* and ec2:*. Run this with an administrative profile.
#
# Usage:
#   SPA_BUCKET=swiggy-delivery-frontend-241077340105 \
#   EC2_ORIGIN_DOMAIN=ec2-1-2-3-4.compute-1.amazonaws.com \
#   AWS_PROFILE=admin \
#   ./deploy/provision_frontend.sh
#
set -euo pipefail

: "${SPA_BUCKET:?set SPA_BUCKET to the (globally unique) bucket name}"
: "${EC2_ORIGIN_DOMAIN:?set EC2_ORIGIN_DOMAIN to the instance public DNS}"
BUCKET_REGION="${BUCKET_REGION:-us-east-1}"
API_PORT="${API_PORT:-8001}"

# AWS-managed policy ids (stable, documented by AWS)
CACHE_OPTIMIZED="658327ea-f89d-4fab-a63d-7e88639e58f6"
CACHE_DISABLED="4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
# forwards everything except Host; a custom origin should see its own Host
ORIGIN_REQ_ALL_VIEWER_EXCEPT_HOST="b689b0a8-53d0-40ab-baf2-68738e2966ac"

echo "==> 1/5 creating private bucket ${SPA_BUCKET}"
if aws s3api head-bucket --bucket "$SPA_BUCKET" 2>/dev/null; then
  echo "    already exists, skipping"
else
  if [ "$BUCKET_REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$SPA_BUCKET" --region us-east-1
  else
    aws s3api create-bucket --bucket "$SPA_BUCKET" --region "$BUCKET_REGION" \
      --create-bucket-configuration "LocationConstraint=$BUCKET_REGION"
  fi
fi

# The bucket is never public: CloudFront reaches it through an Origin Access
# Control, so objects are only readable via the distribution.
aws s3api put-public-access-block --bucket "$SPA_BUCKET" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "==> 2/5 creating origin access control"
OAC_ID=$(aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='${SPA_BUCKET}-oac'].Id | [0]" \
  --output text 2>/dev/null || echo "None")

if [ "$OAC_ID" = "None" ] || [ -z "$OAC_ID" ]; then
  OAC_ID=$(aws cloudfront create-origin-access-control \
    --origin-access-control-config "Name=${SPA_BUCKET}-oac,Description=SPA access,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3" \
    --query 'OriginAccessControl.Id' --output text)
fi
echo "    OAC: $OAC_ID"

echo "==> 3/5 creating distribution (S3 default + /api/* to EC2:${API_PORT})"
CONFIG=$(cat <<JSON
{
  "CallerReference": "swiggy-frontend-$(date +%s)",
  "Comment": "Swiggy delivery time predictor - SPA + API",
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 2,
    "Items": [
      {
        "Id": "spa-s3",
        "DomainName": "${SPA_BUCKET}.s3.${BUCKET_REGION}.amazonaws.com",
        "OriginAccessControlId": "${OAC_ID}",
        "S3OriginConfig": { "OriginAccessIdentity": "" }
      },
      {
        "Id": "api-ec2",
        "DomainName": "${EC2_ORIGIN_DOMAIN}",
        "CustomOriginConfig": {
          "HTTPPort": ${API_PORT},
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only",
          "OriginSslProtocols": { "Quantity": 1, "Items": ["TLSv1.2"] },
          "OriginReadTimeout": 60
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "spa-s3",
    "ViewerProtocolPolicy": "redirect-to-https",
    "CachePolicyId": "${CACHE_OPTIMIZED}",
    "Compress": true,
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"] }
    }
  },
  "CacheBehaviors": {
    "Quantity": 1,
    "Items": [
      {
        "PathPattern": "/api/*",
        "TargetOriginId": "api-ec2",
        "ViewerProtocolPolicy": "redirect-to-https",
        "CachePolicyId": "${CACHE_DISABLED}",
        "OriginRequestPolicyId": "${ORIGIN_REQ_ALL_VIEWER_EXCEPT_HOST}",
        "Compress": true,
        "AllowedMethods": {
          "Quantity": 7,
          "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"],
          "CachedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"] }
        }
      }
    ]
  },
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      { "ErrorCode": 403, "ResponseCode": "200", "ResponsePagePath": "/index.html", "ErrorCachingMinTTL": 10 },
      { "ErrorCode": 404, "ResponseCode": "200", "ResponsePagePath": "/index.html", "ErrorCachingMinTTL": 10 }
    ]
  }
}
JSON
)

DIST=$(aws cloudfront create-distribution --distribution-config "$CONFIG")
DIST_ID=$(echo "$DIST" | python3 -c 'import json,sys; print(json.load(sys.stdin)["Distribution"]["Id"])')
DIST_DOMAIN=$(echo "$DIST" | python3 -c 'import json,sys; print(json.load(sys.stdin)["Distribution"]["DomainName"])')

echo "==> 4/5 granting the distribution read access to the bucket"
aws s3api put-bucket-policy --bucket "$SPA_BUCKET" --policy "$(cat <<JSON
{
  "Version": "2008-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontServicePrincipalReadOnly",
    "Effect": "Allow",
    "Principal": { "Service": "cloudfront.amazonaws.com" },
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${SPA_BUCKET}/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::$(aws sts get-caller-identity --query Account --output text):distribution/${DIST_ID}"
      }
    }
  }]
}
JSON
)"

echo "==> 5/5 done"
cat <<SUMMARY

  Distribution ID : ${DIST_ID}
  URL             : https://${DIST_DOMAIN}

  Add these as GitHub repo secrets:
    SPA_BUCKET                 = ${SPA_BUCKET}
    CLOUDFRONT_DISTRIBUTION_ID = ${DIST_ID}

  STILL REQUIRED -- the SPA will load but every prediction will time out
  until the instance accepts traffic from CloudFront on ${API_PORT}:

    aws ec2 authorize-security-group-ingress \\
      --group-id <the instance security group> \\
      --ip-permissions 'IpProtocol=tcp,FromPort=${API_PORT},ToPort=${API_PORT},PrefixListIds=[{PrefixListId=<com.amazonaws.global.cloudfront.origin-facing>}]' \\
      --region us-east-1

  Find the prefix list id with:
    aws ec2 describe-managed-prefix-lists --region us-east-1 \\
      --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing

  The distribution takes ~15 minutes to finish deploying.

SUMMARY
