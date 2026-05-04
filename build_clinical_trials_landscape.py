from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "NCT Number",
    "Study Title",
    "Study Status",
    "Conditions",
    "Interventions",
    "Sponsor",
    "Funder Type",
    "Study Type",
    "First Posted",
    "Locations",
}

OPTIONAL_COLUMNS = {
    "Study URL",
    "Collaborators",
    "Phases",
    "Sex",
    "Age",
    "Enrollment",
    "Start Date",
    "Primary Completion Date",
    "Completion Date",
    "Last Update Posted",
}

INACTIVE_STATUSES = {
    "TERMINATED",
    "WITHDRAWN",
    "SUSPENDED",
    "NO_LONGER_AVAILABLE",
    "TEMPORARILY_NOT_AVAILABLE",
}

FOCUS_INTERVENTION_PREFIXES = {
    "DRUG",
    "BIOLOGICAL",
    "GENETIC",
    "COMBINATION_PRODUCT",
}

EXCLUDED_INTERVENTION_PREFIXES = {
    "DEVICE",
    "BEHAVIORAL",
    "PROCEDURE",
    "DIAGNOSTIC_TEST",
    "DIETARY_SUPPLEMENT",
    "OTHER",
    "RADIATION",
}

INTERVENTION_PRIORITY = [
    "DRUG",
    "BIOLOGICAL",
    "GENETIC",
    "COMBINATION_PRODUCT",
]

HEALTHY_PATTERN = r"\bHealthy Volunteers\b|\bHealthy\b"

CONDITION_NORMALIZATION = {
    "Diabetes Mellitus, Type 2": "Type 2 Diabetes Mellitus",
    "Covid19": "COVID-19",
    "Covid-19": "COVID-19",
    "COVID19": "COVID-19",
    "Solid Tumors": "Solid Tumor",
    "Advanced Solid Tumors": "Advanced Solid Tumor",
}

COUNTRY_NORMALIZATION = {
    "Korea, Republic of": "South Korea",
    "Republic of Korea": "South Korea",
    "Korea Republic of": "South Korea",
    "Iran, Islamic Republic of": "Iran",
    "Moldova, Republic of": "Moldova",
    "Russian Federation": "Russia",
}

CHART_COLORS = {
    "primary": "#1d4ed8",
    "secondary": "#0f766e",
    "accent": "#dc2626",
    "neutral": "#475569",
}

DASHBOARD_COLUMNS = [
    "NCT Number",
    "Study Title",
    "Study Status",
    "Sponsor",
    "Phases",
    "Normalized_Conditions",
    "Primary_Condition",
    "Interventions",
    "Intervention_Type",
    "Start Year",
    "Completion Year",
    "Duration (years)",
    "Country",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a cleaned industry-sponsored clinical trials landscape from "
            "a ClinicalTrials.gov CSV export."
        )
    )
    parser.add_argument(
        "--input",
        default="raw/ctg-studies.csv",
        help="Path to the ClinicalTrials.gov CSV export.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Directory where cleaned data, summaries, and charts should be written.",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2000,
        help="Inclusive lower bound for study start year.",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2025,
        help="Inclusive upper bound for study start year.",
    )
    return parser.parse_args()


def split_pipe_separated(value: object) -> list[str]:
    if pd.isna(value):
        return []
    return [item.strip() for item in str(value).split("|") if item.strip()]


