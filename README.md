# Two Scales of Failure Dependence: Replication Package

Repository: https://github.com/Zhangliufeng2024/openhands-failure-dependence-replication.

This repository accompanies **“Two Scales of Failure Dependence in LLM Agent Trajectories: Step-Level Self-Excitation and Attempt-Level Clustering in 67,074 OpenHands Runs.”** It contains the analysis code, derived data, machine-readable results, figures, table extracts, and manuscript source needed to inspect and reproduce the reported analyses.

## Contents

- Analysis scripts: [`05_Replication_Package/01_code`](05_Replication_Package/01_code)
- Derived data: [`05_Replication_Package/02_derived_data`](05_Replication_Package/02_derived_data)
- Machine-readable results: [`05_Replication_Package/03_results`](05_Replication_Package/03_results)
- Environment and data provenance: [`05_Replication_Package/04_environment`](05_Replication_Package/04_environment)
- Figures: [`02_Figures`](02_Figures)
- Manuscript source: [`01_Manuscript/Manuscript_Paper3_v3.7_source.md`](01_Manuscript/Manuscript_Paper3_v3.7_source.md)

The 2.08 GB upstream corpus is not redistributed. Obtain `trajectories.parquet` from [Hugging Face](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories), revision `35455389ab51` (CC-BY-4.0), then follow [`05_Replication_Package/README.md`](05_Replication_Package/README.md). The replication README also explains why attempt order cannot be inferred from row order.

To run the numeric reconciliation against the bundled result files:

```bash
python 05_Replication_Package/01_code/final_audit.py 01_Manuscript/Manuscript_Paper3_v3.7_source.md
```

Full reproduction requires the upstream corpus and dependencies listed in the replication README.

## Citation and licenses

Please cite the accompanying manuscript. Code is released under the MIT License ([`LICENSE`](LICENSE)). Derived data and results are shared under CC-BY-4.0 with attribution to Nebius and the upstream dataset; details are in the replication README and provenance file. The upstream corpus remains hosted by its provider and is not included here.
