from __future__ import annotations

import argparse
import hashlib
import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


CORE_FILES = {
    "encounters": "encounters.csv",
    "conditions": "conditions.csv",
    "procedures": "procedures.csv",
    "medications": "medications.csv",
    "patients": "patients.csv",
    "providers": "providers.csv",
}

DATETIME_COLUMNS = {
    "encounters": ["start", "stop"],
    "conditions": ["start", "stop"],
    "procedures": ["date"],
    "medications": ["start", "stop"],
    "patients": ["birthdate", "deathdate"],
    "providers": [],
}

NUMERIC_COLUMNS = {
    "encounters": ["base_encounter_cost", "total_claim_cost", "payer_coverage"],
    "procedures": ["base_cost"],
    "medications": ["base_cost", "payer_coverage", "dispenses", "totalcost"],
    "patients": ["lat", "lon", "healthcare_expenses", "healthcare_coverage"],
    "providers": ["lat", "lon", "utilization"],
    "conditions": [],
}


def normalize_column_name(name: str) -> str:
    value = name.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def clean_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [normalize_column_name(c) for c in cleaned.columns]

    for col in DATETIME_COLUMNS[table_name]:
        if col in cleaned.columns:
            cleaned[col] = pd.to_datetime(cleaned[col], errors="coerce", utc=True)

    for col in NUMERIC_COLUMNS[table_name]:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    for col in cleaned.columns:
        if cleaned[col].dtype == object:
            cleaned[col] = cleaned[col].astype("string").str.strip()

    return cleaned


def deterministic_nps(encounter_id: str) -> int:
    digest = hashlib.md5((encounter_id or "").encode("utf-8")).hexdigest()
    return int(digest[:2], 16) % 11


def generate_feedback(encounters: pd.DataFrame) -> pd.DataFrame:
    feedback = encounters[["id", "patient", "provider", "start", "stop", "encounterclass", "description", "reasondescription"]].copy()
    feedback = feedback.rename(
        columns={
            "id": "consult_id",
            "patient": "patient_id",
            "provider": "clinician_id",
            "start": "consult_start",
            "stop": "consult_stop",
            "description": "consult_description",
            "reasondescription": "reason_description",
        }
    )

    feedback["consult_duration_hours"] = (
        (feedback["consult_stop"] - feedback["consult_start"]).dt.total_seconds() / 3600.0
    )

    feedback["nps_score"] = feedback["consult_id"].fillna("").map(deterministic_nps)
    feedback["nps_category"] = pd.cut(
        feedback["nps_score"],
        bins=[-1, 6, 8, 10],
        labels=["Detractor", "Passive", "Promoter"],
    ).astype("string")

    feedback["survey_response"] = feedback["nps_category"].map(
        {
            "Detractor": "Dissatisfied",
            "Passive": "Neutral",
            "Promoter": "Satisfied",
        }
    )

    feedback["complaint_flag"] = (
        (feedback["nps_score"] <= 6)
        | (feedback["consult_duration_hours"].fillna(0) > 8)
    )

    class_map = {
        "wellness": "Service quality concern",
        "ambulatory": "Wait time concern",
        "emergency": "Emergency process concern",
        "inpatient": "Continuity of care concern",
        "urgentcare": "Urgent care flow concern",
    }

    feedback["complaint_category"] = feedback.apply(
        lambda row: class_map.get((row.get("encounterclass") or "").lower(), "General complaint") if row["complaint_flag"] else "No complaint",
        axis=1,
    )

    feedback["qualitative_comment"] = feedback.apply(
        lambda row: (
            "Service was efficient and communication was clear."
            if row["nps_category"] == "Promoter"
            else "Care was acceptable but there is room for improvement."
            if row["nps_category"] == "Passive"
            else "I experienced delays and would like better follow-up."
        ),
        axis=1,
    )

    return feedback


def load_core_tables(input_dir: Path) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for table_name, file_name in CORE_FILES.items():
        file_path = input_dir / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"Missing required Synthea file: {file_path}")
        raw = pd.read_csv(file_path)
        tables[table_name] = clean_dataframe(raw, table_name)
    return tables


def export_processed(tables: dict[str, pd.DataFrame], feedback: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for table_name, frame in tables.items():
        frame.to_csv(output_dir / f"{table_name}_clean.csv", index=False)
    feedback.to_csv(output_dir / "patient_feedback_synthetic.csv", index=False)


def get_db_config() -> tuple[str, object]:
    load_dotenv()
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    pwd = os.getenv("PGPASSWORD")
    schema = os.getenv("PGSCHEMA", "digital_health")

    missing = [k for k, v in {"PGHOST": host, "PGDATABASE": db, "PGUSER": user, "PGPASSWORD": pwd}.items() if not v]
    if missing:
        raise ValueError(f"Missing environment variables for DB load: {', '.join(missing)}")

    engine = create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}")
    return schema, engine


def write_to_database(tables: dict[str, pd.DataFrame], feedback: pd.DataFrame) -> None:
    schema, engine = get_db_config()
    with engine.begin() as conn:
        conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema};")

    for table_name, frame in tables.items():
        frame.to_sql(f"raw_{table_name}", engine, schema=schema, if_exists="replace", index=False)

    feedback.to_sql("raw_patient_feedback", engine, schema=schema, if_exists="replace", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Synthea CSV data and optionally load to PostgreSQL.")
    parser.add_argument("--input-dir", required=True, help="Directory containing Synthea CSV files")
    parser.add_argument("--output-dir", default="data/processed", help="Directory for cleaned CSV outputs")
    parser.add_argument("--load-db", action="store_true", help="Load cleaned tables into PostgreSQL using .env")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    tables = load_core_tables(input_dir)
    feedback = generate_feedback(tables["encounters"])
    export_processed(tables, feedback, output_dir)

    if args.load_db:
        write_to_database(tables, feedback)

    print("Synthea ingestion complete")
    for table_name, frame in tables.items():
        print(f"{table_name}_rows: {len(frame):,}")
    print(f"patient_feedback_rows: {len(feedback):,}")


if __name__ == "__main__":
    main()
