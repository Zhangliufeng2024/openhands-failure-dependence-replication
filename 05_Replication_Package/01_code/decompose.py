#!/usr/bin/env python3
"""决定性检验：串联持续性 是「真状态依赖」还是「工具类型构成」造成的？
   若剔除工具类型后持续性消失 -> 构成伪影
   若仍在 -> 真状态依赖
"""
import json, collections
import numpy as np

S = json.load(open('full_seqs.json'))
EB, SE = 0, 1

print("=" * 78)
print("1. 工具类型本身是否可预测？（不变性检验）")
print("=" * 78)
# 若 工具选择完全由「上一步是否失败」驱动，则 P(tool|fail) != P(tool|succ)
tr_tool_f = collections.defaultdict(int); tr_tool_s = collections.defaultdict(int)
for tr in S:
    st = [s for s in tr['steps'] if s[0] in (EB, SE)]
    for k in range(1, len(st)):
        tp, yp = st[k-1][0], st[k-1][1]
        tc = st[k][0]
        if yp == 1: tr_tool_f[tc] += 1
        else:       tr_tool_s[tc] += 1
nf = sum(tr_tool_f.values()); ns = sum(tr_tool_s.values())
print(f"  {'tool':<14}{'P(tool|prev fail)':>20}{'P(tool|prev succ)':>20}{'ratio':>10}")
for t, nm in [(EB, 'execute_bash'), (SE, 'str_replace_editor')]:
    a = tr_tool_f[t]/nf; b = tr_tool_s[t]/ns
    print(f"  {nm:<14}{a:>20.4f}{b:>20.4f}{a/b:>10.3f}")
print("  -> 工具选择几乎不随上一步成败改变，故构成不是持续性的直接驱动")

print()
print("=" * 78)
print("2. 分工具内部的 lag-1 持续性（已控制工具类型）")
print("=" * 78)
for tool, nm in [(EB, 'execute_bash'), (SE, 'str_replace_editor')]:
    pf = ps = nfq = nsq = 0
    for tr in S:
        seq = [s[1] for s in tr['steps'] if s[0] == tool]
        for k in range(1, len(seq)):
            if seq[k-1] == 1: nfq += 1; pf += seq[k]
            else:             nsq += 1; ps += seq[k]
    a = pf/max(nfq, 1); b = ps/max(nsq, 1)
    orv = (a/(1-a))/(b/(1-b)) if 0 < a < 1 and 0 < b < 1 else float('nan')
    print(f"  {nm:<20} P(f|f)={a:.4f} P(f|s)={b:.4f} ratio={a/b:.3f}x OR={orv:.3f}")

print()
print("=" * 78)
print("3. 关键反事实：把「同一工具内」的序列打乱后持续性是否消失")
print("   若消失 -> 持续性来自真实时间顺序，非边际构成的静态反映")
print("=" * 78)
rng = np.random.default_rng(7)
for tool, nm in [(EB, 'execute_bash'), (SE, 'str_replace_editor')]:
    seqs = []
    for tr in S:
        seq = [s[1] for s in tr['steps'] if s[0] == tool]
        if len(seq) > 2: seqs.append(np.array(seq))
    obs_pf = obs_nf = obs_ps = obs_ns = 0
    for y in seqs:
        for k in range(1, len(y)):
            if y[k-1] == 1: obs_nf += 1; obs_pf += y[k]
            else:           obs_ns += 1; obs_ps += y[k]
    obs = (obs_pf/obs_nf)/(obs_ps/obs_ns)
    sims = []
    for _ in range(30):
        pfl = nfl = psl = nsl = 0
        for y in seqs:
            sh = y.copy(); rng.shuffle(sh)   # 轨迹内打乱，保持该轨迹的失败总数
            for k in range(1, len(sh)):
                if sh[k-1] == 1: nfl += 1; pfl += sh[k]
                else:            nsl += 1; psl += sh[k]
        sims.append((pfl/nfl)/(psl/nsl))
    sims = np.array(sims)
    print(f"  {nm:<20} 观察 ratio={obs:.4f}  打乱零分布 mean={sims.mean():.4f} "
          f"[{np.percentile(sims,2.5):.4f},{np.percentile(sims,97.5):.4f}]")

print()
print("=" * 78)
print("4. 分离「累积损伤」与「持续性」：控制累计失败数后的条件持续性")
print("=" * 78)
# 在每个累计失败数层内，看 P(fail|prev fail) vs P(fail|prev succ)
lay = collections.defaultdict(lambda: [0, 0, 0, 0])   # cum -> [pf,nf,ps,ns]
for tr in S:
    st = [s for s in tr['steps'] if s[0] in (EB, SE)]
    # 逐工具独立计累计
    cum = {EB: 0, SE: 0}
    for k in range(1, len(st)):
        tp, yp = st[k-1][0], st[k-1][1]
        tc, yc = st[k][0], st[k][1]
        if tp == tc:
            c = min(cum[tc], 5)
            if yp == 1: lay[c][0] += yc; lay[c][1] += 1
            else:       lay[c][2] += yc; lay[c][3] += 1
        cum[tp] += yp
print(f"  {'cum_fail':>9}{'P(f|f)':>10}{'P(f|s)':>10}{'ratio':>9}{'n_fail':>12}{'n_succ':>12}")
for c in sorted(lay):
    pf, nfq, ps, nsq = lay[c]
    if nfq < 500 or nsq < 500: continue
    a = pf/nfq; b = ps/nsq
    print(f"  {c:>9}{a:>10.4f}{b:>10.4f}{a/b:>9.3f}{nfq:>12,}{nsq:>12,}")
print("  -> 若各层内 ratio 仍 >1，则持续性独立于累积损伤")

json.dump({'tool_transition': {str(k): v for k, v in tr_tool_f.items()}},
          open('decompose_results.json', 'w'), indent=1)
print("\n-> decompose_results.json")
