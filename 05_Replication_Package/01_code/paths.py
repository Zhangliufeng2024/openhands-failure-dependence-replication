# -*- coding: utf-8 -*-
"""Shared path resolution for the replication package scripts.

Paths to the corpus and to the large derived intermediates are resolved as
follows, in priority order:

  1. the environment variable PAPER3_CORPUS  -> the downloaded trajectories.parquet
  2. the environment variable PAPER3_WORK    -> directory holding regenerable
     intermediates (full_seqs.json, step_meta.json, instance_repeat.json, ...)
  3. otherwise a `work/` directory next to the package root

Shipped result files live in 05_Replication_Package/03_results and are read
directly by final_audit.py.

Example:
  set PAPER3_CORPUS=D:\\data\\trajectories.parquet
  python 01_code/extract_stream.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))   # 05_Replication_Package/
RESULTS = os.path.join(ROOT, '03_results')

DEFAULT_WORK = os.path.join(ROOT, 'work')


def work(*parts):
    """Path to a regenerable intermediate under the work directory."""
    base = os.environ.get('PAPER3_WORK') or DEFAULT_WORK
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, *parts)


def corpus():
    """Path to the source corpus, with an actionable error if it is missing."""
    p = os.environ.get('PAPER3_CORPUS') or os.path.join(DEFAULT_WORK, 'trajectories.parquet')
    if not os.path.exists(p):
        raise SystemExit(
            'corpus not found: %s\n'
            'Download trajectories.parquet from the source below and either place it in\n'
            'work/ or set PAPER3_CORPUS to its location.\n'
            '  https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories'
            % p)
    return p


def results(*parts):
    """Path to a shipped result file (05_Replication_Package/03_results)."""
    return os.path.join(RESULTS, *parts)


DEFAULT_FIGS = os.path.join(os.path.dirname(ROOT), '02_Figures')
DERIVED = os.path.join(ROOT, '02_derived_data')


def figs(*parts):
    """Path to a final paper figure (02_Figures at the project root).

    Override the destination with PAPER3_WORK-adjacent PAPER3_FIGS.
    """
    base = os.environ.get('PAPER3_FIGS') or DEFAULT_FIGS
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, *parts)


def derived(*parts):
    """Path to a shipped derived-data file (05_Replication_Package/02_derived_data).

    Override with PAPER3_DERIVED; falls back to the work directory so a
    regeneration run (see README stage 2) keeps working.
    """
    shipped = os.environ.get('PAPER3_DERIVED') or DERIVED
    p = os.path.join(shipped, *parts)
    if not os.path.exists(p):
        p = work(*parts)
    return p
