#!/usr/bin/env python3
"""Hawkes vs AR(1) 可分性：持续性随滞后阶数的衰减形状
   Hawkes(指数核): lag-k 自相关 ~ exp(-beta*k)  —— 单调指数衰减
   AR(1)/静态异质: 也指数衰减，但可由「轨迹随机效应」解释
   关键判别: 控制轨迹随机效应(条件似然)后，Hawkes 的衰减是否仍存在
"""
import json, collections, math
import numpy as np

S = json.load(open('full_seqs.json'))
EB, SE = 0, 1

print("=" * 78)
print("A. 滞后阶数衰减曲线（每工具内部）")
print("=" * 78)
for tool, nm in [(EB, 'execute_bash'), (SE, 'str_replace_editor')]:
    rows = {}
    for lag in (1, 2, 3, 4, 5):
        pf = nf = ps = ns = 0
        for tr in S:
            seq = [s[1] for s in tr['steps'] if s[0] == tool]
            for k in range(lag, len(seq)):
                if seq[k-lag] == 1: nf += 1; pf += seq[k]
                else:               ns += 1; ps += seq[k]
        if nf and ns:
            a = pf/nf; b = ps/ns
            rows[lag] = (a/b, (a/(1-a))/(b/(1-b)))
    print(f"  {nm}")
    print(f"    {'lag':>4}{'ratio':>10}{'OR':>10}{'ln(OR)':>10}{'衰减比':>10}")
    prev = None
    for lag, (r, o) in rows.items():
        d = f"{math.log(o)/prev:.3f}" if prev else "—"
        print(f"    {lag:>4}{r:>10.4f}{o:>10.4f}{math.log(o):>10.4f}{d:>10}")
        prev = math.log(o)
    print("    -> 衰减比≈常数 = 指数核(与Hawkes相容)；快速归零 = 仅一阶效应")

print()
print("=" * 78)
print("B. 轨迹随机效应 vs 真实时序传播（条件检验）")
print("   构造：只保留「既有失败又有成功」的轨迹，且只看对内的次序反转")
print("=" * 78)
# 在每条轨迹内，用该轨迹自身的失败率 p_i 做条件期望
num = den = 0.0
num_s = den_s = 0.0
for tr in S:
    seq = [s[1] for s in tr['steps'] if s[0] in (EB, SE)]
    n = len(seq)
    if n < 4: continue
    k = sum(seq)
    if k == 0 or k == n: continue
    pi = k/n
    # 对每一对 (k-1, k) 计算 观察 - 条件期望
    for j in range(1, n):
        num += (seq[j] - pi) * (seq[j-1] - pi)
        den += (seq[j-1] - pi) ** 2
        num_s += (seq[j] - pi) * pi * (1-pi) / max(1e-9, pi*(1-pi))
rho_cond = num/den if den else float('nan')
print(f"  轨迹内去均值 lag-1 自相关 rho_cond = {rho_cond:.6f}")
print(f"  (对照: 无条件下每条轨迹的期望为 0)")
print("  -> rho_cond > 0 说明即使剔除轨迹平均失败率的差异，")

print()
print("=" * 78)
print("C. 置换检验：轨迹内打乱（保持每条轨迹失败总数）")
print("=" * 78)
rng = np.random.default_rng(11)
seqs = []
for tr in S:
    seq = [s[1] for s in tr['steps'] if s[0] in (EB, SE)]
    if len(seq) >= 4: seqs.append(np.array(seq))
print(f"  参与检验的轨迹数 = {len(seqs):,}")
obs_num = obs_den = 0.0
for y in seqs:
    pi = y.mean()
    if 0 < pi < 1:
        for j in range(1, len(y)):
            obs_num += (y[j]-pi)*(y[j-1]-pi)
            obs_den += (y[j-1]-pi)**2
obs = obs_num/obs_den
sims = []
for _ in range(50):
    sn = sd = 0.0
    for y in seqs:
        sh = y.copy(); rng.shuffle(sh)
        pi = sh.mean()
        if 0 < pi < 1:
            for j in range(1, len(sh)):
                sn += (sh[j]-pi)*(sh[j-1]-pi)
                sd += (sh[j-1]-pi)**2
    sims.append(sn/sd)
sims = np.array(sims)
print(f"  观察 rho_cond = {obs:.6f}")
print(f"  打乱零分布 mean={sims.mean():.6f}  sd={sims.std():.6f}  "
      f"95%=[{np.percentile(sims,2.5):.6f},{np.percentile(sims,97.5):.6f}]")
z = (obs - sims.mean())/sims.std()
print(f"  z = {z:.1f}")

json.dump({'rho_cond': obs, 'null_mean': float(sims.mean()),
           'null_sd': float(sims.std()), 'z': float(z)},
          open('hawkes_vs_ar1.json', 'w'), indent=1)
print("\n-> hawkes_vs_ar1.json")
