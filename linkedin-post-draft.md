# LinkedIn Post Draft

## Version A

I recently built a first-pass analysis of `ClinicalTrials.gov` focused on a narrower question:

`Where is industry-sponsored drug development clustering?`

Instead of treating the registry as one giant bucket, I filtered the dataset to focus on:

- industry-funded studies
- interventional trials
- drug, biologic, genetic, and combination-product interventions
- disclosed phases
- studies starting between `2000` and `2025`

A few patterns stood out:

1. Trial activity appears heavily concentrated in a handful of geographies, especially the `United States`, `United Kingdom`, and `China`, with strong additional activity in `Japan` and `South Korea`.
2. On the disease side, large recurring clusters include `Type 2 Diabetes Mellitus`, `Asthma`, `Breast Cancer`, `Hypertension`, `Rheumatoid Arthritis`, and `Schizophrenia`.
3. In the more recent `2015-2025` window, `COVID-19` clearly shows up as a major temporary demand shock in the registry.
4. Within this filtered dataset, `DRUG` studies dominate, while `BIOLOGICAL`, `GENETIC`, and `COMBINATION_PRODUCT` programs form smaller but still meaningful slices.
5. Trial durations appear to cluster heavily in the `0-2 year` range, although that result depends on how partial dates are recorded in the registry.

The main lesson for me was methodological:

Cleaning choices change the story a lot.
A project like this becomes much more useful once you define exactly what is in scope and what is not.

Next step is turning the notebook into a cleaner dashboard and short write-up.

## Version B

I’ve been turning a rough clinical trials notebook into a more publishable research project.

The dataset starts huge, but the more interesting question is not "what does all of ClinicalTrials.gov say?"

It is:

`What does industry-sponsored drug development look like when you clean the registry into a comparable subset?`

For the first pass, I filtered the data to:

- active or completed studies
- interventional programs
- industry-funded trials
- drug, biologic, genetic, and combination-product interventions
- studies with disclosed phases
- start years from `2000-2025`

Some early observations:

- The `United States` remains the anchor geography, but `United Kingdom`, `China`, `Japan`, and `South Korea` also show strong trial activity in the filtered set.
- Conditions such as `Type 2 Diabetes Mellitus`, `Asthma`, `Breast Cancer`, `Hypertension`, and `Rheumatoid Arthritis` appear repeatedly near the top.
- `COVID-19` becomes much more visible when narrowing to the `2015-2025` window.
- Trial durations skew short in a simple registry-based calculation, which is interesting but also a reminder to handle partial dates carefully.

The most useful takeaway was not just the output charts.
It was seeing how much the narrative depends on explicit scope, normalization, and filtering decisions.

That makes this kind of project a nice bridge between analytics, healthcare data, and research communication.

If useful, I can share the methodology and the cleaned chart set once I finish the public-facing version.
