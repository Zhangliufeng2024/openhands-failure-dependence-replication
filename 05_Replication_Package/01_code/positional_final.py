#!/usr/bin/env python3
"""最终结论：位置效应的构成校正版本。

总结三个层次的构成混叠：
  L1 工具混合: bash/editor 占比随位置变化 (bash 0.32 -> 0.62)
  L2 子命令混合: editor 内部 view 0.99 -> 0.32, str_replace 0.001 -> 0.476
  L3 bash 类型混合: 测试类占比 0.33 -> 0.13 -> 0.28

校正后的真实图景:
  - 绝大多数「活动类型」内部，失败风险随轨迹推进【上升】
  - 唯一下降的是「运行测试/构建」类命令，且其降幅小于其他类的升幅
  - 因此「失败率随轨迹推进下降」是假象，正确的表述是「上升」

本脚本给出可写入手稿的最终数字，并做 bootstrap 稳健性检查。
"""
from paths import work, corpus, results
import json, collections
import numpy as np

S = json.load(open(work('step_meta.json')))

LAYERS = [
    ('bash, non-test',        0, 4, 0),
    ('bash, test/build',      0, 4, 1),
    ('editor, view',          1, 3, 0),
    ('editor, create',        1, 3, 1),
    ('editor, str_replace',   1, 3, 2),
]

def collect(tool, subidx, subval):
    """返回每条轨迹的前后半段失败率列表"""
    rows = []
    for tr in S:
        y = [s[1] for s in tr['steps'] if s[0]==tool and s[subidx]==subval]
        if len(y) < 8: continue
        h = len(y)//2
        rows.append((sum(y[:h])/h, sum(y[h:])/(len(y)-h)))
    return rows

print("=" * 78)
print("构成校正后的位置效应（最终数字）")
print("=" * 78)
print(f"  {'活动类型':<22}{'前半段':>9}{'后半段':>9}{'变化':>9}{'t':>8}{'n轨迹':>9}")
results = {}
for nm, tool, si, sv in LAYERS:
    rows = collect(tool, si, sv)
    if len(rows) < 1000: continue
    a = np.array([r[0] for r in rows]); b = np.array([r[1] for r in rows])
    d = b - a
    se = d.std(ddof=1)/np.sqrt(len(d))
    results[nm] = dict(first=float(a.mean()), second=float(b.mean()),
                       diff=float(d.mean()), t=float(d.mean()/se), n=len(d))
    print(f"  {nm:<22}{a.mean():>9.4f}{b.mean():>9.4f}{d.mean():>+9.4f}"
          f"{d.mean()/se:>8.1f}{len(d):>9,}")

print()
print("=" * 78)
print("bootstrap 稳健性（1000 次重采样，对总均差）")
print("=" * 78)
rng = np.random.default_rng(42)
alls = {nm: collect(tool, si, sv) for nm, tool, si, sv in LAYERS}
for nm, rows in alls.items():
    if len(rows) < 1000: continue
    d = np.array([b-a for a,b in rows])
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    excl0 = (lo > 0) or (hi < 0)
    print(f"  {nm:<22} 均差={d.mean():+.4f}  95%CI=[{lo:+.4f},{hi:+.4f}]  "
          f"{'显著' if excl0 else '不显著'}")

print()
print("=" * 78)
print("加权总效应（按各层样本量加权）")
print("=" * 78)
tot_num = tot_den = 0.0
for nm, tool, si, sv in LAYERS:
    rows = alls[nm]
    if len(rows) < 1000: continue
    d = np.array([b-a for a,b in rows])
    tot_num += d.mean()*len(d); tot_den += len(d)
    print(f"  {nm:<22} 均差={d.mean():+.4f}  n={len(d):,}  权重={len(d)/tot_den:.3f}")
print(f"  {'-'*60}")
print(f"  加权总均差 = {tot_num/tot_den:+.4f}")

json.dump(results, open(results('positional_final.json'),'w'), indent=1)
print("\n-> positional_final.json")
