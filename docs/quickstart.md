# Quickstart

## 1) Environment
```powershell
Set-Location "i:\Joe_Prsn\Irembo\New Positions\Monitoring and Evaluation\clinical_ops_patient_experience_synthea"
& "I:\Joe_Prsn\Irembo\New Positions\.venv\Scripts\Activate.ps1"
& "I:\Joe_Prsn\Irembo\New Positions\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## 2) Configure DB
- Copy `.env.example` to `.env`
- Update PostgreSQL credentials

## 3) Ingest Synthea CSV and load DB
```powershell
python .\scripts\ingest_synthea.py --input-dir "i:\Joe_Prsn\Irembo\New Positions\Interesting Datasets\synthea_sample_data_csv_apr2020\csv" --output-dir ".\data\processed" --load-db
```

## 4) Create views
Run SQL file:
- `sql/01_views.sql`

## 5) Launch dashboard
```powershell
& "I:\Joe_Prsn\Irembo\New Positions\.venv\Scripts\python.exe" -m streamlit run .\app\streamlit_app.py
```
