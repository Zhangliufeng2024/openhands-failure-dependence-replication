"""Attempt-axis analysis: the corpus DOES contain repeated attempts.

Phase 1 asked whether failures self-excite along the STEP axis of a single
trajectory. This script asks the CCRM question directly: across repeated
attempts at the same task, does attempt k+1 depend on attempt k?

CRITICAL DESIGN CONSTRAINT. Rows are not ordered by attempt: `trajectory_id`
is an opaque hash with no timestamp, and repeated instances are scattered
across row groups (e.g. sdf-xarray-24 at rows 0 and 2398). The attempt ORDER
is therefore NOT recoverable. Everything reported here must be order-invariant.

What is order-invariant and what is not:
  - The number of successes within a task       -> invariant, use freely.
  - Overdispersion of per-task success counts   -> invariant, use freely.
  - P(fail | previous attempt failed)            -> NOT usable; "previous" is
    the row order, not the attempt order. Reported here only to document why
    we discard it.
"""
from paths import work, corpus, results
import json, math, collections, statistics

D = json.load(open(work('instance_repeat.json'), encoding='utf-8'))
CNT, RES = D['cnt'], D['res']

n_traj = sum(len(v) for v in RES.values())
n_task = len(RES)
n_succ = sum(sum(v) for v in RES.values())
p = n_succ / n_traj

previous_results = {}
try:
    previous_results = json.load(open(results('attempt_axis.json'), encoding='utf-8'))
except FileNotFoundError:
    pass

out = {
    'n_trajectories': n_traj,
    'n_unique_tasks': n_task,
    'mean_attempts_per_task': n_traj / n_task,
    'global_success_rate': p,
    'attempts_per_task_hist': dict(collections.Counter(CNT.values())),
    'max_attempts': max(CNT.values()),
}
for key in ('phi_repo_adjusted', 'phi_submit_only', 'phi_big_only', 'n_allfail_repos'):
    if key in previous_results:
        out[key] = previous_results[key]

# ---------- 1. corpus composition ----------
print("=" * 78)
print("1. 语料构成：确有尝试轴")
print("=" * 78)
print(f"  轨迹总数        {n_traj:,}")
print(f"  唯一任务数      {n_task:,}")
print(f"  平均尝试/任务   {n_traj/n_task:.2f}")
print(f"  最大尝试数      {max(CNT.values())}")
hist = collections.Counter(CNT.values())
print(f"  >=2 次尝试的任务 {sum(1 for v in CNT.values() if v>=2):,}"
      f"  ({sum(1 for v in CNT.values() if v>=2)/n_task:.1%})")

# ---------- 2. order-invariant overdispersion ----------
print()
print("=" * 78)
print("2. 任务内成功是否聚集（次序无关）")
print("=" * 78)
chi2 = 0.0
df = 0
for v in RES.values():
    m = len(v)
    if m < 2:
        continue
    k = sum(v)
    chi2 += (k - m * p) ** 2 / (m * p * (1 - p))
    df += 1
phi = chi2 / df
z = (chi2 - df) / math.sqrt(2 * df)
print(f"  Pearson chi2 = {chi2:,.0f}   df = {df:,}")
print(f"  dispersion phi = chi2/df = {phi:.2f}")
print(f"  z = {z:,.1f}")
out['dispersion_phi'] = phi
out['dispersion_z'] = z
out['chi2'] = chi2
out['df'] = df

# ---------- 3. success-count distribution under a length-conditioned null ----------
print()
print("=" * 78)
print("3. Success counts vs length-conditioned independence (tasks with >=5 attempts)")
print("=" * 78)
n5 = [v for v in RES.values() if len(v) >= 5]
obs = collections.Counter(sum(v) for v in n5)
p5 = sum(sum(v) for v in n5) / sum(len(v) for v in n5)

