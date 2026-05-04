from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html

from build_clinical_trials_landscape import (
    INTERVENTION_PRIORITY,
    build_clean_dataset,
    validate_columns,
)


BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_PATH = BASE_DIR / "raw" / "ctg-studies.csv"
OUTPUT_DIR = BASE_DIR / "output"
DASHBOARD_DATA_PATH = OUTPUT_DIR / "dashboard_trials.csv"
CLEANED_DATA_PATH = OUTPUT_DIR / "cleaned_industry_trials.csv"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"
DEFAULT_START_YEAR = 2000
DEFAULT_END_YEAR = 2025
CHART_HEIGHT = 360

PALETTE = {
    "teal": "#0f766e",
    "navy": "#1d4ed8",
    "copper": "#b45309",
    "rose": "#be123c",
    "plum": "#7c3aed",
    "ink": "#172033",
    "muted": "#64748b",
    "paper": "#fffdf9",
    "line": "#d8d2c6",
}

PHASE_ORDER = [
    "EARLY_PHASE1",
    "PHASE1",
    "PHASE1|PHASE2",
    "PHASE2",
    "PHASE2|PHASE3",
    "PHASE3",
    "PHASE4",
]


def load_project_summary() -> dict[str, object]:
    if not SUMMARY_PATH.exists():
        return {}
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def load_dashboard_dataset() -> tuple[pd.DataFrame | None, str | None]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if DASHBOARD_DATA_PATH.exists():
        df = pd.read_csv(DASHBOARD_DATA_PATH)
        return prepare_dashboard_dataset(df), None

    if CLEANED_DATA_PATH.exists():
        df = pd.read_csv(CLEANED_DATA_PATH)
        return prepare_dashboard_dataset(df), None

    if RAW_DATA_PATH.exists():
        raw_df = pd.read_csv(RAW_DATA_PATH)
        validate_columns(raw_df)
        cleaned = build_clean_dataset(
            raw_df,
            start_year=DEFAULT_START_YEAR,
            end_year=DEFAULT_END_YEAR,
        )
        cleaned.to_csv(CLEANED_DATA_PATH, index=False)
        return prepare_dashboard_dataset(cleaned), None

    return None, (
        "No dataset found yet. Place the ClinicalTrials.gov export at "
        f"{RAW_DATA_PATH} or run the analysis script to generate "
        f"{DASHBOARD_DATA_PATH}."
    )


def prepare_dashboard_dataset(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()

    for column in ("Start Date Parsed", "Completion Date Parsed"):
        if column in work.columns:
            work[column] = pd.to_datetime(work[column], errors="coerce")

    for column in ("Start Year", "Completion Year"):
        work[column] = pd.to_numeric(work[column], errors="coerce").astype("Int64")

    for column in ("Duration (months)", "Duration (years)", "Enrollment"):
        work[column] = pd.to_numeric(work[column], errors="coerce")

    work["Country"] = work["Country"].fillna("Unspecified")
    work["Intervention_Type"] = work["Intervention_Type"].fillna("Unspecified")
    work["Phases"] = work["Phases"].fillna("Unspecified")
    work["Sponsor"] = work["Sponsor"].fillna("Unspecified")
    work["Normalized_Conditions"] = work["Normalized_Conditions"].fillna("")
    work["Primary_Condition"] = work["Primary_Condition"].fillna("")
    work["Condition_List"] = work["Normalized_Conditions"].str.split("|", regex=False)
    work["Primary_Condition_Label"] = work["Primary_Condition"].where(
        work["Primary_Condition"].str.strip().ne(""),
        work["Condition_List"].str[0],
    )
    work["Primary_Condition_Label"] = work["Primary_Condition_Label"].fillna("Unspecified")
    work["Study URL"] = work["NCT Number"].map(
        lambda nct: f"https://clinicaltrials.gov/study/{nct}"
    )
    work["Condition_Search_Text"] = work["Normalized_Conditions"].str.lower()

    return work


def explode_conditions(df: pd.DataFrame) -> pd.DataFrame:
    exploded = df.assign(
        Condition=df["Normalized_Conditions"].fillna("").str.split("|", regex=False)
    ).explode("Condition")
    exploded["Condition"] = exploded["Condition"].fillna("").str.strip()
    exploded = exploded[exploded["Condition"].ne("")]
    return exploded


def build_empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        x=0.5,
        y=0.5,
        text=message,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16, "color": PALETTE["muted"]},
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 24, "r": 24, "t": 56, "b": 24},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def style_figure(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Aptos, Segoe UI, Helvetica Neue, Arial, sans-serif", "color": PALETTE["ink"]},
        title_font={"size": 18},
        margin={"l": 24, "r": 24, "t": 64, "b": 28},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "title": {"text": ""},
        },
    )
    fig.update_xaxes(
        gridcolor="rgba(100, 116, 139, 0.12)",
        zeroline=False,
        linecolor="rgba(23, 32, 51, 0.16)",
    )
    fig.update_yaxes(
        gridcolor="rgba(100, 116, 139, 0.12)",
        zeroline=False,
        linecolor="rgba(23, 32, 51, 0.16)",
    )
    return fig


