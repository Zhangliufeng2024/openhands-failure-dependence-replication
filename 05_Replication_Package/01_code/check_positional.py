#!/usr/bin/env python3
"""验证最严重的问题：位置效应的 warm-up 解释与工具分解矛盾
   手稿 4.4 用合并曲线说「前几步是侦察所以失败率低」
   但分工具后 editor 在 5-10 步是 0.383（比 bash 高），且 10-15 步反而降到 0.269
   -> 合并曲线的形状是两个工具不同形状的叠加，不是统一的「warm-up」
"""
from paths import work, corpus, results
import json, collections
import numpy as np

S = json.load(open(work('full_seqs.json')))
EB, SE = 0, 1
B = [(0,5),(5,10),(10,15),(15,20),(20,30),(30,50),(50,100)]

print("=" * 78)
print("问题核心：合并曲线的「倒U」是否真实存在？")
print("=" * 78)
# 合并（手稿 Table 6 的口径）
bk = collections.defaultdict(lambda: [0,0])
for tr in S:
    y = [s[1] for s in tr['steps'] if s[0] in (EB,SE)]
    for k,v in enumerate(y):
        for lo,hi in B:
            if lo<=k<hi: bk[(lo,hi)][0]+=v; bk[(lo,hi)][1]+=1; break
print(f"  {'bin':<10}{'合并':>10}{'bash':>10}{'editor':>10}{'bash占比':>12}")
bd = collections.defaultdict(lambda: [0,0]); ed = collections.defaultdict(lambda: [0,0])
for tr in S:
    for tool,acc in ((EB,bd),(SE,ed)):
        y = [s[1] for s in tr['steps'] if s[0]==tool]
        for k,v in enumerate(y):
            for lo,hi in B:
                if lo<=k<hi: acc[(lo,hi)][0]+=v; acc[(lo,hi)][1]+=1; break
for lo,hi in B:
    f,n = bk[(lo,hi)]
    bf,bn = bd[(lo,hi)]; ef,en = ed[(lo,hi)]
    print(f"  {lo:>3}-{hi:<5}{f/n:>10.4f}{bf/bn:>10.4f}{ef/en:>10.4f}{bn/(bn+en):>12.3f}")

print()
print("  观察：合并曲线在 10-15 步见顶(0.345)，但")
print("    - bash 在 10-15 见顶后缓慢下降")
print("    - editor 在 5-10 见顶(0.383) 后骤降")
print("  -> 两个工具峰值位置不同，合并倒U是叠加产物")

print()
print("=" * 78)
print("更严重的检查：editor 在 5-10 步的 0.383 是异常吗？")
print("=" * 78)
# editor 的 5-10 步 n 很小吗？
for lo,hi in B:
    f,n = ed[(lo,hi)]
    if n: print(f"  editor {lo:>3}-{hi:<4} rate={f/n:.4f} n={n:,}")
print()
print("  注意：editor 的 50-100 步 n 仅 11,527，而 0-5 步 n=335,368")
print("  -> 长轨迹末端样本极少，Table 6 的分箱在高端不稳定")

print()
print("=" * 78)
print("结论：4.4 节的因果解释（warm-up / context growth）缺乏依据")
print("=" * 78)
print("  可支持的只有：失败率随步数非单调，早期上升，中期见顶，后期缓降。")
print("  不可支持的是：把它归因于「侦察阶段」或「context growth」，")
print("  因为两个工具的峰值位置不同，说明它至少部分由工具混合比变化驱动。")
# 工具混合比随步数变化
print()
print("  工具混合比随步数变化（这本身就能制造形状）：")
for lo,hi in B:
    bf,bn = bd[(lo,hi)]; ef,en = ed[(lo,hi)]
    print(f"    {lo:>3}-{hi:<4} bash占比={bn/(bn+en):.3f}")
