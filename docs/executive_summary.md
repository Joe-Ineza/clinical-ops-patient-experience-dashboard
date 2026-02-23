# Executive Summary: Clinical Operations & Patient Experience Dashboard

## Purpose
This dashboard provides a concise, operational view of synthetic digital health service delivery and patient experience signals. It is designed for stakeholder reviews, MEL discussions, and rapid decision support.

It answers four practical questions:
1. How are consultation volumes and encounter mix changing over time?
2. Where are referral intensity and cost pressures highest?
3. How are patient experience signals (NPS and complaints) evolving?
4. Which complaint categories and comments need immediate attention?

---

## Data Source and Scope
- **Clinical data source:** Synthea open CSV sample data (April 2020 package)
- **Core files used:** `encounters.csv`, `conditions.csv`, `procedures.csv`, `medications.csv`, `patients.csv`, `providers.csv`
- **System architecture:** PostgreSQL-backed analytics views + Streamlit dashboard
- **Feedback module:** Synthetic encounter-level patient satisfaction and complaint signals generated for portfolio simulation

---

## How We Built It
- **Ingestion and cleaning:** Loaded Synthea CSVs with Python (`pandas`), normalized columns, and standardized date/time and numeric fields for modeling.
- **Clinical record model:** Linked encounters with conditions, procedures, and medications to produce consultation-level analytical records (consult ID, patient ID, clinician ID, diagnosis, treatment, referral, timestamps).
- **Synthetic feedback generator:** Created one feedback record per consultation using deterministic rules from encounter characteristics:
  - Generated an `nps_score` (0–10) from consultation ID-based hashing for reproducible results.
  - Derived `nps_category` (Promoter/Passive/Detractor) and mapped survey response labels.
  - Flagged complaints using rule logic (e.g., low NPS and prolonged consultation duration).
  - Assigned complaint categories by encounter class and produced standardized qualitative comment templates.
- **Storage and views:** Loaded raw and generated tables into PostgreSQL and created SQL views for consultation operations, monthly performance, experience trends, and comments.
- **Visualization layer:** Built a Streamlit dashboard with guided tabs, KPI summaries, trend analysis, complaint category breakdowns, and filtered export support.

---

## What the Dashboard Shows
- **Overview & Consultations**
  - Total consultations, unique patients, unique clinicians, referral rate, average NPS, complaint rate
  - Monthly consultation trends by encounter class
- **Operations Performance**
  - Referral rate trend by encounter class
  - Average claim cost trend by encounter class
- **Experience Signals**
  - Average NPS trend
  - Complaints trend and top complaint categories
- **Comment Explorer**
  - Filterable qualitative comments and complaint context

---

## Why This Is Useful for Stakeholders
This dashboard enables:
- **Operational monitoring:** Understand demand patterns and service load changes
- **Quality/governance reviews:** Detect potential pressure points in referrals and cost dynamics
- **Experience management:** Track satisfaction and complaint burden over time
- **Communication:** Present one clear, consistent performance narrative to technical and non-technical audiences

---

## Recommended Review Flow (Meeting Use)
1. Start with **Overview & Consultations** for baseline status and current pressure points.
2. Move to **Operations Performance** to identify class-level referral and cost drivers.
3. Review **Experience Signals** for NPS trajectory and complaint burden.
4. Close with **Comment Explorer** to ground decisions in qualitative context.

---

## Interpretation Notes
- All records are synthetic and de-identified by design.
- Patient feedback fields in this project are simulated from encounter characteristics for analytics demonstration.
- Trends should be interpreted as portfolio evidence of analytical capability, not real-world service outcomes.

---

## Limitations
- Feedback data is simulated, not collected from real surveys.
- Generalizability to real deployments is limited by synthetic generation logic.
- Some metrics are proxies and should be validated against production definitions in real implementations.

---

## Suggested Next Enhancements
- Integrate one real open patient-experience source for external benchmarking.
- Add automated “top 5 insights” export for governance meeting packs.
- Add threshold alerts (e.g., complaint rate or referral spikes) for proactive monitoring.

---

## Document Control
- **Prepared for:** Stakeholder presentation and reference
- **Project:** Clinical Operations & Patient Experience (Synthea)
- **Version:** 1.0
- **Date:** February 2026
