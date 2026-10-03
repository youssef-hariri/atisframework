# ATIS Framework — Empirical Study Package

Data and code behind the paper *"AI Technical Specificities and the ATIS Maturity Model"*
(Paper 1). The ATIS self-assessment instrument lives in this same repository (website root).

## Contents

```
study/
├── code/
│   ├── slang_hunter_v2.1.py          # Final extraction script (DeepSeek Reasoner, 4 specificity rubrics, JSON schema)
│   ├── result_combinator.py          # Aggregates the 184 result JSONs into the master matrix
│   ├── main.py                       # ATIS co-occurrence pipeline entry point
│   ├── co_occurrence_analyzer.py     # Stressor × ATIS-pillar co-occurrence analysis
│   ├── keyword_manager.py            # Dynamic keyword management
│   ├── negative_cases_analyzer.py    # Negative-case (boundary) analysis
│   ├── deepseek_client.py / config.py / view_results.py / requirements.txt
│   └── legacy/                       # slang_hunter v1.0–v2.0 (exploratory passes, kept for provenance)
└── data/
    ├── slang_results_run_2/          # 184 JSON files — the frozen extraction: 1,392 analytical units
    ├── master_qualitative_matrix.csv # 1,392 rows × 6 cols — the coded matrix reported in the paper
    ├── co-occurrence/
    │   ├── statistics.json           # Frozen co-occurrence matrix and pillar/stressor frequencies
    │   ├── co_occurrence_data.csv    # 6,166 raw stressor–pillar pairs
    │   ├── processed_quotes.csv      # 1,391 processed quotes with pillar assignments and detection method
    │   ├── negative_case_summary.csv # 279 negative cases (boundary conditions)
    │   ├── dynamic_keywords.json
    │   └── quick_report.txt
    ├── indicators/                   # The 42-code rubric (4 specificities: indicators + management frictions)
    └── legacy/slang_results_run_1/   # Exploratory run (inconsistent schema; superseded by run_2)
```

## Pipeline (how to reproduce)

1. **Extraction** — `code/slang_hunter_v2.1.py` processes the interview transcripts
   (46 transcript files covering 48 experts × 4 AI specificities = 184 analytical passes)
   against the rubric in `data/indicators/`, producing one JSON per transcript × specificity.
2. **Aggregation** — `code/result_combinator.py` merges the 184 JSONs into
   `data/master_qualitative_matrix.csv` (1,392 analytical units).
3. **Co-occurrence analysis** — `code/main.py` maps each quote to ATIS pillars
   (Act / Train / Inquire / Standardize) via hybrid LLM + keyword detection and writes
   `data/co-occurrence/`.

## Provenance notes (read before citing numbers)

- **`slang_results_run_2/` and `master_qualitative_matrix.csv` are the frozen pipeline the
  paper reports.** `data/legacy/slang_results_run_1/` was an earlier exploratory pass with an
  inconsistent output schema; it is archived for transparency only.
- Co-occurrence statistics are computed on **1,391 processed quotes**
  (`processed_quotes.csv`); the master matrix holds 1,392 rows (one additional negative-case
  row excluded at the processing stage). Percentages in the paper use the 1,391 base.
- Co-occurrence intensity is defined as observed pairs ÷ stressor quote count × 100
  (100% = parity). Verified headline values: Stochastic Uncertainty → Act **170.8%**;
  High Customer Expectations → Inquire **128.0%**; Process Disruption → Act **161.2%**;
  Autocatalysis → Standardize **98.3%**; Process Disruption → Standardize **89.6%**.
- The Stage-2 abductive scan (Make + DeepSeek Reasoner R1, 400-word segments) is described
  qualitatively in the paper; its intermediate outputs are not deposited here.

## Transcripts

The anonymized interview transcripts are **not** included in this repository out of respect
for participant privacy. They are available from the author upon reasonable request, subject
to the consent terms given at interview.

## Citation

If you use this data or code, please cite the paper and this repository
(Zenodo DOI: *to be minted on release*).
