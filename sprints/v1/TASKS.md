# Sprint v1 — Tasks

## Status: In Progress

- [x] Task 1: Scaffold the React frontend with Vite + Tailwind in `frontend/` (P0)
  - Acceptance: `cd frontend && npm run dev` serves a page on :5173 with a Tailwind-styled heading; `npm run build` emits `frontend/dist/`
  - Files: frontend/package.json, frontend/vite.config.js, frontend/index.html, frontend/src/main.jsx, frontend/src/App.jsx, frontend/src/index.css, .gitignore (add `frontend/node_modules`, `frontend/dist`)
  - Completed: 2026-08-03 — React 18 + Vite 6 + Tailwind v4 (via `@tailwindcss/vite`, no config file needed). Playwright set up with a dev-server harness. 3 E2E tests green; build emits `dist/` with a 7.86 kB compiled stylesheet. semgrep 0 findings, npm audit 0 vulnerabilities.

- [x] Task 2: Add the simplified request schema and raw-payload builder (P0)
  - Acceptance: `build_raw_payload(SimplifiedOrder(distance_km=7.5, ...))` returns a 19-key dict; feeding it through `perform_data_cleaning()` yields a non-empty frame whose `distance` equals 7.5000. Pydantic rejects `distance_km=25.1`, `age=17`, `ratings=6`
  - Files: scripts/api_payload.py (new), tests/unit/test_api_payload.py (new)
  - Notes: restaurant fixed at (22.745049, 75.892471); `delivery_lat = 22.745049 + distance_km / 111.19492664`, longitude unchanged. `Weatherconditions` must be sent as `"conditions {Weather}"`. Bounds: distance 0<d≤25.0, age≥18, ratings 1.0–5.0, pickup 1–60
  - Completed: 2026-08-03 — 65 unit tests green. Two bounds came out tighter than the PRD assumed: `type_of_vehicle` drops `bicycle` and `order_hour` starts at 7, because the fitted encoder (`handle_unknown="ignore"`) would silently zero-encode `bicycle` and `after_midnight` rather than erroring. Added a test that asserts every offered label exists in the fitted encoder so this cannot regress. semgrep 290 rules / 0 findings.

- [x] Task 3: Add `GET /api/health` and `POST /api/predict` to the FastAPI app (P0)
  - Acceptance: `/api/health` returns `{"status":"ok","model_loaded":true,"model_name":...}`; `POST /api/predict` with simplified JSON returns `{"prediction_minutes": <float>}`; an empty cleaned frame returns 400 with a readable message; existing `POST /predict` still works
  - Files: app.py, tests/integration/test_api.py (new)
  - Notes: paths must literally start with `/api/` so the CloudFront behavior maps 1:1 with no origin-path rewriting
  - Completed: 2026-08-03 — 18 integration tests green (83 total). Model loading moved out of import time into a `lifespan` startup hook that records failures instead of raising; this was required by the acceptance criteria, since the old code died on a failed registry load and could never have served `model_loaded: false`. Import dropped from 46s (network) to 1s (none), and tests now run offline against the local artifacts. `/predict` refactored onto the shared `predict_minutes()` helper and still passes. semgrep 290 rules / 0 findings.

- [x] Task 4: Move the service from port 8000 to port 8001 (P0)
  - Acceptance: `docker build` + `docker run -p 8001:8001` serves `/api/health` on :8001; nothing in the repo still binds 8000
  - Files: Dockerfile, app.py, deploy/scripts/start_docker.sh, scripts/sample_predictions.py, .dockerignore (new), tests/unit/test_deployment_config.py (new)
  - Notes: this frees port 8000 for the other project on the same EC2 instance
  - Completed: 2026-08-03 — 9 config tests + verified for real: image built, container ran as `uid=10001(appuser)`, `/api/health` answered on :8001. `scripts/sample_predictions.py` also hardcoded 8000 and was missed by the original task description. Added `.dockerignore` (build context 2.3 GB → ~300 MB; was shipping `.venv`, `frontend/node_modules` and any local `.env` into the image) and a non-root `USER` to clear a blocking semgrep finding. 92 tests green, semgrep 299 rules / 0 findings.

