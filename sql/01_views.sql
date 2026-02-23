CREATE SCHEMA IF NOT EXISTS digital_health;

CREATE OR REPLACE VIEW digital_health.vw_consultation_clinical_records AS
WITH diagnosis AS (
    SELECT
        encounter,
        STRING_AGG(DISTINCT description, '; ' ORDER BY description) AS diagnosis_summary
    FROM digital_health.raw_conditions
    WHERE encounter IS NOT NULL
    GROUP BY encounter
),
procedure_tx AS (
    SELECT
        encounter,
        STRING_AGG(DISTINCT description, '; ' ORDER BY description) AS procedure_summary
    FROM digital_health.raw_procedures
    WHERE encounter IS NOT NULL
    GROUP BY encounter
),
medication_tx AS (
    SELECT
        encounter,
        STRING_AGG(DISTINCT description, '; ' ORDER BY description) AS medication_summary
    FROM digital_health.raw_medications
    WHERE encounter IS NOT NULL
    GROUP BY encounter
)
SELECT
    e.id AS consult_id,
    e.patient AS patient_id,
    e.provider AS clinician_id,
    e.start AS consultation_start,
    e.stop AS consultation_end,
    EXTRACT(EPOCH FROM (e.stop - e.start)) / 3600.0 AS consultation_duration_hours,
    e.encounterclass,
    e.description AS consultation_type,
    COALESCE(d.diagnosis_summary, 'No diagnosis recorded') AS diagnosis,
    CONCAT_WS(' | ', p.procedure_summary, m.medication_summary) AS treatment,
    (e.reasoncode IS NOT NULL OR e.reasondescription IS NOT NULL) AS referral_flag,
    e.reasondescription AS referral_reason,
    e.base_encounter_cost,
    e.total_claim_cost,
    e.payer_coverage
FROM digital_health.raw_encounters e
LEFT JOIN diagnosis d ON d.encounter = e.id
LEFT JOIN procedure_tx p ON p.encounter = e.id
LEFT JOIN medication_tx m ON m.encounter = e.id;


CREATE OR REPLACE VIEW digital_health.vw_operations_monthly AS
SELECT
    DATE_TRUNC('month', consultation_start)::date AS month,
    encounterclass,
    COUNT(*) AS consultations,
    AVG(consultation_duration_hours) AS avg_consultation_hours,
    SUM(CASE WHEN referral_flag THEN 1 ELSE 0 END) AS referrals,
    100.0 * SUM(CASE WHEN referral_flag THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS referral_rate_pct,
    AVG(total_claim_cost) AS avg_claim_cost
FROM digital_health.vw_consultation_clinical_records
GROUP BY 1, 2
ORDER BY 1, 2;


CREATE OR REPLACE VIEW digital_health.vw_patient_experience_monthly AS
SELECT
    DATE_TRUNC('month', consult_start)::date AS month,
    encounterclass,
    COUNT(*) AS responses,
    AVG(nps_score) AS avg_nps,
    100.0 * SUM(CASE WHEN nps_score >= 9 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS promoter_pct,
    100.0 * SUM(CASE WHEN nps_score <= 6 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS detractor_pct,
    SUM(CASE WHEN complaint_flag THEN 1 ELSE 0 END) AS complaints,
    100.0 * SUM(CASE WHEN complaint_flag THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS complaint_rate_pct
FROM digital_health.raw_patient_feedback
GROUP BY 1, 2
ORDER BY 1, 2;


CREATE OR REPLACE VIEW digital_health.vw_feedback_comments AS
SELECT
    consult_id,
    patient_id,
    clinician_id,
    consult_start,
    encounterclass,
    nps_score,
    nps_category,
    survey_response,
    complaint_flag,
    complaint_category,
    qualitative_comment
FROM digital_health.raw_patient_feedback;
