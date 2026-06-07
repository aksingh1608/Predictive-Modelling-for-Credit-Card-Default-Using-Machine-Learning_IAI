# Credit Card Default Prediction — IAI Project

End-to-end machine learning project for predicting next-month credit card default, with an optional web demo for scoring clients and exploring what-if scenarios.

**Name** Aryan Kumar Singh
**Course:** BSBI · Introduction to AI  
**Dataset:** `Credit_Card.csv` (34,788 rows, 30 columns)  
**Main deliverable:** `Credit_Card_Default_Prediction.ipynb` (Tasks 1–5)

---

## Project structure

```
IAI/
├── Credit_Card.csv                          # Raw dataset
├── Credit_Card_Default_Prediction.ipynb     # Assignment notebook (EDA → model → evaluation)
├── requirements-app.txt                     # Python deps for the web app only
├── run_app.sh                               # Start the FastAPI server
│
├── scripts/
│   └── export_for_app.py                    # Saves trained model + preprocessing to models/
│
├── models/                                  # Generated after notebook export (Section 7)
│   ├── model.joblib                         # Tuned classifier
│   ├── scaler.joblib                        # StandardScaler (train-fitted)
│   ├── feature_columns.json                 # Feature order (73 columns)
│   ├── iqr_caps.json                        # Outlier caps (train-fitted)
│   ├── impute.json                          # Imputation values (train-fitted)
│   ├── cities.json                          # City list for the web form
│   └── metadata.json                        # Model name, test metrics, top features
│
├── api/                                     # FastAPI backend
│   ├── main.py                              # /api/predict, /api/whatif, /api/metadata
│   ├── preprocess.py                        # Single-row preprocessing (matches notebook)
│   └── schemas.py                           # Request/response validation
│
└── web/                                     # Frontend (HTML/CSS/JS)
    ├── index.html
    ├── app.js
    └── style.css
```

---

## Prerequisites

- **Python 3.10+** (3.12 recommended)
- **Jupyter** (Lab or Notebook) for running the assignment
- Terminal access

### Notebook dependencies

Install once before running the notebook:

```bash
pip install pandas numpy scikit-learn matplotlib seaborn xgboost shap jupyter
```

### Web app dependencies

Install once before running the demo:

```bash
cd "/home/aksingh/AK May 2026/BSBI 1st Sem Work/IAI"
pip install -r requirements-app.txt
```

---

## Part 1 — Run the notebook

This is the **required** part for grading.

1. Open a terminal and go to the project folder:

   ```bash
   cd "/home/aksingh/AK May 2026/BSBI 1st Sem Work/IAI"
   ```

2. Start Jupyter:

   ```bash
   jupyter notebook Credit_Card_Default_Prediction.ipynb
   ```

   Or open the file directly in VS Code / Cursor and use the built-in notebook runner.

3. **Kernel → Restart & Run All** (or run cells top to bottom).

4. Wait for all cells to finish (~5–10 minutes on a laptop). The notebook covers:

   | Section | Content |
   |---------|---------|
   | §1 | Load CSV, repair corrupted columns |
   | §2 | EDA — distributions, correlations, leak diagnosis |
   | §3 | Data prep — split-first pipeline (no leakage) |
   | §4 | Train 7 models |
   | §5 | Evaluation, tuning, threshold, RISK_RATING ablation, SHAP |
   | §6 | Conclusions, limitations, replication notes |
   | §7 | *(Optional)* Export model for web app |

5. Confirm the load cell prints:

   ```text
   Shape: (34788, 30)
   ```

   If you see ~11,000 rows instead, restart the kernel and run from the top — you may have a stale or partial load.

---

## Part 2 — Export the model (for the web demo)

The web app uses the **same pipeline as the notebook**. You must export after training.

1. In the notebook, run **Section 7 — (Optional) Export model for the web application**.

   This writes all files into `models/`.

2. Verify export succeeded:

   ```bash
   ls models/
   ```

   You should see at least: `model.joblib`, `scaler.joblib`, `metadata.json`, `feature_columns.json`.

---

## Part 3 — Run the web application

1. Make sure Part 2 is done (`models/model.joblib` exists).

2. Install web dependencies (if not already):

   ```bash
   pip install -r requirements-app.txt
   ```

3. Start the server:

   ```bash
   ./run_app.sh
   ```

   Or manually:

   ```bash
   python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. Open in your browser:

   **http://127.0.0.1:8000**

5. Use the app:

   - Fill in client details **or** click **Low risk sample** / **High risk sample**
   - Click **Assess default risk** → probability, risk tier, drivers, recommendations
   - Click **Run what-if analysis** → compare scenarios (e.g. if PAY_0 becomes current)

6. Stop the server: `Ctrl+C` in the terminal.

---

## End-to-end quick reference

```bash
# 1. Go to project
cd "/home/aksingh/AK May 2026/BSBI 1st Sem Work/IAI"

# 2. Notebook deps
pip install pandas numpy scikit-learn matplotlib seaborn xgboost shap jupyter

# 3. Run notebook (Jupyter UI) → Run All → then Section 7 export

# 4. Web app deps
pip install -r requirements-app.txt

# 5. Start demo
./run_app.sh

# 6. Browser
# http://127.0.0.1:8000
```

---

## API endpoints (optional / for testing)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/` | Web UI |
| GET | `/api/health` | Server + model status |
| GET | `/api/metadata` | Model metrics, cities, top features |
| POST | `/api/predict` | Score one client profile (JSON body) |
| POST | `/api/whatif` | Compare baseline vs modified scenarios |

Example predict request:

```bash
curl -s -X POST http://127.0.0.1:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"LIMIT_BAL":140000,"SEX":2,"EDUCATION":2,"MARRIAGE":2,"AGE":34,
       "PAY_0":0,"PAY_2":0,"PAY_3":0,"PAY_4":0,"PAY_5":0,"PAY_6":0,
       "RISK_RATING":1,"CITY":"City_1"}'
```

---

## Troubleshooting

### `./run_app.sh`: `env: bash\r: No such file or directory`

The script has Windows line endings. Fix:

```bash
sed -i 's/\r$//' run_app.sh
chmod +x run_app.sh
```

```bash
# Find and stop the old process, or use another port:
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload

---

## Deploy online

See **[DEPLOY.md](DEPLOY.md)** for:

- **Render** (recommended) — full app in one deploy
