#!/usr/bin/env python3
"""1) 位置效应：在工具内部检验（消除工具混合构成本文已在 4.4 承认的混淆）
   2) 确认 editor 假阳性是否集中在 view 类调用（读文件时内容含 Error 字样）
"""
from paths import work, corpus, results
import json, collections
import numpy as np, pyarrow.parquet as pq

S = json.load(open(work('full_seqs.json')))
EB, SE = 0, 1
B = [(0,5),(5,10),(10,15),(15,20),(20,30),(30,50),(50,100)]

print("=" * 78)
print("1. 位置效应：工具内部（工具类型已固定）")
print("=" * 78)
for tool, nm in ((EB,'execute_bash'), (SE,'str_replace_editor')):
    bk = collections.defaultdict(lambda: [0,0])
    for tr in S:
        y = [s[1] for s in tr['steps'] if s[0]==tool]
        for k,v in enumerate(y):
            for lo,hi in B:
                if lo<=k<hi: bk[(lo,hi)][0]+=v; bk[(lo,hi)][1]+=1; break
    print(f"\n  {nm}")
    prev=None
    for lo,hi in B:
        f,n = bk[(lo,hi)]
        if not n: continue
        r=f/n
        d = f"  ({r/prev:+.2f}x vs 前箱)" if prev else ""
        print(f"    {lo:>3}-{hi:<4} rate={r:.4f}  n={n:>9,}{d}")
        prev=r

print()
print("=" * 78)
print("2. 关键问题：位置效应是否可在工具内用「同轨迹对照」检验？")
print("=" * 78)
# 更强检验：在每条轨迹内，比较前半段与后半段的失败率（配对检验，消除轨迹异质性）
print("   配对设计：每条轨迹内 前半段 vs 后半段 失败率")
for tool, nm in ((EB,'execute_bash'), (SE,'str_replace_editor')):
    diffs=[]; fh=0; nh=0; sh=0; ns=0
    for tr in S:
        y = [s[1] for s in tr['steps'] if s[0]==tool]
        if len(y) < 8: continue
        h = len(y)//2
        a,b2 = y[:h], y[h:]
        ra, rb = sum(a)/len(a), sum(b2)/len(b2)
        diffs.append(rb-ra)
        fh+=sum(a); nh+=len(a); sh+=sum(b2); ns+=len(b2)
    diffs=np.array(diffs)
    se = diffs.std(ddof=1)/np.sqrt(len(diffs))
    print(f"\n  {nm}  (n={len(diffs):,} 条轨迹)")
    print(f"    前半段失败率 = {fh/nh:.4f}  (n={nh:,})")
    print(f"    后半段失败率 = {sh/ns:.4f}  (n={ns:,})")
    print(f"    配对均差 = {diffs.mean():+.4f}  SE={se:.4f}  t = {diffs.mean()/se:+.1f}")
    print(f"    后半段更低的轨迹占比 = {(diffs<0).mean()*100:.1f}%")

print()
print("=" * 78)
print("3. 控制累计失败数后的位置效应（排除「后半段失败多是因为失败多」）")
print("=" * 78)
# 只看「到目前为止失败数为 0」的调用，此时位置是唯一变量
for tool, nm in ((EB,'execute_bash'), (SE,'str_replace_editor')):
    bk = collections.defaultdict(lambda: [0,0])
    for tr in S:
        cum = 0
        for k, s in enumerate([x for x in tr['steps'] if x[0]==tool]):
            if cum == 0:
                for lo, hi in B:
                    if lo <= k < hi:
                        bk[(lo,hi)][0] += s[1]; bk[(lo,hi)][1] += 1
                        break
            cum += s[1]
    print(f"\n  {nm}  —— 仅累计失败=0 的调用")
    prev=None
    for lo,hi in B:
        f,n = bk[(lo,hi)]
        if not n: continue
        r=f/n
        d = f"  ({r/prev:+.2f}x)" if prev else ""
        print(f"    {lo:>3}-{hi:<4} rate={r:.4f}  n={n:>9,}{d}")
        prev=r
print()
print("  说明：在累计失败=0 的调用中，历史失败数被固定为 0，")
print("        此位置曲线的任何形状不能再由「累积损伤」解释。")
