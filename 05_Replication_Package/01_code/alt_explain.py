#!/usr/bin/env python3
"""检验 editor 失败率下降的替代解释。

对手解释 B: editor 调用在轨迹后期变少 / 性质改变（例如从「写代码」转向「跑测试」），
            于是后期 editor 样本成分不同，失败率下降只是构成效应。

需要检验的通道:
 B1. editor 占交互调用比例是否随位置变化
 B2. editor 调用是否在后期集中于某类命令（view vs create vs str_replace/insert）
 B3. 在固定「命令类型」后，下降是否仍存在  <-- 关键判据
 B4. 在固定「前后是否紧跟 bash」后，下降是否仍存在
"""
from paths import work, corpus, results
import json, collections
import numpy as np

S = json.load(open(work('full_seqs.json')))
EB, SE = 0, 1
B = [(0,5),(5,10),(10,15),(15,20),(20,30),(30,50),(50,100)]

print("=" * 78)
print("B1. editor 占交互调用比例 随位置的变化")
print("=" * 78)
cnt = collections.defaultdict(lambda: [0,0])   # bin -> [editor, total]
for tr in S:
    for k, s in enumerate([x for x in tr['steps'] if x[0] in (EB,SE)]):
        for lo,hi in B:
            if lo<=k<hi:
                cnt[(lo,hi)][1]+=1
                if s[0]==SE: cnt[(lo,hi)][0]+=1
                break
for lo,hi in B:
    e,t = cnt[(lo,hi)]
    if t: print(f"  {lo:>3}-{hi:<4} editor占比={e/t:.4f}  n={t:,}")

print()
print("=" * 78)
print("结论1: 若 editor 占比随位置大幅下降，则 B 通道存在")
print("=" * 78)

print()
print("=" * 78)
print("B3. 关键判据 —— 需要 editor 的子命令类型，但 full_seqs.json 未记录")
print("     先检查是否需要重新抽取")
print("=" * 78)
print("  full_seqs 仅含 [tool_id, lenient, strict]，无命令类型。")
print("  -> 需要从 parquet 重新抽取 editor 的 command 参数。")
