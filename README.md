# Clinical Operations & Patient Experience (Synthea)

This project builds a digital health analytics using open Synthea CSV data.

## Executive Summary
- **Objective:** Provide a practical operations and patient-experience dashboard for service monitoring and MEL-style review.
- **Questions answered:** consultation volume/mix changes, referral and cost pressure points, NPS/complaint movement, and key qualitative complaint themes.
- **How it was built:** Synthea CSV ingestion and normalization, consultation-level clinical modeling, synthetic encounter-level feedback generation, PostgreSQL view layer, and Streamlit analytics UI.
- **Stakeholder value:** A clear, presentation-ready view of service performance and experience signals for technical and non-technical review meetings.
- **Important caveat:** Feedback and comments are simulated for portfolio demonstration, not real survey collection.

Full stakeholder brief: [docs/executive_summary.md](docs/executive_summary.md)

## Scope
- Consultation and clinical records analytics from Synthea encounters and linked clinical events.
- Synthetic patient satisfaction and complaint analytics generated at encounter level.
- PostgreSQL-backed Streamlit dashboard for operations, quality, and experience monitoring.

## Input data
- Folder: `Interesting Datasets/synthea_sample_data_csv_apr2020/csv`
- Core CSVs used:
  - `encounters.csv`
  - `conditions.csv`
  - `procedures.csv`
  - `medications.csv`
  - `patients.csv`
  - `providers.csv`

## Project structure
- `scripts/ingest_synthea.py` - data ingestion, cleaning, synthetic feedback generation, DB load
- `sql/01_views.sql` - analytics views for dashboarding
- `app/streamlit_app.py` - Streamlit dashboard
- `data/processed` - processed extracts
- `docs/quickstart.md` - run guide

## Quick run
1. Install dependencies
   - `pip install -r requirements.txt`
2. Configure `.env` (copy from `.env.example`)
3. Ingest and load database
   - `python scripts/ingest_synthea.py --input-dir "../../Interesting Datasets/synthea_sample_data_csv_apr2020/csv" --output-dir data/processed --load-db`
4. Apply views
   - execute `sql/01_views.sql` in PostgreSQL
5. Launch app
   - `streamlit run app/streamlit_app.py`

## Note
Patient satisfaction data is generated synthetically from encounter characteristics to simulate survey/complaint workflows.
