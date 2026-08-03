"""Guards that the service is wired to one port, everywhere.

Port 8001 is this app's home on the shared EC2 instance; 8000 belongs to a
different project on the same box.  A stale 8000 in any one of these files
means either a container that publishes a port nothing listens on, or two
projects fighting over the same one -- both of which only show up at deploy
time, so they are asserted here instead.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

SERVICE_PORT = 8001
OTHER_PROJECT_PORT = 8000

DOCKERFILE = ROOT / "Dockerfile"
START_DOCKER = ROOT / "deploy" / "scripts" / "start_docker.sh"
SAMPLE_PREDICTIONS = ROOT / "scripts" / "sample_predictions.py"


def active_lines(path, comment_prefix="#"):
    """Lines with real effect: blanks and comment-only lines removed."""
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith(comment_prefix):
            yield number, line


def test_dockerfile_exposes_the_service_port():
    exposed = re.findall(r"^EXPOSE\s+(\d+)", DOCKERFILE.read_text(), re.M)
    assert exposed == [str(SERVICE_PORT)]


def test_dockerfile_cmd_binds_the_service_port():
    cmd = [line for _, line in active_lines(DOCKERFILE) if line.startswith("CMD")]
    assert len(cmd) == 1, "expected exactly one CMD"
    assert f'"{SERVICE_PORT}"' in cmd[0], cmd[0]


def test_start_docker_publishes_the_service_port():
    published = re.findall(r"-p\s+(\d+):(\d+)", START_DOCKER.read_text())
    assert published == [(str(SERVICE_PORT), str(SERVICE_PORT))]


def test_app_module_default_port():
    import app

    assert app.PORT == SERVICE_PORT


def test_sample_predictions_targets_the_service_port():
    urls = re.findall(r"127\.0\.0\.1:(\d+)", SAMPLE_PREDICTIONS.read_text())
    assert urls, "expected a local URL in the sample script"
    assert set(urls) == {str(SERVICE_PORT)}


@pytest.mark.parametrize(
    "path, comment_prefix",
    [
        (DOCKERFILE, "#"),
        (START_DOCKER, "#"),
        (ROOT / "app.py", "#"),
        (SAMPLE_PREDICTIONS, "#"),
    ],
)
def test_no_active_line_still_binds_the_other_projects_port(path, comment_prefix):
    offenders = [
        f"{path.name}:{number}: {line.strip()}"
        for number, line in active_lines(path, comment_prefix)
        if str(OTHER_PROJECT_PORT) in line
    ]
    assert not offenders, (
        f"port {OTHER_PROJECT_PORT} belongs to the other project: "
        + "; ".join(offenders)
    )
