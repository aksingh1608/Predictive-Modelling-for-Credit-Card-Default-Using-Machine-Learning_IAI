#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [[ ! -f models/model.joblib ]]; then
  echo "No exported model found."
  echo ""
  echo "Export from your notebook first:"
  echo "  1. Open Credit_Card_Default_Prediction.ipynb"
  echo "  2. Run all cells through Task 4 (tuned model)"
  echo "  3. Run Section 7 — Export model for the web application"
  exit 1
fi

echo "Using model from: $(python3 -c "import json; print(json.load(open('models/metadata.json'))['source'])")"
echo "Starting server at http://127.0.0.1:8000"
exec python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
