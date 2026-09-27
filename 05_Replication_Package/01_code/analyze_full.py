#!/usr/bin/env python3
"""
全语料核心分析 —— 复现并升级手稿全部关键数字。

输入: full_seqs.json (由 extract_stream.py 生成)
      格式: [{'id','inst','repo','resolved','steps':[[tool_id, lenient, strict],...]}]
      tool_id: 0=execute_bash 1=str_replace_editor 2=think 3=finish 4=task_tracker

输出: analysis_results.json + 控制台报告
"""
import json, math, collections
import numpy as np

rng = np.random.default_rng(20260918)
EB, SE = 0, 1                      # 具名交互工具 id
INTERACTIVE = (EB, SE)


def load():
    return json.load(open('full_seqs.json'))


def sub(tr, key):
    """仅取交互工具 -> (tools, labels); key: 1=lenient, 2=strict"""
    t = [s[0] for s in tr['steps'] if s[0] in INTERACTIVE]
    y = [s[key] for s in tr['steps'] if s[0] in INTERACTIVE]
    return t, y


# ---------------- 1. pooled vs within ----------------
def pooled_within(S, key):
    pf0 = pf1 = nf0 = nf1 = 0
    b = c = 0
    for tr in S:
        _, y = sub(tr, key)
        for k in range(1, len(y)):
            if y[k-1] == 0: nf0 += 1; pf0 += y[k]
            else:           nf1 += 1; pf1 += y[k]
            if y[k-1] == 1 and y[k] == 0: b += 1
            if y[k-1] == 0 and y[k] == 1: c += 1
    p0 = pf0/max(nf0, 1); p1 = pf1/max(nf1, 1)
    orr = (p1/(1-p1))/(p0/(1-p0)) if 0 < p0 < 1 and 0 < p1 < 1 else float('nan')
    return dict(p_succ=p0, p_fail=p1, ratio=p1/p0 if p0 else float('nan'),
                OR=orr, disc_f2s=b, disc_s2f=c,
                within_OR=b/max(c, 1), n_pairs=nf0+nf1)


def permutation(S, obs_or, key, N=200):
    seqs = [np.array(sub(tr, key)[1]) for tr in S]
    seqs = [s for s in seqs if len(s) > 1]
    allsig = np.concatenate(seqs); lens = [len(s) for s in seqs]
    sims = []
    for _ in range(N):
        sh = allsig.copy(); rng.shuffle(sh)
        pf0 = pf1 = nf0 = nf1 = 0; i = 0
        for L in lens:
            y = sh[i:i+L]; i += L
            for k in range(1, len(y)):
                if y[k-1] == 0: nf0 += 1; pf0 += y[k]
                else:           nf1 += 1; pf1 += y[k]
        a0 = pf0/max(nf0, 1); a1 = pf1/max(nf1, 1)
        if 0 < a0 < 1 and 0 < a1 < 1:
            sims.append((a1/(1-a1))/(a0/(1-a0)))
    sims = np.array(sims)
    return dict(mean=float(sims.mean()),
                lo=float(np.percentile(sims, 2.5)),
                hi=float(np.percentile(sims, 97.5)),
                p=float((sims >= obs_or).mean()), n=len(sims))


# ---------------- 2. 同工具持续性 ----------------
def same_tool(S, key):
    out = {}
    for tool in INTERACTIVE:
        pf = ps = nf = ns = 0
        for tr in S:
            t, y = sub(tr, key)
            seq = [y[i] for i in range(len(t)) if t[i] == tool]
            for k in range(1, len(seq)):
                if seq[k-1] == 1: nf += 1; pf += seq[k]
                else:             ns += 1; ps += seq[k]
        a = pf/max(nf, 1); b = ps/max(ns, 1)
        out[tool] = dict(p_after_fail=a, p_after_succ=b,
                         ratio=a/b if b else float('nan'),
                         n_fail=nf, n_succ=ns)
    return out


# ---------------- 3. 跨工具 ----------------
def cross_tool(S, key):
    out = {}
    for A in INTERACTIVE:
        for B in INTERACTIVE:
            if A == B: continue
            pa = pb = na = nb = 0
            for tr in S:
                t, y = sub(tr, key)
                for k in range(1, len(t)):
                    if t[k] != B or t[k-1] != A: continue
                    if y[k-1] == 1: na += 1; pa += y[k]
                    else:           nb += 1; pb += y[k]
            a = pa/max(na, 1); b = pb/max(nb, 1)
            out[f"{A}->{B}"] = dict(p_after_fail=a, p_after_succ=b,
                                    ratio=a/b if b else float('nan'),
                                    n=(na, nb))
    return out


