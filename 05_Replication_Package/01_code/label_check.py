#!/usr/bin/env python3
"""标签效度深入：宽松标签的假阳性是否均匀分布？若非均匀，是否制造伪持续性？
   设计：在同一批 bash 上同时算 宽松 与 严格 两种标签，
        比较 宽松下的持续性 与 严格下的持续性（严格=退出码，几乎无假阳性）
"""
import json, re, collections
import numpy as np, pyarrow.parquet as pq

EB = 0
EXITCODE = re.compile(r"(?:exit code|exit status)\s*[:=]?\s*(-?\d+)", re.I)
FINISHED = re.compile(r"finished with exit code\s*(\d+)", re.I)
ERR = re.compile(
    r"(Traceback \(most recent call last\)|\b[A-Za-z_]*Error\b|\berror:"
    r"|command not found|No such file or directory|not found|fatal:"
    r"|FAILED|AssertionError|\bException\b)", re.I)


def strict_of(c):
    m = EXITCODE.search(c)
    if m:
        try: return int(m.group(1)) != 0
        except ValueError: return False
    m = FINISHED.search(c)
    if m: return int(m.group(1)) != 0
    return False


# 只抽取连续的 execute_bash 序列对（同一轨迹内、相邻且均为 bash）
f = pq.ParquetFile('trajectories.parquet')
pairs = collections.defaultdict(lambda: [0, 0, 0, 0])   # key -> [pf,nf,ps,ns]
# 同时记录每一对的「上一步严格标签、下一步宽松标签」
cross = collections.defaultdict(lambda: [0, 0])
n_traj = 0
for b in f.iter_batches(batch_size=256, columns=['trajectory', 'resolved']):
    for r in b.to_pylist():
        n_traj += 1
        seq = []
        for m in r['trajectory']:
            if m['role'] != 'tool' or m.get('name') != 'execute_bash':
                continue
            c = m.get('content') or ''
            s = strict_of(c)
            l = s or bool(ERR.search(c))
            seq.append((s, l))
        for k in range(1, len(seq)):
            ps_, pl_ = seq[k-1]      # prev strict, prev lenient
            cs_, cl_ = seq[k]        # cur  strict, cur  lenient
            for mode, (yp, yc) in (('strict', (ps_, cs_)), ('lenient', (pl_, cl_))):
                if yp == 1: pairs[mode][0] += yc; pairs[mode][1] += 1
                else:       pairs[mode][2] += yc; pairs[mode][3] += 1
            cross[(ps_, pl_, cs_)][0] += 1
            cross[(ps_, pl_, cs_)][1] += 0
    if n_traj >= 20000:
        break

print("=" * 78)
print("标签定义鲁棒性：同一批 bash 相邻对，两种标签下的持续性")
print("=" * 78)
print(f"  {'标签':<10}{'P(f|f)':>10}{'P(f|s)':>10}{'ratio':>9}{'OR':>9}")
for mode in ('lenient', 'strict'):
    pf, nf, ps, ns = pairs[mode]
    a = pf/nf; b = ps/ns
    orv = (a/(1-a))/(b/(1-b))
    print(f"  {mode:<10}{a:>10.4f}{b:>10.4f}{a/b:>9.3f}{orv:>9.3f}")
print("  -> 若严格标签下持续性依然显著，则结论不依赖宽松标签的假阳性")

print()
print("=" * 78)
print("假阳性的条件结构：上一步「严格成功但宽松失败」后，下一步严格失败率")
print("=" * 78)
tot = collections.defaultdict(int)
for (ps_, pl_, cs_), (n, _) in cross.items():
    tot[('prev_strict', ps_, 'prev_lenient', pl_)] += n
base = None
for key in sorted(tot):
    print(f"  {key}  n={tot[key]:,}")
print()
print("  注：若 prev 宽松失败(pl=1) 而严格成功(ps=0) 后 cur 严格失败率 ≈ 基线，")
print("      则宽松标签的假阳性不携带预测信息，宽松持续性来自真实失败。")

json.dump({'pairs': {k: v for k, v in pairs.items()},
           'cross': {str(k): v[0] for k, v in cross.items()}},
          open('label_validity.json', 'w'), indent=1)
print("\n-> label_validity.json")
