# Runbook: Run evaluations

The eval is **deterministic** — it scores properties we can verify without an LLM judge.

## Run

```bash
competitive-intel eval --cases eval/cases.yaml
# or, in CI without the console script:
PYTHONPATH=src python eval/harness.py eval/cases.yaml
```

This runs a live brief per case and prints a table:

```
        Deterministic evaluation
┏━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━┓
┃ Company   ┃ Coverage ┃ Src valid ┃ Recency ┃ Findings ┃ Pass ┃
┡━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━┩
│ Perplexity│     100% │      100% │     86% │        7 │ PASS │
│ ...                                                          │
└───────────┴──────────┴───────────┴─────────┴──────────┴──────┘
```

## Metrics (`evaluation.py`)

| Metric | Definition |
|---|---|
| `citation_coverage` | fraction of findings backed by a resolvable citation |
| `source_validity` | fraction of cited ids that resolve to a listed source |
| `recency_adherence` | fraction of dated sources within the requested window |

A case **passes** when it produced grounded findings (`n_findings > 0`), coverage > 0, and `source_validity == 1.0`.

## Add a case

Edit `eval/cases.yaml`:

```yaml
cases:
  - company: Your Company
    focus: [funding, product]
    window: month
```

## Why not LLM-as-judge / DeepEval?

For a diligence tool the trust question is concrete and checkable: *does every claim resolve to a real, recent source?* Deterministic metrics answer that without adding a second model's opinion (and cost/variance) to the loop. The metric functions are unit-tested on synthetic briefs in `tests/test_evals_observability.py`, so the eval logic itself is verified offline.
