# Sprint v1 — PRD: Public Web Frontend for Delivery Time Prediction

## Overview

Build a simple, responsive React frontend so anyone with a link can get a delivery-time
prediction without touching Swagger or curl. The existing FastAPI `/predict` endpoint expects
the raw 19-field Swiggy dataset schema (lat/long pairs, rider IDs, pickup timestamps), which is
unusable for a human, so this sprint adds a **simplified `/api/predict` endpoint** that accepts
~10 human-friendly fields and synthesizes the raw payload internally. The SPA is served from
S3 behind CloudFront, with the API attached to the **same** CloudFront distribution as a second
origin — giving one HTTPS URL for both, with no CORS. The service also moves from port 8000 to
**port 8001** so the other project can take 8000 on the same EC2 instance.

## Goals

- A public HTTPS URL where anyone can enter ~10 fields and see a predicted delivery time in minutes.
- Layout works on phone (single column) and desktop (two columns) with no horizontal scroll.
- New `/api/predict` accepts simplified input, builds the raw 19-field payload, reuses the existing model pipeline.
- Input validation makes the silent `.dropna()` → 400 failure mode unreachable from the UI.
- App runs on **port 8001** end to end, freeing port 8000 for the other project.
- Frontend deploys through the existing GitHub Actions pipeline — no second pipeline to hand-manage.

## User Stories

- As a visitor, I want to enter a few plain-English order details and get a predicted delivery time, so that I can use the model without reading API docs.
- As a visitor on my phone, I want the form to be usable one-handed, so that I can try it from anywhere.
- As a curious visitor, I want a "Try an example" button, so that I can see a prediction without knowing what to type.
- As a visitor, I want to see whether the service is live, so that I know a failure is the server, not me.
- As a visitor, I want my last few predictions kept on screen, so that I can compare scenarios side by side.
- As the maintainer, I want this app off port 8000, so that I can run my other project there on the same box.

## Technical Architecture

**Frontend**: React 18 + Vite + Tailwind CSS (no component library — keep it small)
**Backend**: existing FastAPI app, plus a new `/api/*` router, now listening on **8001**
**Hosting**: S3 (private, Origin Access Control) + CloudFront
**Model**: unchanged — MLflow registry via DagsHub, loaded at container startup

### Component diagram

```
                        Browser
                           │  https://dXXXX.cloudfront.net
                           ▼
              ┌────────────────────────────┐
              │   CloudFront Distribution  │
              │   (default *.cloudfront.net cert)
              └──────────┬─────────┬───────┘
                         │         │
      default behavior   │         │  /api/*  behavior
      (cache: enabled)   │         │  (cache: DISABLED, all HTTP methods)
                         ▼         ▼
             ┌──────────────┐   ┌────────────────────────────┐
             │  S3 bucket   │   │  EC2 custom origin  :8001  │
             │  (private,   │   │  HTTP-only to origin       │
             │   OAC)       │   │  ┌──────────────────────┐  │
             │  React build │   │  │ FastAPI container    │  │
             └──────────────┘   │  │  delivery_time_pred  │  │
                                │  │  GET  /api/health    │  │
                                │  │  POST /api/predict   │  │
                                │  │  POST /predict (kept)│  │
                                │  └──────────┬───────────┘  │
                                │  port 8000 → FREE for the  │
                                │  other project             │
                                └─────────────┼──────────────┘
                                              ▼
                                   MLflow registry (DagsHub)
```

### Port allocation on the EC2 instance

| Port | Owner | Change |
| --- | --- | --- |
| 8000 | the other project | freed by this sprint |
| 8001 | `delivery_time_pred` container | **new home** for this app |

Moving the port touches three files — `Dockerfile` (`EXPOSE` + `CMD`), `app.py` (the
`__main__` uvicorn call), and `deploy/scripts/start_docker.sh` (`-p 8001:8001`). The
security group must open 8001 and the CloudFront origin must target 8001.

### Why the API sits behind CloudFront

A page served over HTTPS from CloudFront **cannot** call `http://<ec2-ip>:8001` — browsers block
that as mixed active content, and it cannot be worked around from JavaScript. Routing `/api/*`
through the same distribution solves three problems at once:

| Problem | Solved by |
| --- | --- |
| Mixed content (HTTPS page → HTTP API) | CloudFront terminates TLS, talks HTTP to the origin |
| CORS preflight and headers | SPA and API share one origin → no CORS at all |
| Needing an ALB + ACM cert + domain | Default `*.cloudfront.net` cert is free and instant |

### Data flow (one prediction)

```
Form state (10 fields)
   │  POST /api/predict
   ▼
Pydantic SimplifiedOrder  ── validation rejects out-of-range input with a clear message
   │
   ▼
build_raw_payload()  ── synthesizes the 19 raw fields
   │   • lat/long: restaurant fixed at Indore (22.745049, 75.892471);
   │     delivery lat offset by distance_km / 111.19492664  → haversine returns distance exactly
   │   • Order_Date  = today, "%d-%m-%Y"
   │   • Time_Orderd = chosen hour; Time_Order_picked = + pickup_minutes
   │   • Weatherconditions = "conditions {weather}"  (cleaner strips "conditions ")
   │   • ID / Delivery_person_ID = dummies (dropped during cleaning)
   ▼
perform_data_cleaning()  ── existing, untouched
   ▼
model_pipe.predict()
   ▼
{ "prediction_minutes": 27.4 }
```

