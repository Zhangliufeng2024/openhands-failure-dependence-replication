# -*- coding: utf-8 -*-
"""Regenerate 03_Tables/TableNN.txt extracts from the manuscript source.

Each extract carries the table's source line number so it can be traced back.
Usage: python extract_tables.py [source.md]
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '01_Manuscript', 'Manuscript_Paper3_v3.7_source.md')
OUTDIR = os.path.join(ROOT, '03_Tables')

lines = io.open(SRC, encoding='utf-8').read().split('\n')
def is_sep(ln):
    s = ln.strip()
    return bool(s) and set(s) <= set('-=')

n = 0
i = 0
while i < len(lines):
    s = lines[i].strip()
    if re.match(r'^Table \d+\.', s) and i + 1 < len(lines) and is_sep(lines[i + 1]):
        cap_line = i + 1
        cap = s
        # collect caption (may wrap) and the table block
        j = i + 1
        while j < len(lines) and lines[j].strip() and not is_sep(lines[j]):
            j += 1
        # table body: from after the first separator until blank line
        body = []
        k = j
        while k < len(lines) and lines[k].strip():
            body.append(lines[k].rstrip())
            k += 1
        m = re.match(r'^Table (\d+)\.', cap)
        num = int(m.group(1))
        out = os.path.join(OUTDIR, 'Table%02d.txt' % num)
        with io.open(out, 'w', encoding='utf-8') as f:
            f.write(cap + '\n')
            f.write('=' * 88 + '\n')
            f.write('(source: %s, line %d)\n' % (os.path.basename(SRC), cap_line))
            f.write('=' * 88 + '\n')
            f.write('\n')
            f.write('\n'.join(body) + '\n')
        n += 1
        i = k
    else:
        i += 1
print('regenerated %d table extracts in %s' % (n, OUTDIR))