def parse_partial_date(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return pd.Timestamp(datetime.strptime(text, fmt).date())
        except ValueError:
            continue
    return pd.NaT


def extract_intervention_types(value: object) -> list[str]:
    prefixes: list[str] = []
    for item in split_pipe_separated(value):
        match = re.match(r"^\s*([A-Z_]+)\s*:", item.upper())
        prefix = match.group(1) if match else "UNSPECIFIED"
        if prefix not in prefixes:
            prefixes.append(prefix)
    return prefixes


def select_primary_intervention_type(types: list[str]) -> str | pd.NA:
    for label in INTERVENTION_PRIORITY:
        if label in types:
            return label
    if types:
        return types[0]
    return pd.NA


def normalize_condition_label(label: str) -> str:
    cleaned = re.sub(r"\s+", " ", label.strip())
    return CONDITION_NORMALIZATION.get(cleaned, cleaned)


def normalize_conditions(value: object) -> list[str]:
    normalized: list[str] = []
    for item in split_pipe_separated(value):
        label = normalize_condition_label(item)
        if label and label not in normalized:
            normalized.append(label)
    return normalized


def extract_country(value: object) -> str | pd.NA:
    if pd.isna(value):
        return pd.NA

    first_site = str(value).split("|")[0].strip()
    parts = [part.strip() for part in first_site.split(",") if part.strip()]
    if not parts:
        return pd.NA

    country = parts[-1]
    if country in {"Republic of", "Islamic Republic of", "Province of China"} and len(parts) >= 2:
        country = f"{parts[-2]}, {country}"

    return COUNTRY_NORMALIZATION.get(country, country)


def validate_columns(df: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def dataframe_records(df: pd.DataFrame) -> list[dict[str, object]]:
    return json.loads(df.to_json(orient="records"))


def ensure_optional_columns(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    for column in OPTIONAL_COLUMNS:
        if column not in work.columns:
            work[column] = pd.NA
    return work


def build_clean_dataset(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    work = ensure_optional_columns(df)

    work = work[~work["Study Status"].isin(INACTIVE_STATUSES)].copy()

    work["Intervention_Types_List"] = work["Interventions"].map(extract_intervention_types)
    work["Has_Focus_Intervention"] = work["Intervention_Types_List"].map(
        lambda items: any(item in FOCUS_INTERVENTION_PREFIXES for item in items)
    )
    work["Has_Excluded_Intervention"] = work["Intervention_Types_List"].map(
        lambda items: any(item in EXCLUDED_INTERVENTION_PREFIXES for item in items)
    )
    work = work[work["Has_Focus_Intervention"] & ~work["Has_Excluded_Intervention"]].copy()

    work = work[work["Funder Type"].fillna("").str.upper().eq("INDUSTRY")].copy()
    work = work[work["Study Type"].fillna("").str.upper().eq("INTERVENTIONAL")].copy()
    work = work.dropna(
        subset=["Phases", "Interventions", "Conditions", "Funder Type", "Study Type"]
    ).copy()

    work = work[
        ~work["Conditions"].fillna("").str.contains(HEALTHY_PATTERN, case=False, regex=True)
    ].copy()

    work["Start Date Raw"] = work["Start Date"].where(
        work["Start Date"].notna(),
        work["First Posted"],
    )
    work["Start Date Basis"] = work["Start Date"].map(
        lambda value: "START_DATE" if pd.notna(value) else "FIRST_POSTED_FALLBACK"
    )
    work["Completion Date Raw"] = work["Completion Date"].where(
        work["Completion Date"].notna(),
        work["Primary Completion Date"],
    )
    work["Completion Date Basis"] = work["Completion Date"].map(
        lambda value: "COMPLETION_DATE" if pd.notna(value) else "PRIMARY_COMPLETION_DATE_FALLBACK"
    )

    work["Start Date Parsed"] = work["Start Date Raw"].map(parse_partial_date)
    work["Completion Date Parsed"] = work["Completion Date Raw"].map(parse_partial_date)
    work["Start Year"] = work["Start Date Parsed"].dt.year
    work["Completion Year"] = work["Completion Date Parsed"].dt.year

    work = work[work["Start Year"].between(start_year, end_year, inclusive="both")].copy()

    duration_days = (
        work["Completion Date Parsed"] - work["Start Date Parsed"]
    ).dt.days
    work["Duration (months)"] = (duration_days / 30.44).round(1)
    work.loc[work["Duration (months)"] < 0, "Duration (months)"] = pd.NA
    work["Duration (years)"] = (work["Duration (months)"] / 12).round(1)

    work["Condition_List"] = work["Conditions"].map(normalize_conditions)
    work["Normalized_Conditions"] = work["Condition_List"].map("|".join)
    work["Primary_Condition"] = work["Condition_List"].map(
        lambda items: items[0] if items else pd.NA
    )
    work["Country"] = work["Locations"].map(extract_country)

    work["Intervention_Type"] = work["Intervention_Types_List"].map(
        select_primary_intervention_type
    )
    work["Intervention_Types"] = work["Intervention_Types_List"].map("|".join)
    work["Intervention_Type_Count"] = work["Intervention_Types_List"].map(len)
    work["Condition_Count"] = work["Condition_List"].map(len)

    selected_columns = [
        "NCT Number",
        "Study Title",
        "Study Status",
        "Sponsor",
        "Funder Type",
        "Study Type",
        "Phases",
        "Sex",
        "Age",
        "Enrollment",
        "Conditions",
        "Normalized_Conditions",
        "Primary_Condition",
        "Condition_Count",
        "Interventions",
        "Intervention_Type",
        "Intervention_Types",
        "Intervention_Type_Count",
        "Start Date Raw",
        "Start Date Basis",
        "Start Date Parsed",
        "Start Year",
        "Completion Date Raw",
        "Completion Date Basis",
        "Completion Date Parsed",
        "Completion Year",
        "Duration (months)",
        "Duration (years)",
        "First Posted",
        "Last Update Posted",
        "Locations",
        "Country",
    ]

    renamed = work[selected_columns].rename(
        columns={
            "Start Date Raw": "Start Date",
            "Completion Date Raw": "Completion Date",
        }
    )

    return renamed.sort_values(
        by=["Start Year", "Intervention_Type", "Study Title"],
        ascending=[True, True, True],
    )


def write_table(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


def build_summary_tables(cleaned: pd.DataFrame, output_dir: Path) -> dict[str, object]:
    trials_by_start_year = (
        cleaned.groupby("Start Year")
        .size()
        .reset_index(name="Trial Count")
        .sort_values("Start Year")
    )
    write_table(trials_by_start_year, output_dir / "trials_by_start_year.csv")

    top_conditions = (
        cleaned["Normalized_Conditions"]
        .str.split("|", regex=False)
        .explode()
        .dropna()
        .str.strip()
        .loc[lambda s: s.ne("")]
        .value_counts()
        .head(15)
        .rename_axis("Condition")
        .reset_index(name="Trial Count")
    )
    write_table(top_conditions, output_dir / "top_conditions.csv")

    top_countries = (
        cleaned["Country"]
        .dropna()
        .value_counts()
        .head(15)
        .rename_axis("Country")
        .reset_index(name="Trial Count")
    )
    write_table(top_countries, output_dir / "top_countries.csv")

    phase_mix = (
        cleaned["Phases"]
        .value_counts()
        .rename_axis("Phase")
        .reset_index(name="Trial Count")
    )
    write_table(phase_mix, output_dir / "phase_mix.csv")

    intervention_mix = (
        cleaned["Intervention_Type"]
        .value_counts()
        .rename_axis("Intervention Type")
        .reset_index(name="Trial Count")
    )
    write_table(intervention_mix, output_dir / "intervention_mix.csv")

    duration_summary = (
        cleaned["Duration (years)"]
        .dropna()
        .agg(["count", "mean", "median", "min", "max"])
        .round(2)
        .to_frame(name="Value")
        .rename_axis("Metric")
        .reset_index()
    )
    write_table(duration_summary, output_dir / "duration_summary.csv")

    summary = {
        "cleaned_trial_count": int(len(cleaned)),
        "start_year_min": int(cleaned["Start Year"].min()) if not cleaned.empty else None,
        "start_year_max": int(cleaned["Start Year"].max()) if not cleaned.empty else None,
        "top_conditions": dataframe_records(top_conditions.head(5)),
        "top_countries": dataframe_records(top_countries.head(5)),
        "intervention_mix": dataframe_records(intervention_mix),
        "phase_mix": dataframe_records(phase_mix.head(7)),
        "duration_years": {
            str(row["Metric"]): row["Value"]
            for row in dataframe_records(duration_summary)
        },
    }

    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    write_summary_markdown(summary, output_dir / "summary.md")
    return summary


def write_dashboard_dataset(cleaned: pd.DataFrame, output_dir: Path) -> None:
    dashboard_df = cleaned[DASHBOARD_COLUMNS].copy()
    dashboard_df.to_csv(output_dir / "dashboard_trials.csv", index=False)


def write_summary_markdown(summary: dict[str, object], path: Path) -> None:
    top_countries = summary.get("top_countries", [])
    top_conditions = summary.get("top_conditions", [])
    duration = summary.get("duration_years", {})

    country_lines = "\n".join(
        f"- {item['Country']}: {item['Trial Count']}"
        for item in top_countries[:5]
    )
    condition_lines = "\n".join(
        f"- {item['Condition']}: {item['Trial Count']}"
        for item in top_conditions[:5]
    )

    content = f"""# Generated Summary

## Scope

Filtered `ClinicalTrials.gov` export focused on industry-sponsored interventional studies with drug, biologic, genetic, or combination-product interventions.

## Headline Metrics

- cleaned trial count: {summary.get("cleaned_trial_count")}
- start-year window represented: {summary.get("start_year_min")} to {summary.get("start_year_max")}
- median duration in years: {duration.get("median")}
- mean duration in years: {duration.get("mean")}

## Top Countries

{country_lines or "- No country data available"}

## Top Conditions

{condition_lines or "- No condition data available"}

## Reminder

Use this summary as a starting point, not the final narrative. The public post should name the filters and caveats clearly.
"""

    path.write_text(content, encoding="utf-8")


def save_start_year_chart(cleaned: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    counts = cleaned["Start Year"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(counts.index.astype(int), counts.values, color=CHART_COLORS["primary"])
    ax.set_title("Industry-Sponsored Trial Starts by Year")
    ax.set_xlabel("Start Year")
    ax.set_ylabel("Number of Trials")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(output_dir / "trials_by_start_year.png", dpi=220)
    plt.close(fig)


def save_top_conditions_chart(cleaned: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    counts = (
        cleaned["Normalized_Conditions"]
        .str.split("|", regex=False)
        .explode()
        .dropna()
        .str.strip()
        .loc[lambda s: s.ne("")]
        .value_counts()
        .head(10)
        .sort_values()
    )

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(counts.index, counts.values, color=CHART_COLORS["secondary"])
    ax.set_title("Most Frequent Conditions in the Filtered Trial Set")
    ax.set_xlabel("Number of Trials")
    ax.set_ylabel("Condition")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(output_dir / "top_conditions.png", dpi=220)
    plt.close(fig)


def save_top_countries_chart(cleaned: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    counts = cleaned["Country"].dropna().value_counts().head(10).sort_values()

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(counts.index, counts.values, color=CHART_COLORS["accent"])
    ax.set_title("Top Countries by First Listed Trial Location")
    ax.set_xlabel("Number of Trials")
    ax.set_ylabel("Country")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(output_dir / "top_countries.png", dpi=220)
    plt.close(fig)


def save_intervention_mix_chart(cleaned: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    mix = (
        cleaned.groupby(["Start Year", "Intervention_Type"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )

    ordered_columns = [label for label in INTERVENTION_PRIORITY if label in mix.columns]
    mix = mix[ordered_columns]

    fig, ax = plt.subplots(figsize=(12, 7))
    mix.plot(kind="bar", stacked=True, ax=ax, width=0.85)
    ax.set_title("Intervention Mix by Start Year")
    ax.set_xlabel("Start Year")
    ax.set_ylabel("Number of Trials")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(title="Intervention Type", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(output_dir / "intervention_mix_by_year.png", dpi=220)
    plt.close(fig)


def save_duration_chart(cleaned: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    duration = cleaned["Duration (years)"].dropna()
    duration = duration[duration <= 15]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.hist(duration, bins=15, color=CHART_COLORS["neutral"], edgecolor="white")
    ax.set_title("Trial Duration Distribution")
    ax.set_xlabel("Duration (years)")
    ax.set_ylabel("Number of Trials")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(output_dir / "duration_distribution.png", dpi=220)
    plt.close(fig)


def save_charts(cleaned: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    plt.style.use("seaborn-v0_8-whitegrid")
    save_start_year_chart(cleaned, output_dir)
    save_top_conditions_chart(cleaned, output_dir)
    save_top_countries_chart(cleaned, output_dir)
    save_intervention_mix_chart(cleaned, output_dir)
    save_duration_chart(cleaned, output_dir)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    validate_columns(df)

    cleaned = build_clean_dataset(df, start_year=args.start_year, end_year=args.end_year)
    write_table(cleaned, output_dir / "cleaned_industry_trials.csv")
    write_dashboard_dataset(cleaned, output_dir)
    build_summary_tables(cleaned, output_dir)
    save_charts(cleaned, output_dir)

    print(f"Built clinical trials landscape with {len(cleaned):,} filtered rows.")
    print(f"Outputs written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
