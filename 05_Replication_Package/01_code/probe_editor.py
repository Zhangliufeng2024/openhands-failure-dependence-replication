#!/usr/bin/env python3
"""勘察 str_replace_editor 的失败消息形态，为构造准严格标签取证"""
from paths import work, corpus, results
import collections, re, json
import pyarrow.parquet as pq

f = pq.ParquetFile(corpus())
# 采样 editor 的 observation 头部模式
head = collections.Counter()
samples = collections.defaultdict(list)
n = 0
for b in f.iter_batches(batch_size=256, columns=['trajectory']):
    for r in b.to_pylist():
        n += 1
        for m in r['trajectory']:
            if m['role'] != 'tool' or m.get('name') != 'str_replace_editor':
                continue
            c = (m.get('content') or '').strip()
            if not c:
                head['<EMPTY>'] += 1; continue
            # 取前 60 字符作为形态指纹
            key = c[:60].replace('\n', ' ')
            head[key] += 1
            if len(samples[key]) < 2:
                samples[key].append(c[:300])
    if n >= 20000:
        break

print("=" * 78)
print(f"str_replace_editor observation 形态 Top 30 (采样 {n:,} 轨迹)")
print("=" * 78)
for k, v in head.most_common(30):
    print(f"{v:>9,}  {k}")

print()
print("=" * 78)
print("关键形态的完整样本")
print("=" * 78)
KEYS = ["Error", "error", "not found", "does not", "matches", "Invalid",
        "failed", "No replacement", "is not", "cannot", "Cannot", "must"]
seen = set()
for k, _ in head.most_common(60):
    for kw in KEYS:
        if kw in k and k not in seen:
            seen.add(k)
            print("-" * 70)
            print(f"[{head[k]:,} 次]")
            for s in samples[k][:1]:
                print(s)
            break
