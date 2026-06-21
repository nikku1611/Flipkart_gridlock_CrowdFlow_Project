# CrowdFlow — Traffic Congestion Intelligence System

CrowdFlow is an event-driven ML system designed for smart-city traffic command centers. It forecasts how planned and unplanned events (accidents, VIP movements, water logging) will disrupt traffic and generates rule-based deployment plans.

## System Architecture
The project is split into three main components:
1. **ML Pipeline (`/ml`)**: XGBoost, LightGBM, and CatBoost models predicting:
   - `time_to_resolution` (Regression — Ground truth)
   - `congestion_severity` (Classification — Heuristic)
   - `required_manpower` (Classification — Heuristic)
2. **Backend API (`/backend`)**: FastAPI server serving predictions, SHAP explanations, and historical data.
3. **Frontend UI (`/frontend`)**: React + Vite command center dashboard.

---

## 🚀 How to Run the Project

You will need two terminal windows to run the system locally: one for the Python Backend and one for the React Frontend.

### 1. Start the Backend API (FastAPI)
Open a terminal in the project root directory and run:

```powershell
# Ensure you are in the project root directory
cd d:\Desktop\traffic

# (Optional) If you haven't installed dependencies yet
pip install -r backend\requirements.txt

# Start the FastAPI server on port 8000
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
*The backend will be available at [http://localhost:8000/docs](http://localhost:8000/docs)*

### 2. Start the Frontend Dashboard (React)
Open a **second** terminal window and run:

```powershell
# Navigate to the frontend directory
cd d:\Desktop\traffic\frontend

# (Optional) If you haven't installed dependencies yet
npm install

# Start the Vite development server
npm run dev
```
*The command center dashboard will be available at [http://localhost:5173](http://localhost:5173)*

---

## 🧠 Retraining the ML Models
If you update the dataset (`data.csv`) and want to retrain the models:

```powershell
# Run from the project root
python ml\train.py
```

This will:
1. Clean the data and generate features.
2. Train XGBoost, LightGBM, and CatBoost.
3. Run Optuna hyperparameter tuning.
4. Save the winning models to `ml/models/`.

After training, you can regenerate the SHAP feature importance metrics by running:
```powershell
python ml\evaluate.py
```
*Note: Restart the FastAPI backend after retraining so it loads the new models.*
