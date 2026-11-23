# Pakistan Medicine Finder

A Flask website for searching a small generic-medicine reference catalog and pharmacy locations mapped in OpenStreetMap within Pakistan.

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

## Deploy on Render

This repository includes `render.yaml`. In Render, choose **New → Blueprint**, connect this GitHub repository, select branch `feature/flask-medicine-finder`, then apply the configuration. Alternatively create a Python Web Service with build command `pip install -r requirements.txt` and start command `gunicorn app:app`. Add an environment variable `HTTP_USER_AGENT` with a descriptive app name and a real contact email before deployment. Render will provide the public URL after a successful deploy.

## Data, limits, and medical disclaimer

- Pharmacy locations come from OpenStreetMap via Overpass; place data can be missing or outdated.
- Location lookup uses Nominatim and is restricted to Pakistan.
- The medicine JSON is a small illustrative lookup catalog, not a verified list of the most-used medicines, DRAP approval, medical advice, or inventory.
- The site does **not** check stock, price, quality, or registration. Contact a pharmacy and consult a qualified health professional.
- Public Nominatim and Overpass instances have usage policies, rate limits, and availability limits. Review their policies and use an appropriate provider or self-hosted service for sustained/high traffic.
- OpenStreetMap data is under ODbL. Keep the map attribution visible.