def format_stat(value: float | int | str | None, *, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return f"{value:,}"
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.{digits}f}"


def top_label(series: pd.Series, fallback: str = "N/A") -> str:
    counts = series.dropna().astype(str).value_counts()
    return counts.index[0] if not counts.empty else fallback


def ordered_phases(values: list[str]) -> list[str]:
    known = [phase for phase in PHASE_ORDER if phase in values]
    remaining = sorted(phase for phase in values if phase not in known)
    return known + remaining


def filter_trials(
    df: pd.DataFrame,
    year_range: list[int] | tuple[int, int],
    countries: list[str] | None,
    phases: list[str] | None,
    intervention_types: list[str] | None,
    condition_query: str | None,
) -> pd.DataFrame:
    filtered = df.copy()

    start_year, end_year = year_range
    filtered = filtered[
        filtered["Start Year"].between(start_year, end_year, inclusive="both")
    ].copy()

    if countries:
        filtered = filtered[filtered["Country"].isin(countries)].copy()
    if phases:
        filtered = filtered[filtered["Phases"].isin(phases)].copy()
    if intervention_types:
        filtered = filtered[
            filtered["Intervention_Type"].isin(intervention_types)
        ].copy()
    if condition_query:
        query = condition_query.strip().lower()
        if query:
            filtered = filtered[
                filtered["Condition_Search_Text"].str.contains(query, regex=False)
            ].copy()

    return filtered


def build_trial_trend_figure(filtered: pd.DataFrame) -> go.Figure:
    if filtered.empty:
        return build_empty_figure("No trials match the selected filters.")

    yearly = (
        filtered.groupby("Start Year")
        .size()
        .reset_index(name="Trial Count")
        .sort_values("Start Year")
    )
    fig = px.area(
        yearly,
        x="Start Year",
        y="Trial Count",
        markers=True,
        color_discrete_sequence=[PALETTE["navy"]],
    )
    fig.update_traces(
        line={"width": 3},
        fillcolor="rgba(29, 78, 216, 0.16)",
        hovertemplate="Start Year %{x}<br>Trials %{y}<extra></extra>",
    )
    return style_figure(fig, "Trial Starts by Year")


