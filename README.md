# Industry-Sponsored Clinical Trials Landscape

This project turns a raw `ClinicalTrials.gov` CSV export into a cleaner, publishable analysis focused on how `industry-sponsored` drug development clusters by year, geography, phase, intervention type, and disease area.

Created with Codex under the direction of Gunjan Ohri.

## Best Public Framing

The most credible first story is not "all clinical trials."

It is:

`A filtered analysis of industry-sponsored drug, biologic, genetic, and combination-product trials on ClinicalTrials.gov from 2000-2026.`

That framing matches the notebook work you already did and avoids overstating what the dataset represents.

## First-Pass Scope

Included:

- industry-funded studies
- interventional studies
- studies with disclosed phases
- drug, biological, genetic, and combination-product interventions
- start years from `2000` through `2026`

Excluded:

- terminated, withdrawn, suspended, and unavailable studies
- device, behavioral, procedural, dietary supplement, diagnostic test, and radiation-led studies
- healthy-volunteer-only condition counts
- rows missing core fields required for the comparison set

## Project Files

- [build_clinical_trials_landscape.py](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/build_clinical_trials_landscape.py)
- [dashboard.py](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/dashboard.py)
- [project-brief.md](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/project-brief.md)
- [linkedin-post-draft.md](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/linkedin-post-draft.md)
- [raw/README.md](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/raw/README.md)
- [output/README.md](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/output/README.md)

## Quick Start

1. Put the ClinicalTrials.gov export at `raw/ctg-studies.csv`.
2. Install the Python packages in [requirements.txt](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/requirements.txt).
3. Run:

```bash
cd /Users/gunjan/Documents/Playground/research/clinical-trials-landscape
python3 build_clinical_trials_landscape.py
```

4. Launch the dashboard:

```bash
cd /Users/gunjan/Documents/Playground/research/clinical-trials-landscape
python3 dashboard.py
```

5. Review the generated tables, charts, and summary in [output](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/output).

## Expected Outputs

The analysis script writes:

- `cleaned_industry_trials.csv`
- `dashboard_trials.csv`
- `trials_by_start_year.csv`
- `top_conditions.csv`
- `top_countries.csv`
- `phase_mix.csv`
- `intervention_mix.csv`
- `duration_summary.csv`
- `summary.json`
- `summary.md`
- `.png` charts ready to reuse in a LinkedIn carousel or a short write-up

The dashboard shows:

- filter controls for year, geography, phase, intervention type, and condition keyword
- KPI cards for total trials, top country, leading phase, median duration, and leading intervention type
- interactive charts for trend, phase mix, country concentration, condition concentration, and duration by phase
- a searchable trial table with direct ClinicalTrials.gov links

## Methodology Notes

- Intervention parsing is based on the labeled prefixes inside the `Interventions` field such as `DRUG:` and `BIOLOGICAL:`.
- Country is inferred from the first listed location, which is useful for directional analysis but not a perfect multinational-trial geography measure.
- Conditions are normalized lightly for obvious synonym pairs such as `Diabetes Mellitus, Type 2` and `Type 2 Diabetes Mellitus`.
- Duration is calculated from parsed start and completion dates, using partial dates when only year or year-month are available.

## Good Publishable Angles

- Where industry-sponsored drug development is clustering by country
- Which disease areas attract the most trial activity
- How intervention mix changes over time
- Whether later-stage development is concentrating in a few therapeutic areas
- How trial duration differs by phase

## Important Caveats

- This is a registry-based landscape, not a full commercial pipeline database.
- The output is only as clean as the source labels in `ClinicalTrials.gov`.
- Country counts are directional because global multi-site studies can span many geographies.
- The intervention filters make this a `pharma-focused` dataset, not a full census of all clinical research activity.

## Publishing

If you want a live interactive dashboard, use a Python host such as `Render`.

`GitHub Pages` only hosts static HTML, CSS, and JavaScript, so it is a good fit for a report page but not for this Dash app. GitHub documents Pages as a static site hosting service, and Render documents Web Services for dynamic apps that bind to `0.0.0.0` on the assigned port.

Recommended deployment shape:

1. Run `python3 build_clinical_trials_landscape.py` locally.
2. Commit the smaller `output/dashboard_trials.csv` file, not the raw `421 MB` source export.
3. Push the project to GitHub.
4. Create a `Render` Web Service from the repo.
5. Use the included [render.yaml](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/render.yaml).
6. Render will install dependencies from [requirements.txt](/Users/gunjan/Documents/Playground/research/clinical-trials-landscape/requirements.txt) and start the app with Gunicorn.

Helpful docs:

- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages)
- [GitHub large file limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
- [Render Web Services](https://render.com/docs/web-services/)

## Attribution

This dashboard project was created with Codex under the direction of Gunjan Ohri.
