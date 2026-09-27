#!/usr/bin/env python3
"""诊断 editor 宽松标签的 13 万假阳性来源"""
from paths import work, corpus, results
import collections, re
import pyarrow.parquet as pq

ERR = re.compile(
    r"(Traceback \(most recent call last\)|\b[A-Za-z_]*Error\b|\berror:"
    r"|command not found|No such file or directory|not found|fatal:"
    r"|FAILED|AssertionError|\bException\b)", re.I)
ED_FAIL = re.compile(r"^\s*ERROR:")
ED_OK = re.compile(r"^\s*(Here's the|File created successfully|The file|"
                   r"Successfully|Inserted|Edited|Undo)")

f = pq.ParquetFile(corpus())
kw = collections.Counter()      # 哪个关键词触发
ctx = collections.defaultdict(list)
n = 0
for b in f.iter_batches(batch_size=256, columns=['trajectory']):
    for r in b.to_pylist():
        n += 1
        for m in r['trajectory']:
            if m['role'] != 'tool' or m.get('name') != 'str_replace_editor':
                continue
            c = m.get('content') or ''
            if ED_FAIL.match(c) or ED_OK.match(c):
                continue                      # 只看严格判成功的
            if not ERR.search(c):
                continue
            # 找出触发的关键词
            hits = []
            for p in ['Traceback \\(most recent call last\\)', '[A-Za-z_]*Error',
                      'error:', 'command not found', 'No such file or directory',
                      'not found', 'fatal:', 'FAILED', 'AssertionError', 'Exception']:
                if re.search(p, c, re.I): hits.append(p)
            key = hits[0] if hits else 'other'
            kw[key] += 1
            if len(ctx[key]) < 2:
                mm = ERR.search(c)
                st = max(0, mm.start()-60)
                ctx[key].append(c[st:mm.end()+90].replace('\n', ' | '))
    if n >= 20000:
        break

print("=" * 78)
print(f"editor 宽松标签假阳性的触发关键词分布（采样 {n:,} 轨迹）")
print("=" * 78)
tot = sum(kw.values())
for k, v in kw.most_common():
    print(f"  {v:>8,}  ({v/tot*100:>5.1f}%)  {k}")
print(f"  {'-'*60}\n  {tot:>8,}  总计")

print()
print("=" * 78)
print("各关键词的上下文样本")
print("=" * 78)
for k, _ in kw.most_common(6):
    print("-" * 70)
    print(f"[{k}] n={kw[k]:,}")
    for s in ctx[k][:2]:
        print(f"  ...{s}...")
