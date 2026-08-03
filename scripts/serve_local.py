"""Run the API locally against the DVC-tracked model artifacts.

`app.py` normally pulls the model from the DagsHub registry on startup, which
needs DAGSHUB_USER_TOKEN and a network round trip. For local work that is slow
and, without a token, drops into an interactive OAuth prompt. This entry point
injects the artifacts in `models/` instead, so the API comes up offline in
about a second.

    python scripts/serve_local.py

Then start the frontend in another terminal:

    cd frontend && npm run dev

and open http://localhost:5173 -- Vite proxies /api to this process, mirroring
what CloudFront does in production.
"""

import sys
from pathlib import Path

import joblib
import uvicorn
from sklearn import set_config
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# the preprocessor was fitted with pandas output; the pipeline needs the same
set_config(transform_output="pandas")

import app as app_module  # noqa: E402

MODELS = ROOT / "models"


def local_loader():
    """Build the serving pipeline from local files rather than the registry."""
    missing = [
        name
        for name in ("preprocessor.joblib", "model.joblib")
        if not (MODELS / name).exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"missing {', '.join(missing)} in models/ -- run `dvc pull` first"
        )

    pipeline = Pipeline(
        steps=[
            ("preprocess", joblib.load(MODELS / "preprocessor.joblib")),
            ("regressor", joblib.load(MODELS / "model.joblib")),
        ]
    )
    return pipeline, "local-artifact-model"


if __name__ == "__main__":
    state = app_module.load_model(loader=local_loader)
    if state["pipeline"] is None:
        print(f"model failed to load: {state['error']}", file=sys.stderr)
        raise SystemExit(1)

    print(f"model loaded: {state['name']}")
    print(f"API on http://127.0.0.1:{app_module.PORT}  (docs at /docs)")
    uvicorn.run(app_module.app, host="127.0.0.1", port=app_module.PORT)
