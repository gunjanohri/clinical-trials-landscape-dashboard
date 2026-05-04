# Project Brief

## Objective

Package the clinical trials notebook into a public-facing analysis that is polished enough for:

- a LinkedIn post or short carousel
- a GitHub or portfolio project
- a future dashboard or static report page

## Working Title

`Where Is Industry-Sponsored Drug Development Clustering?`

## Core Research Question

Using a filtered `ClinicalTrials.gov` export, where do industry-sponsored drug and biologic trials cluster by:

- year
- phase
- country
- intervention type
- disease area
- study duration

## Why This Is Worth Publishing

- It shows end-to-end data work on a messy real dataset.
- It is specific enough to sound credible, not just "I made some charts."
- It sits at the intersection of healthcare, biotech, analytics, and market intelligence.
- It creates a strong bridge between technical work and business interpretation.

## Recommended Deliverables

1. A reproducible analysis script that rebuilds the cleaned dataset and charts.
2. A short markdown summary with 5-8 findings.
3. A LinkedIn draft that translates the analysis into a public narrative.
4. Later: a static report page or small dashboard once the dataset and final charts are locked.

## Suggested Storyline

1. Start with the size of the raw registry.
2. Narrow to the exact filtered population you care about.
3. Show where trial activity is concentrated by country and condition.
4. Show how the intervention mix changes over time.
5. Add one methodological caveat so the post feels thoughtful, not hype-driven.

## Minimum Viable Publish Set

- `1` chart on trial activity by year
- `1` chart on top conditions
- `1` chart on top countries
- `1` short summary paragraph
- `1` LinkedIn post draft

## Upgrade Path

After the first publishable version:

- normalize more disease synonyms
- improve country extraction for multinational studies
- compare phase distributions by therapeutic area
- add sponsor-level leaderboards
- build a small interactive view for disease or country filters
