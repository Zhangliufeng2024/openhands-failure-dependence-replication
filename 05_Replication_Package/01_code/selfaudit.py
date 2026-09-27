#!/usr/bin/env python3
"""自审：检验手稿中最薄弱的三个论断
   1) 4.2 的「1.44-1.78 无趋势」—— 是否真无趋势？
   2) 4.9 的「resolved 与 unresolved 只差 5%」—— 是否被长度混杂？
   3) 4.4 位置效应 —— 「warm-up」解释能否被数据支持？
"""
from paths import work, corpus, results
import json, collections
import numpy as np

S = json.load(open(work('full_seqs.json')))
EB, SE = 0, 1

print("=" * 78)
print("疑点 1: 分层 ratio 真的「无趋势」吗？")
print("=" * 78)
# 手稿称 band 1.44-1.78「no systematic trend」—— 但 1.439->1.777 是上升的
cum_ratio = [1.439, 1.695, 1.777, 1.769, 1.754, 1.623]
xs = np.arange(len(cum_ratio))
sl = np.polyfit(xs[:5], cum_ratio[:5], 1)
print(f"  前 5 层线性斜率 = {sl[0]:+.4f} /层")
print(f"  序列: {cum_ratio}")
print(f"  -> 单调上升后回落；说「no systematic trend」不准确。")
print(f"     正确表述: 「非单调，先升后降，峰值在 cum=2-4」")

print()
print("=" * 78)
print("疑点 2: resolved vs unresolved 的 5% 差距是否被长度混杂？")
print("=" * 78)
# 按轨迹长度分层，比较同长度下的失败率
lay = collections.defaultdict(lambda: [0, 0, 0, 0])   # bin -> [fail_r, n_r, fail_u, n_u]
BINS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 120), (120, 100000)]
for tr in S:
    y = [s[1] for s in tr['steps'] if s[0] in (EB, SE)]
    if not y: continue
    L = len(y)
    idx = None
    for i, (lo, hi) in enumerate(BINS):
        if lo <= L < hi: idx = i; break
    if idx is None: continue
    f = sum(y)
    if tr['resolved'] == 1:
        lay[idx][0] += f; lay[idx][1] += L
    else:
        lay[idx][2] += f; lay[idx][3] += L
print(f"  {'长度区间':<12}{'resolved失败率':>16}{'unresolved失败率':>18}{'差值':>10}{'n_res':>12}{'n_unres':>12}")
for i, (lo, hi) in enumerate(BINS):
    fr, nr, fu, nu = lay[i]
    if nr < 1000 or nu < 1000: continue
    a, b = fr/nr, fu/nu
    lab = f"{lo}-{hi if hi<100000 else '+'}"
    print(f"  {lab:<12}{a:>16.4f}{b:>18.4f}{a-b:>10.4f}{nr:>12,}{nu:>12,}")
print("  -> 若同一长度层内差距翻转或消失，则 5% 的结论是长度混杂造成的")

print()
print("=" * 78)
print("疑点 3: 位置效应的 warm-up 解释是否成立？")
print("=" * 78)
# 若前几步是「侦察」(read/ls)，则前几步的失败率低应是内容效应而非位置效应
# 检验: 只统计 bash 命令，看失败率随步数的形状是否与合并一致
B = [(0,5),(5,10),(10,15),(15,20),(20,30),(30,50),(50,100)]
for tool, nm in ((EB,'execute_bash'),(SE,'str_replace_editor')):
    bk = collections.defaultdict(lambda: [0,0])
    for tr in S:
        y = [s[1] for s in tr['steps'] if s[0]==tool]
        for k,v in enumerate(y):
            for lo,hi in B:
                if lo<=k<hi:
                    bk[(lo,hi)][0]+=v; bk[(lo,hi)][1]+=1; break
    print(f"  {nm}")
    for lo,hi in B:
        f,n = bk[(lo,hi)]
        if n: print(f"     {lo:>3}-{hi:<4} rate={f/n:.4f}  n={n:,}")
    print()

json.dump({'len_strata': {f"{BINS[i][0]}-{BINS[i][1]}": lay[i] for i in range(len(BINS))}},
          open(results('selfaudit.json'),'w'), indent=1)
print("-> selfaudit.json")
