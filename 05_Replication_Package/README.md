# Replication Package

**Paper:** Two Scales of Failure Dependence in LLM Agent Trajectories:
Step-Level Self-Excitation and Attempt-Level Clustering in 67,074 OpenHands Runs
**Version:** v3.7 ｜ **Date:** 2026-09-26
**Target:** Empirical Software Engineering special issue “Agentic Software Engineering: The Rise of AI Teammates”

---

## Contents

| Directory | Contents | Files |
|---|---|---|
| `01_code` | Analysis, figure, and document-build scripts | 28 |
| `02_derived_data` | Derived data that cannot be cheaply regenerated | 4 |
| `03_results` | Machine-readable outputs of every script | 11 |
| `04_environment` | Environment spec and data provenance | — |

---

## Not included, and why

| File | Size | Reason |
|---|---|---|
| `trajectories.parquet` | 2.08 GB | Third-party data (Nebius, CC-BY-4.0). Obtain from the source below; we cannot redistribute it. |
| `full_seqs.json` | 43.2 MB | Regenerable by `extract_stream.py` (~22 min). |
| `step_meta.json` | 53.1 MB | Regenerable by `extract_meta.py`. |

Because the raw corpus is openly available and both large intermediates are
byte-for-byte reproducible from it, the package is self-contained for the
purposes of reproduction: no step requires data we withhold.

---

## Source data

**`nebius/SWE-rebench-openhands-trajectories`**
- Landing page: https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories
- Mirror used: https://www.modelscope.cn/datasets/nebius/SWE-rebench-openhands-trajectories
- Revision: `35455389ab51` (last modified 2025-12-27)
- License: CC-BY-4.0
- File: `trajectories.parquet`, byte length 2,079,503,354, 67,074 rows
- Collection conditions: OpenHands v0.54.0 + Qwen3-Coder-480B-A35B-Instruct
- Coverage: 1,823 repositories, 3,792 real-world issues

We verified that the mirror's byte length matches the `x-linked-size` reported by
the Hugging Face API exactly, confirming an identical object was served.

---

## Reproduction

### Environment

```bash
python3 -m pip install "pyarrow>=14" "numpy>=1.26" "pandas>=2.0" \
                        "matplotlib>=3.8" "python-docx>=1.1"
```

Tested on Python 3.11, Linux x86–64.

### Full chain

Set `PAPER3_CORPUS` to the downloaded `trajectories.parquet` (or place it in
`work/`; large intermediates are written there, see `01_code/paths.py`).

```bash
# ---- Stage 1: extraction -------------------------------------------------
python3 01_code/extract_stream.py    # -> full_seqs.json   (~22 min)
python3 01_code/extract_meta.py      # -> step_meta.json   (command types, call linkage)

# ---- Stage 2: attempt-axis input -----------------------------------------
# instance_repeat.json maps each instance_id to its attempt count and per-attempt
# outcomes. Stream ALL 17 row groups.
#   expected log:  DONE unique_instances 6306 rows 67074
# (this file is shipped in 02_derived_data, so this step is optional)

# ---- Stage 3: core statistics --------------------------------------------
python3 01_code/analyze_full.py      # -> analysis_results.json
python3 01_code/validate.py          # -> validation_results.json

# ---- Stage 4: the two main results ---------------------------------------
# Step axis
python3 01_code/decompose.py         # -> decompose_results.json
python3 01_code/label_check.py       # -> label_validity.json
python3 01_code/editor_label.py      # -> editor_label.json
python3 01_code/hawkes_test.py       # -> hawkes_vs_ar1.json
python3 01_code/hawkes_params.py     # -> hawkes_params.json
python3 01_code/alt_explain.py
# Positional chain (documented retraction; see manuscript Section 4.4)
python3 01_code/check_positional.py
python3 01_code/positional2.py
python3 01_code/conditional.py
python3 01_code/simpson.py           # -> simpson.json
python3 01_code/positional_final.py  # -> positional_final.json
# Attempt axis
python3 01_code/attempt_axis.py      # -> attempt_axis.json

# ---- Stage 5: figures ----------------------------------------------------
python3 01_code/make_figs.py         # Figures 1, 2, 3, 5  (300 dpi)
python3 01_code/make_fig5.py         # Figure 4  (Simpson's paradox)
python3 01_code/make_fig6.py         # Figure 6  (attempt axis)

# ---- Stage 6: numeric reconciliation and document build -----------------
python3 01_code/final_audit.py
#   expected:  数值核对失败: 0 / 83
python3 01_code/build_docx.py        # -> 01_Manuscript/Manuscript_Paper3_v3.7.docx
python3 01_code/extract_tables.py    # -> 03_Tables/Table01..18.txt
```