The latitude-offset trick was verified against the live cleaning code: requesting 3.0 / 7.5 /
12.0 / 24.9 km returns `distance` of exactly 3.0000 / 7.5000 / 12.0000 / 24.9000 with the
correct `distance_type` bin. Longitude is held constant so the offset is along a meridian, and
both coordinates stay well above the `clean_lat_long` threshold of 1.

### Validation guardrails (probed against the real pipeline)

`perform_data_cleaning()` ends in `.dropna()`, so bad input silently yields an empty frame and a
generic 400. These bounds were measured against the actual cleaning code and are enforced in
Pydantic **and** in the form inputs:

| Field | Bound | What happens outside it |
| --- | --- | --- |
| `distance_km` | `0 < d ≤ 25.0` | `25.01` and above → `distance_type` is NaN → row dropped |
| `age` | `18 – 65` | `17` is explicitly dropped as a minor rider |
| `ratings` | `1.0 – 5.0` | the literal string `"6"` is explicitly dropped |
| `pickup_minutes` | `1 – 60` | negative/absurd values distort `pickup_time_minutes` |
| `order_hour` | `7 – 23` | see below — hour `0` is dropped, hours `1–6` are silently mis-encoded |

### The encoder's known categories are narrower than the dataset's

Discovered while building Task 2, and the reason two of the ranges above are tighter than
expected. The fitted `preprocessor.joblib` nominal encoder uses `handle_unknown="ignore"`, so a
label it was never fitted on **does not raise** — it becomes an all-zero vector and quietly
degrades the prediction. Two values fall into that trap:

| Value | Status | Consequence |
| --- | --- | --- |
| `type_of_vehicle = "bicycle"` | in the raw dataset, **absent** from the fitted encoder | silently zero-encoded |
| `order_time_of_day = "after_midnight"` | produced by hours `1–6`, **absent** from the encoder | silently zero-encoded |

Both are therefore excluded from the accepted input: `bicycle` is not offered, and `order_hour`
starts at `7` (the first hour in the `morning` bin). Hour `0` is separately invalid — the
`time_of_day` bins are `[0, 6, 12, 17, 20, 24]` with `right=True`, so midnight lands on the
excluded left edge and becomes NaN.

`tests/unit/test_api_payload.py` asserts every offered label exists in the fitted encoder's
categories, so this cannot silently regress if the model is retrained.

### Frontend field → model feature mapping

| UI control | Raw field(s) synthesized | Model feature |
| --- | --- | --- |
| Distance (km) slider | `Restaurant_*`, `Delivery_location_*` | `distance`, `distance_type` |
| Rider age | `Delivery_person_Age` | `age` |
| Rider rating | `Delivery_person_Ratings` | `ratings` |
| Prep/pickup minutes | `Time_Orderd`, `Time_Order_picked` | `pickup_time_minutes` |
| Order time (hour) | `Time_Orderd` | `order_time_of_day` |
| Weather select | `Weatherconditions` | `weather` |
| Traffic select | `Road_traffic_density` | `traffic` |
| Vehicle condition | `Vehicle_condition` | `vehicle_condition` |
| Order type / vehicle | `Type_of_order`, `Type_of_vehicle` | same |
| Multiple deliveries | `multiple_deliveries` | same |
| Festival / City type | `Festival`, `City` | `festival`, `city_type` |
| *(implicit — today's date)* | `Order_Date` | `is_weekend` |

### Categorical values the model expects (post-cleaning, lowercased)

All values below are verified present in the fitted `preprocessor.joblib`:

- **weather**: sunny, stormy, sandstorms, cloudy, fog, windy
- **traffic**: low, medium, high, jam
- **type_of_order**: snack, meal, drinks, buffet
- **type_of_vehicle**: motorcycle, scooter, electric_scooter  *(no bicycle — see above)*
- **city_type**: metropolitian, urban, semi-urban  *(note the dataset's spelling)*
- **festival**: yes, no
- **vehicle_condition**: 0, 1, 2, 3
- **multiple_deliveries**: 0, 1, 2, 3
- **order_hour**: 7–23  *(hours 1–6 are unsupported by the model — see above)*

## Out of Scope (v2+)

- Custom domain, Route 53, ACM certificate, ALB
- Authentication, rate limiting, WAF, API keys
- Map-based location picker (Leaflet) for real lat/long input
- Batch CSV upload and bulk prediction
- Server-side persistence of prediction history (v1 history is in-memory, per session)
- Frontend unit/E2E tests (Vitest/Playwright) — belongs in a testing sprint
- SHAP/feature-importance explanation of a prediction
- Actually deploying the other project onto port 8000 (this sprint only frees the port)
- Terraform/CDK codification of the S3 + CloudFront resources

## Dependencies

- **Existing and working**: FastAPI `app.py` with `/predict`, `scripts/data_clean_utils.py`, Docker image → ECR (`ap-southeast-2`), CodeDeploy → EC2 (`us-east-1`), model in DagsHub MLflow registry under alias `candidate`.
- **AWS permissions required** for the CI user: `s3:CreateBucket`/`PutObject` on the new SPA bucket, `cloudfront:CreateInvalidation`, plus console/CLI rights to create the distribution and OAC.
- **EC2 security group** must allow inbound `:8001` from CloudFront (managed prefix list `com.amazonaws.global.cloudfront.origin-facing`).
- **Node.js 20+** locally and on the GitHub Actions runner.
- The EC2 instance needs a stable public DNS — attach an **Elastic IP** if one isn't already attached, otherwise the CloudFront origin breaks on instance restart.
