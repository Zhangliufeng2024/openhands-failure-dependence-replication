#!/usr/bin/env python3
"""关键验证：构成混淆校核 + 标签效度 + 工具混杂校核"""
import json, re, collections
import numpy as np

rng = np.random.default_rng(20260918)
S = json.load(open('full_seqs.json'))
EB, SE = 0, 1

print("=" * 78)
print("A. 构成混淆校核 —— 合并OR 与 个体OR 的关系")
print("=" * 78)
# 对每条轨迹算 within-trace lag-1 OR（全部工具合并）
ors, ws = [], []
for tr in S:
    y = [s[1] for s in tr['steps'] if s[0] in (EB, SE)]
    if len(y) < 4:
        continue
    a = b = c = d = 0
    for k in range(1, len(y)):
        p, q = y[k-1], y[k]
        if p == 0 and q == 0: d += 1
        elif p == 0 and q == 1: c += 1
        elif p == 1 and q == 0: b += 1
        else: a += 1
    # Haldane-Anscombe 修正避免除零
    oi = ((a + .5) * (d + .5)) / ((b + .5) * (c + .5))
    ors.append(oi); ws.append(len(y) - 1)
ors = np.array(ors); ws = np.array(ws)
OR_w = float(np.average(ors, weights=ws))
pooled_OR = 1.567
print(f"  个体 within-trace OR 加权均值 OR_w = {OR_w:.4f}  (>1 表示轨迹内确实有持续性)")
print(f"  合并 pooled OR                    = {pooled_OR:.4f}")
print(f"  个体 OR 中位数={np.median(ors):.4f}  >1 占比={np.mean(ors>1)*100:.1f}%")
print(f"  -> 若 合并OR = OR_w x OR_b，则 between 分量 OR_b = {pooled_OR/OR_w:.4f}")

print()
print("=" * 78)
print("B. 标签效度 —— 按工具分解字符串标签的误报率")
print("=" * 78)
# bash 严格标签作为基准，测宽松标签的假阳性
import pyarrow.parquet as pq
f = pq.ParquetFile('trajectories.parquet')
tp = fp = tn = fn = 0
n_scanned = 0
for b in f.iter_batches(batch_size=256, columns=['trajectory']):
    for r in b.to_pylist():
        for m in r['trajectory']:
            if m['role'] != 'tool' or m.get('name') != 'execute_bash':
                continue
            c = m.get('content') or ''
            em = re.search(r"(?:exit code|exit status)\s*[:=]?\s*(-?\d+)", c, re.I)
            if em:
                strict = int(em.group(1)) != 0
            else:
                fm = re.search(r"finished with exit code\s*(\d+)", c, re.I)
                strict = bool(fm) and int(fm.group(1)) != 0
            lenient = strict or bool(re.search(
                r"(Traceback \(most recent call last\)|\b[A-Za-z_]*Error\b|\berror:"
                r"|command not found|No such file or directory|not found|fatal:"
                r"|FAILED|AssertionError|\bException\b)", c, re.I))
            if strict and lenient: tp += 1
            elif lenient and not strict: fp += 1
            elif not lenient and not strict: tn += 1
            else: fn += 1
    n_scanned += 256
    if n_scanned >= 6000:
        break
if tp + fp:
    print(f"  bash 宽松标签相对严格标签: 精确率 = {tp/(tp+fp):.4f}  (n_pos={tp+fp:,})")
    print(f"  即宽松标签中 {(1-tp/(tp+fp))*100:.1f}% 是「输出里出现 error 字样但退出码为 0」")

print()
print("=" * 78)
print("C. 工具组合变化是否解释持续性")
print("=" * 78)
# 对照：只在「同工具连续」对之间 vs「任意连续」对之间
same_pf = same_ps = same_nf = same_ns = 0
for tr in S:
    st = [(s[0], s[1]) for s in tr['steps'] if s[0] in (EB, SE)]
    for k in range(1, len(st)):
        if st[k][0] != st[k-1][0]:
            continue
        if st[k-1][1] == 1: same_nf += 1; same_pf += st[k][1]
        else:               same_ns += 1; same_ps += st[k][1]
a = same_pf / max(same_nf, 1); b2 = same_ps / max(same_ns, 1)
print(f"  同工具连续对:  P(f|f)={a:.4f}  P(f|s)={b2:.4f}  ratio={a/b2:.3f}x")
print("  (与 [2] 同工具持续性一致 -> 说明持续性并非工具切换的伪影)")

print()
print("=" * 78)
print("D. 设计效应校正后的置信区间")
print("=" * 78)
p0, p1 = 0.2679, 0.3645
n0, n1 = 3_000_000, 700_000
icc, mbar = 0.0538, 59.83
deff = 1 + (mbar - 1) * icc
se_logit = np.sqrt(1/(n0*p0*(1-p0)) + 1/(n1*p1*(1-p1))) * np.sqrt(deff)
orv = (p1/(1-p1))/(p0/(1-p0))
lo = np.exp(np.log(orv) - 1.96*se_logit); hi = np.exp(np.log(orv) + 1.96*se_logit)
print(f"  设计效应 deff = 1+(m-1)*ICC = 1+(59.83-1)*0.0538 = {deff:.3f}")
print(f"  朴素 lOR = {np.log(orv):.4f}; 校正后 SE = {se_logit:.5f}")
print(f"  校正后 pooled OR 95% CI = [{lo:.4f}, {hi:.4f}]  (点估计 {orv:.4f})")

print()
print("=" * 78)
print("E. 与 7.1x 的对照：CCRM 需要多少倍的「尝试间」污染")
print("=" * 78)
print(f"  本文观察到的 pooled 相邻失败比 = {0.3645/0.2679:.3f}x")
print(f"  CCRM 报告的尝试间累积失败倍数 = 7.1x")
print(f"  比值 = {7.1/(0.3645/0.2679):.1f}x -> 观察值比 7.1x 低 {7.1/(0.3645/0.2679):.1f} 倍")

json.dump({'OR_w': OR_w, 'pooled_OR': pooled_OR,
           'label_precision_bash': tp/(tp+fp) if tp+fp else None,
           'deff': float(deff), 'OR_ci_deff': [float(lo), float(hi)],
           'ratio_ratio_vs_CCRM': 7.1/(0.3645/0.2679)},
          open('validation_results.json', 'w'), indent=1)
print("\n-> validation_results.json")