Every random seed is fixed inside the scripts. Total runtime for the full chain,
excluding the 2.08 GB download, is roughly 30 minutes on a single machine.

---

## Expected key values

Use these to check that reproduction succeeded.

| Quantity | Expected | Output file |
|---|---|---|
| Trajectories | 67,074 | `attempt_axis.json` |
| **Distinct tasks** | **6,306** | `attempt_axis.json` |
| Mean attempts per task | 10.64 (max 34) | `attempt_axis.json` |
| Pooled lag-1 OR | 1.567 | `validation_results.json` |
| Within-trajectory OR | 1.573 | `validation_results.json` |
| Between-trajectory multiplier | 0.996 | `validation_results.json` |
| Step-level ICC | 0.054 | `analysis_results.json` |
| Design effect | 4.164 | `validation_results.json` |
| Same-tool OR (bash / editor) | 1.485 / 1.921 | `analysis_results.json` |
| Cross-tool OR | 1.258 / 1.032 | `analysis_results.json` |
| Memory half-life (steps) | 10.2 / 4.8 | `hawkes_params.json` |
| **Attempt-axis dispersion φ** | **8.71** (z = 431.9) | `attempt_axis.json` |
| φ, repo difficulty absorbed | 8.60 | `attempt_axis.json` |
| φ, runtime failures removed | 8.88 | `attempt_axis.json` |
| **Attempt-level ICC** | **0.797** | `attempt_axis.json` |
| All-failure / all-success tasks | 2,441 / 1,990 | `attempt_axis.json` |
| Repositories spanned by all-failure tasks | 917 | `attempt_axis.json` |
| editor strict-label precision | 0.113 | `editor_label.json` |
| Strictly judged adjacent editor pairs | 545,446 | `editor_label.json` |
| bash lenient-label precision | 0.492 | `validation_results.json` |

---

## ⚠️ Two traps a re-user will otherwise fall into

### Trap 1: row order is not attempt order

`trajectory_id` is an opaque hash carrying no timestamp, so repeated attempts at
one task are **not adjacent**. For example `PlasmaFAIR__sdf-xarray-24` appears at
row 0 and row 2,398.

**Consequence.** Any statistic keyed on "the previous attempt" is meaningless
here. Computing one naively on row order yields

```
P(success | "previous" attempt failed) = 0.0992
P(success | "previous" attempt succeeded) = 0.8936
ratio = 0.111
```

which looks like a nine-fold cascade and is **pure artifact**.

**Further consequence.** CCRM's ε₁/ε₀ = 7.1× is therefore **not
computable** on this corpus: it conditions on "the first attempt having failed",
and attempt order is unrecoverable. `attempt_axis.py` records this trap in its
comments, and the manuscript states it in Section 5.

### Trap 2: de-duplicating on `trajectory_id` destroys the attempt structure

`trajectory_id` has 67,074 unique values — one per row — so de-duplicating on it
appears to confirm "67,074 tasks". The actual instance identifier, `instance_id`,
has only **6,306** unique values.

An earlier version of this manuscript fell into this trap and erroneously
asserted that the corpus had no attempt axis. The error, its cause, and the
results it had suppressed are documented in the manuscript's Appendix B and in
Section 5.

---

## Licensing

- **Code** (`01_code`): MIT License.
- **Derived data and results** (`02_derived_data`, `03_results`): CC-BY-4.0,
  inherited from the source corpus.
- **Upstream corpus**: CC-BY-4.0, © Nebius. Not redistributed here.

---

## Verification of this package

| Check | Result |
|---|---|
| Numeric reconciliation (`final_audit.py`) | all listed manuscript values are compared with the bundled measured values and tolerances |
| Figures | 6, all 6.30 in wide at 300 dpi, RGB (meets the ≥300 dpi colour requirement) |
| Tables | 18, contiguous numbering, all bodies present |
| Tables/figures cross-referenced in the manuscript | consistent |

---

## Contact

Liufeng Zhang, College of Science and Technology, Ningbo University, Ningbo 315300, Zhejiang Province, China — zhangliufeng@nbu.edu.cn
