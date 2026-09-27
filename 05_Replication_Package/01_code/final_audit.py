#!/usr/bin/env python3
"""Cell-level audit of the submission manuscript and its bundled attempt data.

Checks that all 18 Markdown tables have complete, ordered rows and that the
Word tables preserve the same cell positions. Table 16 is additionally checked
against the task-level derived data and the length-conditioned null in JSON.
"""
import json
import math
import os
import re
import sys
from pathlib import Path

from docx import Document
from paths import results

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MD = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '01_Manuscript' / 'Manuscript_EMSE_Submission_Ready.md'
DOCX = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / '01_Manuscript' / 'Manuscript_EMSE_Submission_Ready.docx'
ATTEMPT = json.load(open(results('attempt_axis.json'), encoding='utf-8'))


def split_row(line):
    return [part.strip() for part in re.split(r'\s{2,}', line.strip()) if part.strip()]


def parse_tables(text):
    lines = text.splitlines()
    tables = []
    i = 0
    while i < len(lines):
        if not re.match(r'^Table \d+\.', lines[i].strip()) or i + 1 >= len(lines) or not lines[i + 1].strip() or not set(lines[i + 1].strip()) <= set('-='):
            i += 1
            continue
        caption = lines[i].strip()
        number = int(re.match(r'^Table (\d+)\.', caption).group(1))
        i += 2
        groups, current = [], []
        while i < len(lines) and lines[i].strip():
            if set(lines[i].strip()) <= set('-='):
                if current:
                    groups.append(current)
                    current = []
            else:
                current.append(lines[i].rstrip())
            i += 1
        if current:
            groups.append(current)
        if not groups:
            raise ValueError(f'Table {number} is empty')
        ncols = len(split_row(groups[0][-1]))
        headers = []
        for line in groups[0]:
            values = split_row(line)
            if len(values) == ncols:
                headers.append((values, 1))
            elif values and ncols % len(values) == 0:
                headers.append((values, ncols // len(values)))
            else:
                raise ValueError(f'Table {number} header does not resolve to {ncols} columns: {line!r}')
        data, notes = [], []
        for group in groups[1:]:
            for line in group:
                values = split_row(line)
                if len(values) == 1 and not line.startswith(' '):
                    notes.append(values[0])
                    continue
                if len(values) != ncols:
                    raise ValueError(f'Table {number} row has {len(values)} cells, expected {ncols}: {line!r}')
                data.append(values)
        tables.append((number, caption, headers, data, notes))
    return tables


def normalize(value):
    value = re.sub(r'`([^`]*)`', r'\1', value)
    value = re.sub(r'\*([^*]+)\*', r'\1', value)
    value = re.sub(r'\^\{([^}]*)\}', r'\1', value)
    value = re.sub(r'_\{([^}]*)\}', r'\1', value)
    return re.sub(r'\s+', ' ', value).strip()


text = MD.read_text(encoding='utf-8')
source_tables = parse_tables(text)
doc = Document(DOCX)
errors = []
if len(source_tables) != 18:
    errors.append(f'Markdown contains {len(source_tables)} tables; expected 18')
if len(doc.tables) != len(source_tables):
    errors.append(f'DOCX contains {len(doc.tables)} tables; Markdown contains {len(source_tables)}')

for idx, (number, caption, headers, data, notes) in enumerate(source_tables):
    if idx >= len(doc.tables):
        break
    table = doc.tables[idx]
    actual_rows = table.rows
    expected_row_count = len(headers) + len(data)
    if len(actual_rows) != expected_row_count:
        errors.append(f'Table {number}: DOCX has {len(actual_rows)} rows; source has {expected_row_count}')
        continue
    for ri, (values, span) in enumerate(headers):
        actual = [cell.text for cell in actual_rows[ri].cells]
        actual = [actual[j * span] for j in range(len(values))] if span > 1 else actual
        expected = values
        if [normalize(v) for v in actual] != [normalize(v) for v in expected]:
            errors.append(f'Table {number}, header row {ri + 1}: DOCX cells differ from source: {actual!r} != {expected!r}')
    for di, expected in enumerate(data):
        ri = len(headers) + di
        actual = [cell.text for cell in actual_rows[ri].cells]
        if [normalize(v) for v in actual] != [normalize(v) for v in expected]:
            errors.append(f'Table {number}, data row {di + 1}: DOCX cells differ from source: {actual!r} != {expected!r}')
    if not data:
        errors.append(f'Table {number} has a header but no data rows')

# Reconcile every Table 16 cell with counts recomputed from the derived task data.
t16 = next((item for item in source_tables if item[0] == 16), None)
if t16 is None:
    errors.append('Table 16 is missing')
else:
    rows = ATTEMPT.get('u_shape', [])
    table_rows = t16[3]
    if len(table_rows) != len(rows):
        errors.append(f'Table 16 has {len(table_rows)} data rows; result JSON has {len(rows)}')
    for i, (cells, result) in enumerate(zip(table_rows, rows)):
        bin_label, observed, expected, ratio = cells
        if bin_label != result['bin']:
            errors.append(f'Table 16 row {i + 1}: bin {bin_label!r} != result {result["bin"]!r}')
        if int(observed.replace(',', '')) != result['obs']:
            errors.append(f'Table 16 row {bin_label}: observed count mismatch')
        if not math.isclose(float(expected.replace(',', '')), result['exp'], abs_tol=0.0051):
            errors.append(f'Table 16 row {bin_label}: expected count mismatch')
        if not math.isclose(float(ratio), result['ratio'], abs_tol=0.0051):
            errors.append(f'Table 16 row {bin_label}: observed/expected ratio mismatch')
    if sum(row['obs'] for row in rows) != ATTEMPT['n5']:
        errors.append('Table 16 observed counts do not sum to n5')
    if not math.isclose(sum(row['exp'] for row in rows), ATTEMPT['n5'], abs_tol=1e-7):
        errors.append('Table 16 expected counts do not sum to n5')
    if ATTEMPT['all_fail_tasks'] != 2441 or ATTEMPT['all_succ_tasks'] != 1990:
        errors.append('Task-level all-failure/all-success counts disagree with derived results')
    if not math.isclose(ATTEMPT['all_fail_expected'], 27.8024385289443, abs_tol=1e-9):
        errors.append('All-failure expectation differs from the length-conditioned recomputation')
    if not math.isclose(ATTEMPT['all_succ_expected'], 15.868738566558523, abs_tol=1e-9):
        errors.append('All-success expectation differs from the length-conditioned recomputation')
    normalized_text = re.sub(r'\s+', ' ', text)
    if not re.search(r'expected counts are 27\.80 \(0\.45%\) and 15\.87 \(0\.26%\)', normalized_text):
        errors.append('Manuscript prose does not state the reconciled all-failure/all-success expectations')
    if '0.08%' in text or '522.20' in text or '995.00' in text:
        errors.append('Manuscript retains a superseded Table 16 benchmark/value')

print(f'Markdown tables parsed: {len(source_tables)}')
print(f'DOCX tables checked cell-by-cell: {min(len(doc.tables), len(source_tables))}')
print(f'Table 16: {len(ATTEMPT.get("u_shape", []))} bins; observed total {sum(r["obs"] for r in ATTEMPT["u_shape"]):,}; expected total {sum(r["exp"] for r in ATTEMPT["u_shape"]):,.2f}')
print(f'Length-conditioned extremes: all-failure {ATTEMPT["all_fail_tasks"]:,}/{ATTEMPT["all_fail_expected"]:.2f} expected; all-success {ATTEMPT["all_succ_tasks"]:,}/{ATTEMPT["all_succ_expected"]:.2f} expected')
if errors:
    for error in errors:
        print('FAIL:', error)
    raise SystemExit(1)
print('PASS: every source table cell matches the corresponding DOCX cell; Table 16 matches derived-data calculations.')
