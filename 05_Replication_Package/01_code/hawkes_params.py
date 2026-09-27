#!/usr/bin/env python3
"""从经验衰减曲线反解 Hawkes 参数 (beta, 分支比 n = alpha/beta)
   模型: P(fail_t | history) = sigmoid( mu + sum_j alpha*exp(-beta*(t-t_j)) ) 的线性近似
   线性化: ln(OR at lag k) ≈ ln(OR_1) - beta*(k-1)  -> 斜率 = -beta
   分支比 n ≈ 1 - exp(-beta)  * (lnOR_1 折算)   (对小效应的一阶近似)
   同时给出「固定效应 vs 传播」的方差划分。
"""
import json, math
import numpy as np

EB, SE = 0, 1
# 由 hawkes_test.py 得到的经验 ln(OR) 衰减
DATA = {
    'execute_bash':        [0.5985, 0.4456, 0.3823, 0.3416, 0.3098],
    'str_replace_editor':  [0.9579, 0.6366, 0.4909, 0.3897, 0.3565],
}
LAGS = np.array([1, 2, 3, 4, 5], dtype=float)

print("=" * 78)
print("Hawkes 参数反解（指数核）")
print("=" * 78)
print(f"  {'tool':<22}{'beta (95%CI)':>24}{'半衰期':>12}{'lnOR_0外推':>14}")
res = {}
for nm, y in DATA.items():
    y = np.array(y)
    # 对 lag>=2 做线性拟合（lag1 常受瞬时效应影响），再报告全体拟合
    A = np.vstack([np.ones_like(LAGS), -LAGS]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    b0, beta = coef[0], coef[1]
    # 残差与标准误
    pred = A @ coef
    resid = y - pred
    dof = len(y) - 2
    s2 = (resid @ resid) / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    se_beta = math.sqrt(cov[1, 1])
    # beta 的 95% CI（t 分布，dof=3 -> t=3.182）
    tcrit = 3.182
    lo, hi = beta - tcrit*se_beta, beta + tcrit*se_beta
    halflife = math.log(2)/beta
    lnOR0 = b0
    res[nm] = dict(beta=beta, se=se_beta, ci=[lo, hi],
                   halflife=halflife, lnOR0=lnOR0)
    print(f"  {nm:<22}{beta:>10.4f} [{lo:.3f},{hi:.3f}]{halflife:>12.3f}{lnOR0:>14.4f}")
    print(f"  {'':22}R^2 = {1 - (resid@resid)/((y-y.mean())@(y-y.mean())):.4f}")

print()
print("  解释: beta 为激发衰减率（步^-1），半衰期 = ln2/beta 步")
print("        拟合优度高 = 单指数核足以描述持续性 -> 与 Hawkes(指数) 相容")

print()
print("=" * 78)
print("分支比（branching ratio）近似")
print("=" * 78)
print("  线性化: OR_k = exp(a - beta*(k-1))  ->  a = ln OR_1")
print("  分支比 n = 1 - exp(-a) 仅在 a 较小时有意义；此处 a 较大，")
print("  改用「超临界指数」度量：额外失败概率 = P(f|f) - P(f|s)")
for nm, y in DATA.items():
    a = y[0]
    print(f"  {nm:<22} a=ln OR_1={a:.4f}  1-exp(-a)={1-math.exp(-a):.4f}")
print("  -> 该量不是标准分支比，正文中应报告为「相邻激发强度」而非临界性指标")

print()
print("=" * 78)
print("与原始手稿数字的对照")
print("=" * 78)
print(f"  {'量':<34}{'手稿':>14}{'全语料实测':>14}")
rows = [
    ("pooled lag-1 OR",            "3.089*", "1.567"),
    ("within-trace OR",            "~1.0",   "1.573"),
    ("bash 同工具 OR",             "1.94x",  "1.82"),
    ("editor 同工具 OR",           "—",      "2.61"),
    ("累积失败曲线峰值",            "0.331",  "0.338"),
    ("ICC",                        "0.087",  "0.054"),
]
for a, b, c in rows:
    print(f"  {a:<34}{b:>14}{c:>14}")
print("  * 手稿 Table 3 的 3.089 为未校正的混合估计，全语料下不成立")

json.dump(res, open('hawkes_params.json', 'w'), indent=1)
print("\n-> hawkes_params.json")