- [x] Task 5: Build the responsive prediction form (P0)
  - Acceptance: all 10 controls render with the exact allowed values from the PRD; single column below `sm`, two columns above `md`; no horizontal scroll at 360px width; HTML input bounds mirror the Pydantic bounds
  - Files: frontend/src/components/PredictionForm.jsx, frontend/src/constants.js, frontend/tests/e2e/form.spec.js
  - Notes: `city_type` option value is `metropolitian` (dataset spelling), not `metropolitan`
  - Completed: 2026-08-03 — 13 controls (the PRD's field table has more than the 10 estimated here). 18 e2e tests assert each select's options equal the accepted values exactly and each number input's min/max mirrors the pydantic bounds, so the two cannot drift. Layout verified by bounding box: side by side at 1280px, stacked at 360px. semgrep 0 findings, npm audit 0 vulnerabilities.

- [x] Task 6: Wire form submission to the API and render the result card (P0)
  - Acceptance: submitting POSTs to `/api/predict` and shows the predicted minutes; button disables and shows a spinner while in flight; a failed request shows the server's error text instead of a blank screen
  - Files: frontend/src/api.js, frontend/src/components/ResultCard.jsx, frontend/src/App.jsx, frontend/vite.config.js (dev proxy `/api` → `http://localhost:8001`), frontend/tests/e2e/predict.spec.js
  - Notes: in production the API is same-origin, so fetch `/api/predict` relative — do not hardcode a host
  - Completed: 2026-08-03 — 7 e2e tests covering success, in-flight disable, 503, 422 field messages, network abort and error-clearing. `api.js` translates pydantic's 422 list into readable `field: message` text and converts a fetch rejection into a sentence rather than "TypeError: Failed to fetch". Verified beyond the mocks against the real backend through the Vite proxy: 14.2 min clear vs 31.1 min stormy/jam/festival, and a live browser run rendering 21 minutes on both desktop and mobile. semgrep 0 findings, npm audit 0 vulnerabilities.

- [ ] Task 7: Provision the S3 bucket and CloudFront distribution with two origins (P0)
  - Acceptance: the CloudFront domain serves the React app over HTTPS, and `curl https://<domain>/api/health` returns the health JSON from EC2
  - Files: none in-repo (AWS CLI/console); record the bucket name and distribution ID in sprints/v1/NOTES.md
  - Notes: S3 origin private behind OAC as the default behavior; second behavior `/api/*` → EC2 public DNS, **HTTP-only, port 8001**, caching disabled, all HTTP methods allowed, `Origin` + `Content-Type` forwarded. Add SPA fallback: 403/404 → `/index.html` with 200. Open EC2 SG inbound 8001 to prefix list `com.amazonaws.global.cloudfront.origin-facing`

- [x] Task 8: Extend the GitHub Actions pipeline to build and publish the frontend (P0)
  - Acceptance: a push to `main` builds the SPA, syncs it to S3, and creates a CloudFront invalidation; the existing ECR/CodeDeploy steps still run unchanged
  - Files: .github/workflows/ci_cd.yaml, tests/unit/test_ci_workflow.py (new)
  - Notes: add `actions/setup-node@v4` (Node 20), then `npm ci && npm run build` in `frontend/`, `aws s3 sync frontend/dist s3://<bucket> --delete`, `aws cloudfront create-invalidation --paths "/*"`. Run these in the `us-east-1` credential block; add `CLOUDFRONT_DISTRIBUTION_ID` and `SPA_BUCKET` as repo secrets
  - Completed: 2026-08-03 — 16 tests parsing the workflow YAML. The publish steps are gated on `refs/heads/main` because the workflow triggers on **every** push, so an ungated `s3 sync --delete` would let any branch overwrite the live site; the build itself stays ungated so branches catch breakage pre-merge. Tests also assert the sync runs *after* the us-east-1 credential block (it would otherwise use ap-southeast-2) and that all seven pre-existing pipeline steps survive.
  - **Still required before this works**: add the `SPA_BUCKET` and `CLOUDFRONT_DISTRIBUTION_ID` repo secrets, and complete Task 7.

- [x] Task 9: Add the health badge and "Try an example" button (P1)
  - Acceptance: on load the page calls `/api/health` and shows a green "Live" or red "Unavailable" badge; clicking "Try an example" fills every field with a valid sample order that predicts successfully
  - Files: frontend/src/components/HealthBadge.jsx, frontend/src/constants.js, frontend/src/App.jsx, frontend/tests/e2e/health-and-example.spec.js
  - Notes: the model is pulled from DagsHub at container startup, so a red badge is a genuine and likely failure mode worth surfacing
  - Completed: 2026-08-03 — 6 e2e tests. The badge has four states, not two: "unreachable" (amber) is kept distinct from "degraded" (red) because "API down" and "API up, model down" need different messages — exactly the split `/api/health` returning 200-on-degraded was designed for. A test asserts the health check never gates the form, so a slow check cannot block a prediction. The example order is asserted to sit inside every API bound. semgrep 0 findings, npm audit 0 vulnerabilities.

- [x] Task 10: Add session prediction history (P1)
  - Acceptance: each successful prediction prepends a row showing distance, traffic, weather and predicted minutes; the list keeps the last 5 and clears on reload
  - Files: frontend/src/components/HistoryList.jsx, frontend/src/App.jsx, frontend/tests/e2e/history.spec.js
  - Notes: React state only — no localStorage, no backend persistence
  - Completed: 2026-08-03 — 8 e2e tests covering ordering, the 5-row cap evicting the oldest, failed predictions not being recorded, clearing on reload, and no overflow at 360px. React state only, as specified. Production build 152 kB JS / 15 kB CSS. semgrep 0 findings, npm audit 0 vulnerabilities.

---

## Discovered during the sprint — deferred, not fixed here

- **Model cannot serve overnight orders or bicycle deliveries** (found in Task 2)
  - The fitted `preprocessor.joblib` was never trained on `order_time_of_day="after_midnight"`
    (orders placed 01:00–06:59) or `type_of_vehicle="bicycle"`, even though both occur in the
    raw dataset. Because the nominal encoder uses `handle_unknown="ignore"`, these do not raise —
    they become all-zero vectors and the model returns a confident but meaningless number.
  - v1 works around this by refusing the input at validation time, so no user can reach it.
  - Real fix belongs in a training sprint: retrain with those categories represented, or set
    `handle_unknown="error"` so the gap surfaces loudly instead of silently.
  - Scope note: this is a data/model coverage gap, not a defect in the serving code.

- **GitHub Actions are pinned to mutable tags, not commit SHAs** (found in Task 8)
  - semgrep `github-actions-mutable-action-tag` reports 6 blocking findings: `actions/checkout@v4`,
    `actions/setup-python@v5`, `actions/setup-node@v4`, `aws-actions/configure-aws-credentials@v4`
    (twice) and `aws-actions/amazon-ecr-login@v2`. Five pre-date this sprint; Task 8 added the
    sixth following the file's existing convention.
  - Blast radius is what makes this worth recording: the workflow handles `AWS_ACCESS_KEY_ID`,
    `AWS_SECRET_ACCESS_KEY` and `DAGSHUB_TOKEN`. If an action author's `v4` tag were moved to a
    malicious commit, those credentials would be readable by the new code.
  - Not fixed here deliberately: re-pinning six actions to SHAs is a repo-wide policy change, and
    a mistyped SHA breaks the pipeline. Recommended follow-up is pinning all six at once plus
    Dependabot to keep them current.

- **`dagshub.init()` blocks on interactive OAuth when the token is missing** (found in Task 4)
  - Observed while running the built image with no `DAGSHUB_USER_TOKEN`: startup printed an
    "AUTHORIZATION REQUIRED" OAuth URL and sat there for roughly two minutes before giving up,
    after which the app came up degraded and served `/api/health` correctly.
  - Production passes the token from SSM, so the happy path is unaffected; the risk is a wrong or
    expired token turning a deploy into a multi-minute stall. CodeDeploy's `ApplicationStart`
    timeout is 300s, so it currently fits — but only just.
  - Suggested fix: assert `DAGSHUB_USER_TOKEN` is set before calling `dagshub.init()` and fail
    fast with a clear error instead of entering the OAuth flow inside a container.