# ---------------- 4/5. 曲线 ----------------
def cum_curve(S, tool, key, maxc=8):
    bk = collections.defaultdict(lambda: [0, 0])
    for tr in S:
        t, y = sub(tr, key)
        cum = 0
        for k in range(len(t)):
            if t[k] != tool: continue
            bk[min(cum, maxc)][0] += y[k]; bk[min(cum, maxc)][1] += 1
            cum += y[k]
    return {k: dict(rate=v[0]/v[1] if v[1] else float('nan'), n=v[1])
            for k, v in sorted(bk.items())}


def step_curve(S, key):
    bins = [(0,5),(5,10),(10,15),(15,20),(20,30),(30,50),(50,100),(100,999)]
    bk = collections.defaultdict(lambda: [0, 0])
    for tr in S:
        _, y = sub(tr, key)
        for k, v in enumerate(y):
            for lo, hi in bins:
                if lo <= k < hi:
                    bk[f"{lo}-{hi}"][0] += v; bk[f"{lo}-{hi}"][1] += 1
                    break
    return {k: dict(rate=v[0]/v[1] if v[1] else float('nan'), n=v[1])
            for k, v in sorted(bk.items(), key=lambda x: int(x[0].split('-')[0]))}


# ---------------- 6. ICC ----------------
def icc(S, key):
    ms, ns = [], []
    for tr in S:
        _, y = sub(tr, key)
        if len(y) >= 3:
            ms.append(float(np.mean(y))); ns.append(len(y))
    if not ms: return dict(icc=float('nan'))
    ms = np.array(ms); ns = np.array(ns); k = len(ms)
    grand = float(np.average(ms, weights=ns))
    ss_b = float(np.sum(ns*(ms-grand)**2))
    ss_w = float(np.sum(ns*ms*(1-ms)))
    df_b = k-1; df_w = int(ns.sum()-k)
    ms_b = ss_b/df_b; ms_w = ss_w/max(df_w, 1)
    mbar = float(ns.mean())
    den = ms_b+(mbar-1)*ms_w
    v = (ms_b-ms_w)/den if den > 0 else 0.0
    v = max(0.0, min(1.0, v))
    return dict(icc=v, mean_steps=mbar, n_traces=k,
                deff=1+(mbar-1)*v, ms_between=ms_b, ms_within=ms_w)


# ---------------- 7. 模型 LL ----------------
def ll_one(L):
    L = np.asarray(L)
    if L.size == 0 or L.sum() == 0 or L.sum() == L.size: return 0.0, 0
    i = int(np.argmax(L))
    def t(k, n):
        if n == 0 or k == 0 or k == n: return 0.0, 0
        e = k/n
        return k*math.log(e)+(n-k)*math.log(1-e), 1
    a, p0 = t(L[:i+1].sum(), len(L[:i+1]))
    b, p1 = t(L[i+1:].sum(), len(L[i+1:]))
    return a+b, p0+p1


def model_ll(S, key):
    ll0 = ll1 = ll2 = 0.0; n0 = n1 = n2 = 0
    for tr in S:
        t, y = sub(tr, key)
        if not y: continue
        a, p = ll_one(y); ll1 += a; n1 += p
        for tool in INTERACTIVE:
            s2 = [y[i] for i in range(len(t)) if t[i] == tool]
            if len(s2) >= 2:
                a, p = ll_one(s2); ll2 += a; n2 += p
        k = sum(y); ns = len(y)
        if 0 < k < ns:
            e = k/ns
            ll0 += k*math.log(e)+(ns-k)*math.log(1-e); n0 += 1
    return dict(M0=ll0, M1=ll1, M2=ll2, n0=n0, n1=n1, n2=n2,
                dLL_M2_M1=ll2-ll1, LR_M1_M0=2*(ll1-ll0))


# ---------------- 8. 轨迹级关联 ----------------
def outcomes(S, key):
    """resolved 与失败率的关系"""
    r = collections.defaultdict(lambda: [0, 0, 0])   # [fail, steps, traces]
    for tr in S:
        _, y = sub(tr, key)
        if not y: continue
        k = tr['resolved']
        r[k][0] += sum(y); r[k][1] += len(y); r[k][2] += 1
    return {('resolved' if k else 'unresolved'):
            dict(rate=v[0]/v[1] if v[1] else float('nan'),
                 steps=v[1], traces=v[2]) for k, v in sorted(r.items())}


