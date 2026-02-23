from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


st.set_page_config(page_title="Clinical Ops & Patient Experience", page_icon="🏥", layout="wide")


ENCOUNTER_COLORS = {
    "ambulatory": "#1f77b4",
    "emergency": "#d62728",
    "inpatient": "#9467bd",
    "wellness": "#2ca02c",
    "urgentcare": "#ff7f0e",
}


NPS_COLORS = {
    "avg_nps": "#1f77b4",
    "complaints": "#d62728",
}


@st.cache_resource
def get_engine():
    load_dotenv()
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE", "clinical_ops_mel")
    user = os.getenv("PGUSER", "postgres")
    pwd = os.getenv("PGPASSWORD", "")

    if not pwd:
        st.error("PGPASSWORD is missing. Add DB settings in .env and restart.")
        st.stop()

    db_url = URL.create(
        drivername="postgresql+psycopg2",
        username=user,
        password=pwd,
        host=host,
        port=int(port),
        database=db,
        query={"sslmode": "require", "channel_binding": "require"},
    )
    return create_engine(db_url)


@st.cache_data(ttl=300)
def run_query(sql_text: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql_query(text(sql_text), conn)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    consultations = run_query("SELECT * FROM digital_health.vw_consultation_clinical_records")
    ops = run_query("SELECT * FROM digital_health.vw_operations_monthly")
    feedback = run_query("SELECT * FROM digital_health.vw_feedback_comments")

    for frame, date_cols in [
        (consultations, ["consultation_start", "consultation_end"]),
        (ops, ["month"]),
        (feedback, ["consult_start"]),
    ]:
        for col in date_cols:
            if col in frame.columns:
                frame[col] = pd.to_datetime(frame[col], errors="coerce", utc=True).dt.tz_localize(None)

    return consultations, ops, feedback


def color_map_from_classes(classes: list[str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    fallback = ["#17becf", "#bcbd22", "#8c564b", "#7f7f7f", "#e377c2"]
    fallback_index = 0
    for value in classes:
        key = (value or "").lower()
        if key in ENCOUNTER_COLORS:
            resolved[value] = ENCOUNTER_COLORS[key]
        else:
            resolved[value] = fallback[fallback_index % len(fallback)]
            fallback_index += 1
    return resolved


def summarize_consultation_insight(monthly: pd.DataFrame) -> str:
    if monthly.empty:
        return "No consultation trend insight available for current filters."
    total_by_month = monthly.groupby("month", as_index=False)["consultations"].sum().sort_values("month")
    if len(total_by_month) < 2:
        return "Insufficient month coverage to compute consultation change insight."
    delta = int(total_by_month.iloc[-1]["consultations"] - total_by_month.iloc[-2]["consultations"])
    direction = "increased" if delta > 0 else "decreased" if delta < 0 else "did not change"
    return f"Consultation volume {direction} by {abs(delta):,} in the latest month versus the previous month."


def summarize_ops_insight(ops: pd.DataFrame) -> str:
    if ops.empty:
        return "No operations insight available for current filters."
    latest_month = ops["month"].max()
    latest_slice = ops[ops["month"] == latest_month]
    if latest_slice.empty:
        return "No operations insight available for current filters."
    top_ref = latest_slice.sort_values("referral_rate_pct", ascending=False).iloc[0]
    return (
        f"In the latest month ({latest_month.date()}), highest referral rate is in "
        f"{top_ref['encounterclass']} at {top_ref['referral_rate_pct']:.1f}% "
        f"with average claim cost {top_ref['avg_claim_cost']:.2f}."
    )


def summarize_feedback_insight(summary: pd.DataFrame) -> str:
    if summary.empty:
        return "No feedback insight available for current filters."
    latest_row = summary.sort_values("month").iloc[-1]
    complaint_rate = (latest_row["complaints"] / latest_row["responses"] * 100.0) if latest_row["responses"] else 0
    return (
        f"Latest month average NPS is {latest_row['avg_nps']:.2f} with complaint rate "
        f"{complaint_rate:.1f}% across {int(latest_row['responses']):,} responses."
    )


def show_overview(consultations: pd.DataFrame, feedback: pd.DataFrame) -> None:
    st.subheader("Overview KPIs")

    total_consults = len(consultations)
    unique_patients = consultations["patient_id"].nunique()
    unique_clinicians = consultations["clinician_id"].nunique()
    referral_rate = consultations["referral_flag"].fillna(False).mean() * 100 if total_consults else 0
    avg_nps = feedback["nps_score"].mean() if not feedback.empty else 0
    complaint_rate = feedback["complaint_flag"].fillna(False).mean() * 100 if not feedback.empty else 0

    cols = st.columns(6)
    cols[0].metric("Consultations", f"{total_consults:,}")
    cols[1].metric("Unique Patients", f"{unique_patients:,}")
    cols[2].metric("Unique Clinicians", f"{unique_clinicians:,}")
    cols[3].metric("Referral Rate", f"{referral_rate:.1f}%")
    cols[4].metric("Avg NPS", f"{avg_nps:.2f}")
    cols[5].metric("Complaint Rate", f"{complaint_rate:.1f}%")


def show_consultation_tab(consultations: pd.DataFrame, class_color_map: dict[str, str]) -> None:
    st.subheader("Consultation & Clinical Records")

    trend = consultations.copy()
    trend["month"] = trend["consultation_start"].dt.to_period("M").dt.to_timestamp()
    monthly = trend.groupby(["month", "encounterclass"], dropna=False).size().reset_index(name="consultations")

    if monthly.empty:
        st.info("No consultation data found for selected filters.")
        return

    line = px.line(
        monthly,
        x="month",
        y="consultations",
        color="encounterclass",
        markers=True,
        title="Monthly consultations by encounter class",
        color_discrete_map=class_color_map,
    )
    st.plotly_chart(line, use_container_width=True)
    st.info(summarize_consultation_insight(monthly))

    display_cols = [
        "consult_id",
        "patient_id",
        "clinician_id",
        "consultation_start",
        "consultation_end",
        "encounterclass",
        "diagnosis",
        "treatment",
        "referral_flag",
        "referral_reason",
    ]
    with st.expander("Show underlying consultation records"):
        st.dataframe(consultations[display_cols], use_container_width=True, height=420)


def show_feedback_tab(feedback: pd.DataFrame) -> None:
    st.subheader("Patient Satisfaction & Feedback")

    monthly = feedback.copy()
    monthly["month"] = monthly["consult_start"].dt.to_period("M").dt.to_timestamp()
    summary = monthly.groupby("month", dropna=False).agg(
        responses=("consult_id", "count"),
        avg_nps=("nps_score", "mean"),
        complaints=("complaint_flag", "sum"),
    ).reset_index()

    if summary.empty:
        st.info("No feedback data found for selected filters.")
        return

    col1, col2 = st.columns(2)
    with col1:
        chart_nps = px.line(
            summary,
            x="month",
            y="avg_nps",
            markers=True,
            title="Average NPS over time",
            color_discrete_sequence=[NPS_COLORS["avg_nps"]],
        )
        st.plotly_chart(chart_nps, use_container_width=True)

    with col2:
        chart_complaints = px.bar(
            summary,
            x="month",
            y="complaints",
            title="Complaints over time",
            color_discrete_sequence=[NPS_COLORS["complaints"]],
        )
        st.plotly_chart(chart_complaints, use_container_width=True)

    st.info(summarize_feedback_insight(summary))

    cat = feedback.groupby("complaint_category", dropna=False).size().reset_index(name="count").sort_values("count", ascending=False)
    cat_chart = px.bar(cat.head(10), x="complaint_category", y="count", title="Top complaint categories")
    st.plotly_chart(cat_chart, use_container_width=True)

    with st.expander("Show underlying feedback rows"):
        st.dataframe(feedback, use_container_width=True, height=360)


def show_comments_tab(feedback: pd.DataFrame) -> None:
    st.subheader("Qualitative Comments Explorer")

    category_filter = st.multiselect(
        "Complaint category",
        options=sorted(feedback["complaint_category"].dropna().unique().tolist()),
        default=sorted(feedback["complaint_category"].dropna().unique().tolist())[:5],
    )

    working = feedback.copy()
    if category_filter:
        working = working[working["complaint_category"].isin(category_filter)]

    st.info(f"Showing {len(working):,} comments for selected complaint categories.")

    st.dataframe(
        working[
            [
                "consult_id",
                "consult_start",
                "encounterclass",
                "nps_score",
                "survey_response",
                "complaint_category",
                "qualitative_comment",
            ]
        ],
        use_container_width=True,
        height=440,
    )


def main() -> None:
    st.title("Clinical Operations & Patient Experience Dashboard")
    st.markdown(
        "Data source: [Synthea open CSV dataset](https://synthetichealth.github.io/synthea/) + synthetic feedback generator"
    )

    with st.expander("How to read this dashboard", expanded=True):
        st.markdown(
            """
This dashboard helps answer four operational questions:
1. How consultation volume and class mix are changing over time.
2. Where referral intensity and claim cost pressure are highest.
3. How patient experience (NPS and complaints) is trending.
4. Which complaint categories and comments need attention.
            """
        )

    consultations, ops, feedback = load_data()

    with st.sidebar:
        st.header("Global Filters")

        classes = sorted([c for c in consultations["encounterclass"].dropna().unique().tolist()])
        selected_classes = st.multiselect("Encounter class", options=classes, default=classes)

        min_date = consultations["consultation_start"].min()
        max_date = consultations["consultation_start"].max()

        date_range = st.date_input(
            "Consultation date range",
            value=(min_date.date() if pd.notna(min_date) else None, max_date.date() if pd.notna(max_date) else None),
        )

    badge_cols = st.columns(4)
    badge_cols[0].metric("Encounter Classes", f"{len(classes)}")
    badge_cols[1].metric("Date Start", f"{min_date.date() if pd.notna(min_date) else '-'}")
    badge_cols[2].metric("Date End", f"{max_date.date() if pd.notna(max_date) else '-'}")
    badge_cols[3].metric("Selected Classes", f"{len(selected_classes)}")

    if selected_classes:
        consultations = consultations[consultations["encounterclass"].isin(selected_classes)]
        ops = ops[ops["encounterclass"].isin(selected_classes)]
        feedback = feedback[feedback["encounterclass"].isin(selected_classes)]

    if isinstance(date_range, tuple) and len(date_range) == 2 and date_range[0] and date_range[1]:
        start_ts = pd.Timestamp(date_range[0])
        end_ts = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
        consultations = consultations[
            (consultations["consultation_start"] >= start_ts)
            & (consultations["consultation_start"] < end_ts)
        ]
        feedback = feedback[(feedback["consult_start"] >= start_ts) & (feedback["consult_start"] < end_ts)]
        start_month = start_ts.to_period("M").to_timestamp()
        end_month = (end_ts - pd.Timedelta(days=1)).to_period("M").to_timestamp()
        ops = ops[(ops["month"] >= start_month) & (ops["month"] <= end_month)]

    class_color_map = color_map_from_classes(classes)

    show_overview(consultations, feedback)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Overview & Consultations",
        "Operations Performance",
        "Experience Signals",
        "Comment Explorer",
    ])

    with tab1:
        show_consultation_tab(consultations, class_color_map)

    with tab2:
        st.subheader("Operations Monitoring")
        if ops.empty:
            st.info("No operations data for selected filters.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                ref_chart = px.line(
                    ops,
                    x="month",
                    y="referral_rate_pct",
                    color="encounterclass",
                    markers=True,
                    title="Referral rate by month",
                    color_discrete_map=class_color_map,
                )
                st.plotly_chart(ref_chart, use_container_width=True)
            with c2:
                cost_chart = px.line(
                    ops,
                    x="month",
                    y="avg_claim_cost",
                    color="encounterclass",
                    markers=True,
                    title="Average claim cost by month",
                    color_discrete_map=class_color_map,
                )
                st.plotly_chart(cost_chart, use_container_width=True)
            st.info(summarize_ops_insight(ops))
            with st.expander("Show underlying operations metrics"):
                st.dataframe(ops, use_container_width=True, height=380)

    with tab3:
        show_feedback_tab(feedback)

    with tab4:
        show_comments_tab(feedback)

    st.download_button(
        label="Download filtered consultation records",
        data=consultations.to_csv(index=False).encode("utf-8"),
        file_name="consultation_records_filtered.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