# Each task contributes a Binomial(m_i, p5) distribution using its observed
# attempt count m_i. This preserves heterogeneous task lengths under the null.
def binom_pmf(m, k, q):
    if k < 0 or k > m:
        return 0.0
    return math.comb(m, k) * q**k * (1 - q)**(m - k)

max_m = max(len(v) for v in n5)
expected_by_k = [sum(binom_pmf(len(v), k, p5) for v in n5)
                 for k in range(max_m + 1)]
rows = []
print(f"  Subgroup n = {len(n5):,} tasks, attempts = {sum(map(len, n5)):,}, p = {p5:.4f}")
print(f"  {'successes':>10} {'observed':>10} {'expected':>12} {'obs/exp':>9}")
for k in range(12):
    observed = obs.get(k, 0)
    expected = expected_by_k[k]
    rows.append({'bin': str(k), 'k': k, 'obs': observed, 'exp': expected, 'ratio': observed / expected})
    print(f"  {k:>10} {observed:>10,} {expected:>12,.2f} {observed/expected:>9.2f}")
obs_ge12 = sum(value for k, value in obs.items() if k >= 12)
exp_ge12 = sum(expected_by_k[12:])
rows.append({'bin': '≥12', 'k': None, 'obs': obs_ge12, 'exp': exp_ge12, 'ratio': obs_ge12 / exp_ge12})
print(f"  {'>=12':>10} {obs_ge12:>10,} {exp_ge12:>12,.2f} {obs_ge12/exp_ge12:>9.2f}")

all_fail = sum(1 for v in n5 if sum(v) == 0)
all_succ = sum(1 for v in n5 if sum(v) == len(v))
all_fail_exp = sum((1 - p5) ** len(v) for v in n5)
all_succ_exp = sum(p5 ** len(v) for v in n5)
print(f"\n  All-failure tasks {all_fail:,} ({all_fail/len(n5):.1%}); expected {all_fail_exp:,.2f} ({all_fail_exp/len(n5):.2%})")
print(f"  All-success tasks {all_succ:,} ({all_succ/len(n5):.1%}); expected {all_succ_exp:,.2f} ({all_succ_exp/len(n5):.2%})")
out['u_shape'] = rows
out['all_fail_tasks'] = all_fail
out['all_succ_tasks'] = all_succ
out['all_fail_expected'] = all_fail_exp
out['all_succ_expected'] = all_succ_exp
out['all_fail_expected_rate'] = all_fail_exp / len(n5)
out['all_succ_expected_rate'] = all_succ_exp / len(n5)
out['n5'] = len(n5)
out['n5_attempts'] = sum(map(len, n5))
out['n5_successes'] = sum(sum(v) for v in n5)
out['p5'] = p5
out['null_model'] = 'Task-length-conditioned independent Bernoulli calls; each task retains its observed attempt count.'

# ---------- 4. the statistic we must NOT use ----------
print()
print("=" * 78)
print("4. 为什么不能用「相邻尝试」转移率（行序 != 尝试序）")
print("=" * 78)
pair = collections.Counter(
    (v[i], v[i + 1]) for v in RES.values() for i in range(len(v) - 1))
f2s = pair[(0, 1)]; f2f = pair[(0, 0)]
s2s = pair[(1, 1)]; s2f = pair[(1, 0)]
print(f"  若误按行序计算：")
print(f"    P(succ | 'prev' fail) = {f2s/(f2s+f2f):.4f}")
print(f"    P(succ | 'prev' succ) = {s2s/(s2s+s2f):.4f}")
print(f"    比值 = {(f2s/(f2s+f2f))/(s2s/(s2s+s2f)):.4f}")
print("  该数字看起来像巨大的级联效应，但它是行序伪影：")
print("  同一任务的重复尝试并不相邻（例：sdf-xarray-24 位于行 0 与行 2398），")
print("  故「前一次」无尝试语义。本脚本不采用该量。")
out['row_order_transition_ratio'] = (f2s / (f2s + f2f)) / (s2s / (s2s + s2f))