def build_phase_mix_figure(filtered: pd.DataFrame) -> go.Figure:
    if filtered.empty:
        return build_empty_figure("No phase mix available for the current filter set.")

    mix = (
        filtered.groupby(["Start Year", "Phases"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )
    ordered_columns = [phase for phase in PHASE_ORDER if phase in mix.columns]
    remaining = [phase for phase in mix.columns if phase not in ordered_columns]
    mix = mix[ordered_columns + remaining]

    fig = px.bar(
        mix.reset_index(),
        x="Start Year",
        y=mix.columns.tolist(),
        color_discrete_sequence=[
            PALETTE["navy"],
            PALETTE["teal"],
            PALETTE["copper"],
            PALETTE["rose"],
            PALETTE["plum"],
            "#2563eb",
            "#0f172a",
        ],
    )
    fig.update_layout(barmode="stack")
    return style_figure(fig, "Phase Mix by Start Year")


def build_top_countries_figure(filtered: pd.DataFrame) -> go.Figure:
    if filtered.empty:
        return build_empty_figure("No country distribution available for the current filters.")

    country_series = filtered.loc[filtered["Country"].ne("Unspecified"), "Country"]
    if country_series.empty:
        return build_empty_figure("No specified country values are available for the selected rows.")

    country_counts = (
        country_series
        .value_counts()
        .head(10)
        .sort_values()
        .rename_axis("Country")
        .reset_index(name="Trial Count")
    )
    fig = px.bar(
        country_counts,
        x="Trial Count",
        y="Country",
        orientation="h",
        color="Trial Count",
        color_continuous_scale=["#d9f2ee", PALETTE["teal"]],
    )
    fig.update_coloraxes(showscale=False)
    return style_figure(fig, "Top Countries by First Listed Site")


def build_top_conditions_figure(filtered: pd.DataFrame) -> go.Figure:
    if filtered.empty:
        return build_empty_figure("No condition distribution available for the current filters.")

    condition_counts = (
        explode_conditions(filtered)["Condition"]
        .value_counts()
        .head(10)
        .sort_values()
        .rename_axis("Condition")
        .reset_index(name="Trial Count")
    )
    if condition_counts.empty:
        return build_empty_figure("No normalized conditions are available for these rows.")

    fig = px.bar(
        condition_counts,
        x="Trial Count",
        y="Condition",
        orientation="h",
        color="Trial Count",
        color_continuous_scale=["#fde7d0", PALETTE["copper"]],
    )
    fig.update_coloraxes(showscale=False)
    return style_figure(fig, "Most Frequent Conditions")


def build_duration_figure(filtered: pd.DataFrame) -> go.Figure:
    duration = filtered.dropna(subset=["Duration (years)"]).copy()
    duration = duration[duration["Duration (years)"].between(0, 20, inclusive="both")]
    if duration.empty:
        return build_empty_figure("No usable duration values are available for the selected rows.")

    ordered_phases = [phase for phase in PHASE_ORDER if phase in duration["Phases"].unique()]
    remaining = [phase for phase in duration["Phases"].unique() if phase not in ordered_phases]

    fig = px.box(
        duration,
        x="Phases",
        y="Duration (years)",
        category_orders={"Phases": ordered_phases + remaining},
        color="Phases",
        color_discrete_sequence=[
            PALETTE["navy"],
            PALETTE["teal"],
            PALETTE["copper"],
            PALETTE["rose"],
            PALETTE["plum"],
            "#2563eb",
            "#0f172a",
        ],
        points=False,
    )
    fig.update_yaxes(title="Duration (years)")
    fig.update_xaxes(title="")
    return style_figure(fig, "Duration by Trial Phase")


def build_table_rows(filtered: pd.DataFrame) -> list[dict[str, object]]:
    display = filtered.sort_values(
        by=["Start Year", "Study Title"],
        ascending=[False, True],
    ).head(250)

    if display.empty:
        return []

    display = display.assign(
        NCT_Link=display["NCT Number"].map(
            lambda nct: f"[{nct}](https://clinicaltrials.gov/study/{nct})"
        ),
        Duration_Years=display["Duration (years)"].round(1),
    )

    columns = [
        "NCT_Link",
        "Study Title",
        "Sponsor",
        "Primary_Condition_Label",
        "Country",
        "Phases",
        "Intervention_Type",
        "Start Year",
        "Completion Year",
        "Duration_Years",
    ]
    return display[columns].rename(
        columns={
            "NCT_Link": "NCT Number",
            "Primary_Condition_Label": "Condition",
            "Duration_Years": "Duration (years)",
        }
    ).to_dict(orient="records")


def build_year_marks(min_year: int, max_year: int) -> dict[int, str]:
    marks: dict[int, str] = {}
    for year in range(min_year, max_year + 1):
        if year == min_year or year == max_year or year % 5 == 0:
            marks[year] = str(year)
    return marks


TRIALS_DF, LOAD_ERROR = load_dashboard_dataset()
PROJECT_SUMMARY = load_project_summary()

if TRIALS_DF is not None and not TRIALS_DF.empty:
    YEAR_MIN = int(TRIALS_DF["Start Year"].min())
    YEAR_MAX = int(TRIALS_DF["Start Year"].max())
    COUNTRY_OPTIONS = sorted(TRIALS_DF["Country"].dropna().unique().tolist())
    PHASE_OPTIONS = ordered_phases(TRIALS_DF["Phases"].dropna().unique().tolist())
    INTERVENTION_OPTIONS = [
        value for value in INTERVENTION_PRIORITY if value in TRIALS_DF["Intervention_Type"].unique()
    ]
else:
    YEAR_MIN = DEFAULT_START_YEAR
    YEAR_MAX = DEFAULT_END_YEAR
    COUNTRY_OPTIONS = []
    PHASE_OPTIONS = []
    INTERVENTION_OPTIONS = INTERVENTION_PRIORITY[:]

RAW_TRIAL_COUNT = PROJECT_SUMMARY.get("raw_trial_count")
CLEANED_TRIAL_COUNT = PROJECT_SUMMARY.get("cleaned_trial_count")
EXCLUDED_TRIAL_COUNT = PROJECT_SUMMARY.get("excluded_trial_count")
EXCLUDED_PCT = PROJECT_SUMMARY.get("excluded_pct")
FILTER_STEPS = PROJECT_SUMMARY.get("filter_steps", [])
app = Dash(__name__)
app.title = "Clinical Trials Landscape Dashboard"
server = app.server


def build_missing_data_layout(message: str) -> html.Div:
    return html.Div(
        className="dashboard-shell",
        children=[
            html.Header(
                className="hero hero-missing",
                children=[
                    html.Div(
                        className="hero-copy",
                        children=[
                            html.P("Clinical trials dashboard"),
                            html.H1("Add the dataset to unlock the dashboard"),
                            html.P(
                                message,
                                className="hero-description",
                            ),
                            html.Code(str(RAW_DATA_PATH)),
                        ],
                    )
                ],
            )
        ],
    )


def build_dashboard_layout() -> html.Div:
    return html.Div(
        className="dashboard-shell",
        children=[
            html.Header(
                className="hero",
                children=[
                    html.Div(
                        className="hero-copy",
                        children=[
                            html.P("ClinicalTrials.gov landscape"),
                            html.H1("Industry-Sponsored Clinical Trials Dashboard"),
                            html.P(
                                (
                                    "Interactive view of industry-funded interventional "
                                    "drug, biologic, genetic, and combination-product "
                                    "trials from 2000-2025."
                                ),
                                className="hero-description",
                            ),
                        ],
                    ),
                    html.Div(
                        className="hero-aside",
                        children=[
                            html.Div(
                                className="hero-aside-card hero-aside-card-primary",
                                children=[
                                    html.P("Scope"),
                                    html.Strong("Filtered registry landscape"),
                                    html.Span(
                                        "Excludes terminated, withdrawn, suspended, device-led, and healthy-volunteer-only trial rows."
                                    ),
                                ],
                            ),
                            html.Div(
                                className="hero-aside-card",
                                children=[
                                    html.P("Best use"),
                                    html.Strong("Publication-ready exploration"),
                                    html.Span(
                                        "Good for LinkedIn visuals, rapid market scans, and story-building before a deeper report."
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Section(
                className="panel filters-panel",
                children=[
                    html.Div(
                        className="panel-heading",
                        children=[
                            html.H2("Slice the trial set"),
                            html.P(
                                "Use a narrow condition keyword if you want the dashboard to focus on one disease pocket."
                            ),
                        ],
                    ),
                    html.Div(
                        className="filters-grid",
                        children=[
                            html.Div(
                                className="filter-field filter-field-wide",
                                children=[
                                    html.Label("Start year range", htmlFor="year-range"),
                                    dcc.RangeSlider(
                                        id="year-range",
                                        min=YEAR_MIN,
                                        max=YEAR_MAX,
                                        step=1,
                                        value=[YEAR_MIN, YEAR_MAX],
                                        marks=build_year_marks(YEAR_MIN, YEAR_MAX),
                                        allowCross=False,
                                    ),
                                ],
                            ),
                            html.Div(
                                className="filter-field",
                                children=[
                                    html.Label("Countries", htmlFor="country-dropdown"),
                                    dcc.Dropdown(
                                        id="country-dropdown",
                                        options=[{"label": item, "value": item} for item in COUNTRY_OPTIONS],
                                        value=[],
                                        multi=True,
                                        placeholder="Filter to one or more countries",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="filter-field",
                                children=[
                                    html.Label("Phases", htmlFor="phase-dropdown"),
                                    dcc.Dropdown(
                                        id="phase-dropdown",
                                        options=[{"label": item, "value": item} for item in PHASE_OPTIONS],
                                        value=[],
                                        multi=True,
                                        placeholder="All phases",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="filter-field",
                                children=[
                                    html.Label("Intervention types", htmlFor="intervention-dropdown"),
                                    dcc.Dropdown(
                                        id="intervention-dropdown",
                                        options=[
                                            {"label": item.replace("_", " ").title(), "value": item}
                                            for item in INTERVENTION_OPTIONS
                                        ],
                                        value=INTERVENTION_OPTIONS,
                                        multi=True,
                                        placeholder="Select intervention types",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="filter-field",
                                children=[
                                    html.Label("Condition keyword", htmlFor="condition-search"),
                                    dcc.Input(
                                        id="condition-search",
                                        type="text",
                                        debounce=True,
                                        placeholder="Examples: diabetes, asthma, breast cancer",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Section(
                className="kpi-grid",
                children=[
                    html.Article(
                        className="kpi-card",
                        children=[html.P("Filtered trials"), html.H3(id="kpi-total-trials")],
                    ),
                    html.Article(
                        className="kpi-card",
                        children=[html.P("Top country"), html.H3(id="kpi-top-country")],
                    ),
                    html.Article(
                        className="kpi-card",
                        children=[html.P("Leading phase"), html.H3(id="kpi-top-phase")],
                    ),
                    html.Article(
                        className="kpi-card",
                        children=[html.P("Median duration"), html.H3(id="kpi-median-duration")],
                    ),
                    html.Article(
                        className="kpi-card",
                        children=[html.P("Leading intervention"), html.H3(id="kpi-top-intervention")],
                    ),
                ],
            ),
            html.Section(
                className="panel narrative-strip",
                children=[html.P(id="filter-summary")],
            ),
            html.Section(
                className="methodology-grid",
                children=[
                    html.Article(
                        className="panel methodology-card methodology-card-primary",
                        children=[
                            html.P("Methodology"),
                            html.H2("How the registry was narrowed"),
                            html.Div(
                                className="methodology-metric",
                                children=[
                                    html.Strong(
                                        (
                                            f"{RAW_TRIAL_COUNT:,} rows -> {CLEANED_TRIAL_COUNT:,} filtered trials"
                                            if RAW_TRIAL_COUNT and CLEANED_TRIAL_COUNT
                                            else "ClinicalTrials.gov -> filtered dashboard set"
                                        )
                                    ),
                                    html.Span(
                                        (
                                            f"{EXCLUDED_TRIAL_COUNT:,} rows removed ({EXCLUDED_PCT}% excluded)."
                                            if EXCLUDED_TRIAL_COUNT is not None and EXCLUDED_PCT is not None
                                            else "This dashboard shows a cleaned subset rather than the full registry."
                                        )
                                    ),
                                ],
                            ),
                            html.P(
                                "This published build focuses on comparable industry-sponsored interventional drug-development records, not all studies on ClinicalTrials.gov."
                            ),
                        ],
                    ),
                    html.Article(
                        className="panel methodology-card",
                        children=[
                            html.P("Filter logic"),
                            html.H2("What was kept vs removed"),
                            html.Ul(
                                className="methodology-list",
                                children=[html.Li(step) for step in FILTER_STEPS] or [
                                    html.Li("See the project README for the current filter logic.")
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            dcc.Loading(
                type="default",
                children=[
                    html.Section(
                        className="chart-grid",
                        children=[
                            html.Article(
                                className="panel chart-card chart-card-wide",
                                children=[dcc.Graph(id="trial-trend-graph", style={"height": CHART_HEIGHT})],
                            ),
                            html.Article(
                                className="panel chart-card",
                                children=[dcc.Graph(id="phase-mix-graph", style={"height": CHART_HEIGHT})],
                            ),
                            html.Article(
                                className="panel chart-card",
                                children=[dcc.Graph(id="top-countries-graph", style={"height": CHART_HEIGHT})],
                            ),
                            html.Article(
                                className="panel chart-card",
                                children=[dcc.Graph(id="top-conditions-graph", style={"height": CHART_HEIGHT})],
                            ),
                            html.Article(
                                className="panel chart-card chart-card-wide",
                                children=[dcc.Graph(id="duration-graph", style={"height": CHART_HEIGHT})],
                            ),
                        ],
                    )
                ],
            ),
            html.Section(
                className="panel table-panel",
                children=[
                    html.Div(
                        className="panel-heading",
                        children=[
                            html.H2("Representative trial rows"),
                            html.P(id="table-summary"),
                        ],
                    ),
                    dash_table.DataTable(
                        id="trials-table",
                        columns=[
                            {"name": "NCT Number", "id": "NCT Number", "presentation": "markdown"},
                            {"name": "Study Title", "id": "Study Title"},
                            {"name": "Sponsor", "id": "Sponsor"},
                            {"name": "Condition", "id": "Condition"},
                            {"name": "Country", "id": "Country"},
                            {"name": "Phases", "id": "Phases"},
                            {"name": "Intervention Type", "id": "Intervention_Type"},
                            {"name": "Start Year", "id": "Start Year"},
                            {"name": "Completion Year", "id": "Completion Year"},
                            {"name": "Duration (years)", "id": "Duration (years)"},
                        ],
                        data=[],
                        markdown_options={"link_target": "_blank"},
                        sort_action="native",
                        filter_action="none",
                        page_size=12,
                        style_as_list_view=True,
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "fontFamily": "Aptos, Segoe UI, Helvetica Neue, Arial, sans-serif",
                            "fontSize": "14px",
                            "padding": "12px 14px",
                            "textAlign": "left",
                            "whiteSpace": "normal",
                            "height": "auto",
                            "backgroundColor": "rgba(255, 253, 249, 0.96)",
                            "color": PALETTE["ink"],
                            "border": "none",
                        },
                        style_header={
                            "backgroundColor": "#efe9dd",
                            "fontWeight": "700",
                            "color": PALETTE["ink"],
                            "borderBottom": f"1px solid {PALETTE['line']}",
                        },
                        style_data={
                            "borderBottom": "1px solid rgba(216, 210, 198, 0.45)",
                        },
                    ),
                ],
            ),
            html.Section(
                className="notes-grid",
                children=[
                    html.Article(
                        className="panel note-card",
                        children=[
                            html.H2("How to read this dashboard"),
                            html.P(
                                "Country reflects the first listed site rather than every site in a multinational trial. "
                                "Condition counts explode multi-condition rows, while the table shows a single primary label for readability."
                            ),
                        ],
                    ),
                    html.Article(
                        className="panel note-card",
                        children=[
                            html.H2("Good LinkedIn chart set"),
                            html.P(
                                "The strongest public-facing pack is usually the trial trend, top countries, top conditions, and one caveat on the filter logic."
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


app.layout = build_missing_data_layout(LOAD_ERROR) if LOAD_ERROR else build_dashboard_layout()


if TRIALS_DF is not None and not TRIALS_DF.empty:

    @app.callback(
        Output("kpi-total-trials", "children"),
        Output("kpi-top-country", "children"),
        Output("kpi-top-phase", "children"),
        Output("kpi-median-duration", "children"),
        Output("kpi-top-intervention", "children"),
        Output("filter-summary", "children"),
        Output("trial-trend-graph", "figure"),
        Output("phase-mix-graph", "figure"),
        Output("top-countries-graph", "figure"),
        Output("top-conditions-graph", "figure"),
        Output("duration-graph", "figure"),
        Output("table-summary", "children"),
        Output("trials-table", "data"),
        Input("year-range", "value"),
        Input("country-dropdown", "value"),
        Input("phase-dropdown", "value"),
        Input("intervention-dropdown", "value"),
        Input("condition-search", "value"),
    )
    def update_dashboard(
        year_range: list[int],
        countries: list[str] | None,
        phases: list[str] | None,
        intervention_types: list[str] | None,
        condition_query: str | None,
    ) -> tuple[str, str, str, str, str, str, go.Figure, go.Figure, go.Figure, go.Figure, go.Figure, str, list[dict[str, object]]]:
        filtered = filter_trials(
            TRIALS_DF,
            year_range=year_range,
            countries=countries,
            phases=phases,
            intervention_types=intervention_types,
            condition_query=condition_query,
        )

        total_trials = len(filtered)
        specified_countries = filtered.loc[filtered["Country"].ne("Unspecified"), "Country"]
        top_country = top_label(specified_countries)
        top_phase = top_label(filtered["Phases"])
        top_intervention = top_label(filtered["Intervention_Type"])
        median_duration = filtered["Duration (years)"].dropna().median()

        country_count = specified_countries.nunique()
        condition_count = explode_conditions(filtered)["Condition"].nunique()
        query_label = condition_query.strip() if condition_query else "all conditions"
        summary = (
            f"Showing {format_stat(total_trials)} trials across {format_stat(country_count)} countries "
            f"and {format_stat(condition_count)} normalized conditions. Current condition search: {query_label}."
        )

        table_rows = build_table_rows(filtered)
        table_summary = (
            f"Displaying up to 250 rows from the current filter set. Total filtered rows: {format_stat(total_trials)}."
        )

        return (
            format_stat(total_trials),
            top_country,
            top_phase.replace("|", " + "),
            f"{format_stat(median_duration)} years" if pd.notna(median_duration) else "N/A",
            top_intervention.replace("_", " ").title(),
            summary,
            build_trial_trend_figure(filtered),
            build_phase_mix_figure(filtered),
            build_top_countries_figure(filtered),
            build_top_conditions_figure(filtered),
            build_duration_figure(filtered),
            table_summary,
            table_rows,
        )


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8050"))
    app.run(debug=False, host=host, port=port)