def corr_len_fail(S, key):
    L, F = [], []
    for tr in S:
        _, y = sub(tr, key)
        if y: L.append(len(y)); F.append(sum(y))
    return float(np.corrcoef(L, F)[0, 1])


def main():
    S = load()
    R = {}
    nsteps = sum(len(tr['steps']) for tr in S)
    named = sum(len(sub(tr, 1)[0]) for tr in S)
    print(f"traces={len(S):,}  all_steps={nsteps:,}  interactive_steps={named:,}")

    for key, nm in [(1, 'lenient'), (2, 'strict')]:
        print("\n" + "#"*78)
        print(f"# 标签定义: {nm}")
        print("#"*78)

        pw = pooled_within(S, key); R[f'pooled_{nm}'] = pw
        print("\n[1] pooled / within")
        print(f"    P(fail|prev succ)={pw['p_succ']:.4f}  P(fail|prev fail)={pw['p_fail']:.4f}")
        print(f"    ratio={pw['ratio']:.3f}x  OR={pw['OR']:.3f}")
        print(f"    discordant: fail->ok={pw['disc_f2s']:,}  ok->fail={pw['disc_s2f']:,}")
        print(f"    within-trace OR={pw['within_OR']:.4f}")

        if key == 1:
            pm = permutation(S, pw['OR'], key, N=200)
            R['perm'] = pm
            print(f"    permutation null: mean={pm['mean']:.3f} "
                  f"95%=[{pm['lo']:.3f},{pm['hi']:.3f}] p={pm['p']:.4f} (n={pm['n']})")

        st = same_tool(S, key); R[f'same_{nm}'] = st
        print("\n[2] 同工具持续性 (Table 2)")
        for k, v in st.items():
            print(f"    tool={k}  P(f|f)={v['p_after_fail']:.4f} "
                  f"P(f|s)={v['p_after_succ']:.4f} ratio={v['ratio']:.3f}x")

        ct = cross_tool(S, key); R[f'cross_{nm}'] = ct
        print("\n[3] 跨工具转移 (Table 3)")
        for k, v in ct.items():
            print(f"    {k}  P(f|f)={v['p_after_fail']:.4f} "
                  f"P(f|s)={v['p_after_succ']:.4f} ratio={v['ratio']:.3f}x")

    # lenient-only 曲线与模型
    print("\n" + "#"*78)
    print("# 曲线 / 方差 / 模型 (lenient)")
    print("#"*78)

    print("\n[4] 累计失败曲线")
    for tool in INTERACTIVE:
        cc = cum_curve(S, tool, 1); R[f'cum_{tool}'] = cc
        print(f"    -- tool {tool} --")
        for k, v in cc.items():
            print(f"       cum={k:>2} rate={v['rate']:.4f} n={v['n']:,}")

    sc = step_curve(S, 1); R['step_curve'] = sc
    print("\n[5] 步序号曲线 (Table 6)")
    for k, v in sc.items():
        print(f"       bin {k:>7} rate={v['rate']:.4f} n={v['n']:,}")

    ic = icc(S, 1); R['icc'] = ic
    print("\n[6] 轨迹级方差分解")
    print(f"    ICC={ic['icc']:.4f}  mean_steps={ic['mean_steps']:.2f} "
          f"traces={ic['n_traces']:,}  deff={ic['deff']:.3f}")

    ml = model_ll(S, 1); R['models'] = ml
    print("\n[7] 嵌套模型")
    print(f"    M0={ml['M0']:,.1f}  M1={ml['M1']:,.1f}  M2={ml['M2']:,.1f}")
    print(f"    dLL(M2-M1)={ml['dLL_M2_M1']:,.1f}   LR(M1-M0)={ml['LR_M1_M0']:,.1f}")

    oc = outcomes(S, 1); R['outcomes'] = oc
    print("\n[8] resolved 分层失败率")
    for k, v in oc.items():
        print(f"    {k:12s} rate={v['rate']:.4f}  steps={v['steps']:,}  traces={v['traces']:,}")

    cl = corr_len_fail(S, 1); R['corr_len_fail'] = cl
    print(f"\n[9] corr(trajectory_length, n_failures) = {cl:.4f}")

    json.dump(R, open('analysis_results.json', 'w'), indent=1, default=str)
    print("\n-> analysis_results.json")


if __name__ == "__main__":
    main()
