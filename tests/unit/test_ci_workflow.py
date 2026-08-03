"""Guards on the deployment pipeline.

The frontend ships to S3/CloudFront while the API ships to ECR/CodeDeploy, out
of the same workflow. These assertions cover the parts that fail silently or
expensively: publishing from a feature branch, invalidating the wrong
distribution, or quietly dropping an existing deployment step.
"""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

WORKFLOW = ROOT / ".github" / "workflows" / "ci_cd.yaml"


@pytest.fixture(scope="module")
def steps():
    workflow = yaml.safe_load(WORKFLOW.read_text())
    job = workflow["jobs"]["CI-CD"]
    return job["steps"]


def find(steps, needle):
    """Every step whose name or run body mentions `needle`."""
    return [
        step
        for step in steps
        if needle in step.get("name", "") or needle in str(step.get("run", ""))
    ]


# --------------------------------------------------------------------------
# the frontend must be built and published
# --------------------------------------------------------------------------

def test_node_is_set_up(steps):
    node = [s for s in steps if "setup-node" in str(s.get("uses", ""))]
    assert node, "the SPA cannot be built without a Node toolchain"
    assert str(node[0]["with"]["node-version"]).startswith("20")


def test_frontend_is_built(steps):
    build = find(steps, "npm run build")
    assert build, "no SPA build step"
    assert "npm ci" in str(build[0]["run"]), "use npm ci for a reproducible install"


def test_build_output_is_synced_to_s3(steps):
    sync = find(steps, "s3 sync")
    assert sync, "the build is never uploaded"
    run = str(sync[0]["run"])
    assert "frontend/dist" in run
    # without --delete, files removed from the app linger in the bucket
    assert "--delete" in run


def test_cloudfront_cache_is_invalidated(steps):
    invalidation = find(steps, "create-invalidation")
    assert invalidation, "viewers would keep the previous build from cache"
    assert "/*" in str(invalidation[0]["run"])


def test_bucket_and_distribution_come_from_secrets(steps):
    published = str(find(steps, "s3 sync")[0]["run"]) + str(
        find(steps, "create-invalidation")[0]["run"]
    )
    assert "secrets.SPA_BUCKET" in published
    assert "secrets.CLOUDFRONT_DISTRIBUTION_ID" in published


# --------------------------------------------------------------------------
# publishing must be limited to the default branch
# --------------------------------------------------------------------------

@pytest.mark.parametrize("needle", ["s3 sync", "create-invalidation"])
def test_publishing_steps_are_gated_on_main(steps, needle):
    step = find(steps, needle)[0]
    condition = str(step.get("if", ""))
    assert "refs/heads/main" in condition, (
        f"{step.get('name')!r} would publish from any branch; "
        "the workflow triggers on every push"
    )


def test_the_build_itself_is_not_gated(steps):
    # building on a feature branch is how we find breakage before merge
    build = find(steps, "npm run build")[0]
    assert "refs/heads/main" not in str(build.get("if", ""))


# --------------------------------------------------------------------------
# the S3 steps need us-east-1 credentials, which are configured partway down
# --------------------------------------------------------------------------

def test_s3_sync_runs_after_the_us_east_1_credentials(steps):
    def index_of(predicate):
        return next(i for i, s in enumerate(steps) if predicate(s))

    creds = index_of(
        lambda s: "configure-aws-credentials" in str(s.get("uses", ""))
        and s.get("with", {}).get("aws-region") == "us-east-1"
    )
    sync = index_of(lambda s: "s3 sync" in str(s.get("run", "")))
    assert sync > creds, "s3 sync would run with the ap-southeast-2 credentials"


# --------------------------------------------------------------------------
# nothing that already worked may be dropped
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "needle",
    [
        "dvc pull",
        "pytest tests/test_model_registry.py",
        "pytest tests/test_model_perf.py",
        "promote_model_to_prod.py",
        "docker build",
        "docker push",
        "aws deploy create-deployment",
    ],
)
def test_existing_pipeline_steps_are_preserved(steps, needle):
    assert find(steps, needle), f"{needle!r} disappeared from the pipeline"