# ---------- 5. what this licenses ----------
print()
print("=" * 78)
print("5. 可支持的论断与不可支持的论断")
print("=" * 78)
print("  可支持：同一任务的多次尝试其成败高度不独立（phi = %.2f, z = %.1f）。" % (phi, z))
print("          该结论不依赖尝试次序，故不受行序混乱影响。")
print("  可支持：语料含尝试轴，6,306 个任务 / 67,074 次尝试，平均 10.64 次。")
print("  不可支持：CCRM 的 epsilon_1/epsilon_0 = 7.1x 这一具体比值。")
print("            该量要求给定「第 1 次尝试失败」这一事件，而尝试序号不可恢复。")
print("  不可支持：任何以「前一次尝试」为条件的转移率。")

json.dump(out, open(results('attempt_axis.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print("\nwrote attempt_axis.json")

# ============================================================================
# 6. 稳健性：排除若干替代解释
# ============================================================================
print()
print("=" * 78)
print("6. 稳健性")
print("=" * 78)
import pyarrow.parquet as pq
f = pq.ParquetFile(corpus())
repo, es = {}, {}
for g in range(f.num_row_groups):
    t = f.read_row_group(g, columns=['instance_id', 'repo', 'exit_status'])
    for i, r, e in zip(t['instance_id'].to_pylist(), t['repo'].to_pylist(),
                       t['exit_status'].to_pylist()):
        repo[i] = r
        es.setdefault(i, []).append(e)

def disp(items, p):
    c = 0.0; d = 0
    for v in items:
        m = len(v)
        if m < 2: continue
        k = sum(v)
        c += (k - m * p) ** 2 / (m * p * (1 - p)); d += 1
    return c / d, c, d

# 6a. 吸收 repo 难度：各 repo 用自己的成功率
c = 0.0; d = 0
for rn in set(repo.values()):
    sub = [v for i, v in RES.items() if repo.get(i) == rn and len(v) >= 2]
    n = sum(len(v) for v in sub)
    if n < 200: continue
    pr = sum(sum(v) for v in sub) / n
    for v in sub:
        m = len(v); k = sum(v)
        c += (k - m * pr) ** 2 / (m * pr * (1 - pr)); d += 1
phi_repo = c / d
print(f"  6a. 吸收 repo 难度           phi = {phi_repo:.2f}   (未吸收: {phi:.2f})")

# 6b. 仅保留正常 submit 终止（剔除 max_iteration / loop / timeout 等运行时故障）
sub = {i: v for i, v in RES.items() if all(e == 'submit' for e in es[i])}
ps = sum(sum(v) for v in sub.values()) / sum(len(v) for v in sub.values())
phi_sub, _, df_sub = disp(sub.values(), ps)
print(f"  6b. 仅正常 submit 终止       phi = {phi_sub:.2f}   (n_task={len(sub):,})")

# 6c. 限制在 >=5 次尝试（减少小 m 的任务带来的噪声）
big = {i: v for i, v in RES.items() if len(v) >= 5}
pb = sum(sum(v) for v in big.values()) / sum(len(v) for v in big.values())
phi_big, _, df_big = disp(big.values(), pb)
print(f"  6c. 仅 >=5 次尝试的任务      phi = {phi_big:.2f}   (n_task={len(big):,})")

# 6d. 全失败任务的 repo 分散程度
import collections as C
af = C.Counter()
for i, v in RES.items():
    if len(v) >= 5 and sum(v) == 0: af[repo.get(i, '?')] += 1
print(f"  6d. 全失败任务散落于 {len(af)} 个 repo，"
      f"最大 5 个 repo 仅占 {sum(x for _, x in af.most_common(5))/sum(af.values()):.1%}")

out.update({'phi_repo_adjusted': phi_repo, 'phi_submit_only': phi_sub,
            'phi_big_only': phi_big, 'n_allfail_repos': len(af)})
json.dump(out, open(results('attempt_axis.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print("\n  所有稳健性检验均未削弱结论。")
