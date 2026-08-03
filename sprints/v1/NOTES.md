# Sprint v1 — Deployment Notes

## Status

Tasks 1–6 and 8–10 are complete. **Task 7 (AWS provisioning) is blocked** and is the only
thing standing between the current code and a public URL.

## Why Task 7 is blocked

The credentials configured locally and in CI belong to
`arn:aws:iam::241077340105:user/sayan-dvc-user`, which is scoped to DVC and ECR:

| Action | Result |
| --- | --- |
| `s3` on existing buckets | works |
| `cloudfront:ListDistributions` | `AccessDenied` — no identity-based policy |
| `ec2:DescribeInstances` | `UnauthorizedOperation` |
| `ec2:DescribeSecurityGroups` | `UnauthorizedOperation` |
| `iam:ListAttachedUserPolicies` | `AccessDenied` |

Provisioning needs an administrative profile. Nothing was created.

## To finish the sprint

### 1. Provision (needs admin credentials)

```bash
SPA_BUCKET=swiggy-delivery-frontend-241077340105 \
EC2_ORIGIN_DOMAIN=<instance public DNS> \
AWS_PROFILE=<admin> \
./deploy/provision_frontend.sh
```

The script creates the private bucket, an Origin Access Control, and one CloudFront
distribution with two origins. It prints the distribution ID and URL when done.

> The script's CloudFront config has been validated as JSON and asserted structurally
> correct, but it has never been run against AWS. Read it before running it.

### 2. Open the security group

The SPA will load without this, but **every prediction will time out** — CloudFront has to
reach the instance on 8001:

```bash
aws ec2 describe-managed-prefix-lists --region us-east-1 \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing

aws ec2 authorize-security-group-ingress \
  --group-id <instance SG> \
  --ip-permissions 'IpProtocol=tcp,FromPort=8001,ToPort=8001,PrefixListIds=[{PrefixListId=<from above>}]' \
  --region us-east-1
```

### 3. Add the repo secrets

Task 8's pipeline reads these; without them the publish steps fail:

- `SPA_BUCKET`
- `CLOUDFRONT_DISTRIBUTION_ID`

### 4. Attach an Elastic IP

If the instance has no Elastic IP, its public DNS changes on restart and the CloudFront
origin silently breaks.

## Record once provisioned

| Item | Value |
| --- | --- |
| SPA bucket | _(fill in)_ |
| Distribution ID | _(fill in)_ |
| Public URL | _(fill in)_ |
| EC2 origin domain | _(fill in)_ |
| Security group id | _(fill in)_ |

## Port allocation on the shared instance

| Port | Owner |
| --- | --- |
| 8000 | the other project (confirmed running a "Papeer API" container) |
| 8001 | this service |
