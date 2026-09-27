#!/usr/bin/env python3
"""决定性检验：固定构成后，editor 失败率下降是否仍存在。

对手解释 B（构成性）：
  B1 editor 占交互调用比例随位置变化（已确认: 0.68 -> 0.38）
  B2 editor 内部命令类型构成随位置变化（view/create/str_replace/...）
  B3 bash 中测试类命令比例随位置变化，改变 editor 失败的「语境」

真正要回答的问题：
  「editor 失败率在轨迹后期下降」在固定了所有可观测构成变量后是否还存在？
  若存在 -> 支持「文件被读懂」；若消失 -> 构成伪影。
"""
from paths import work, corpus, results
import json, collections
import numpy as np

S = json.load(open(work('step_meta.json')))
CMDNAME = {0:'view',1:'create',2:'str_replace',3:'insert',4:'undo_edit',5:'other'}

def split_half(y):
    if len(y) < 8: return None
    h = len(y)//2
    return y[:h], y[h:]

# ---------------- 1. editor 子命令类型构成随位置 ----------------
print("=" * 78)
print("B2. editor 子命令类型构成 随位置的变化")
print("=" * 78)
B = [(0,5),(5,10),(10,15),(15,20),(20,30),(30,50),(50,100)]
cnt = collections.defaultdict(lambda: collections.Counter())
tot = collections.Counter()
for tr in S:
    ei = 0
    for s in tr['steps']:
        if s[0] != 1: continue
        ct = s[3]
        for lo,hi in B:
            if lo<=ei<hi:
                cnt[(lo,hi)][ct]+=1; tot[(lo,hi)]+=1; break
        ei += 1
hdr = "  " + f"{'bin':<9}" + "".join(f"{CMDNAME[i]:>13}" for i in range(6))
print(hdr)
for lo,hi in B:
    if not tot[(lo,hi)]: continue
    row = f"  {f'{lo}-{hi}':<9}"
    for i in range(6):
        row += f"{cnt[(lo,hi)][i]/tot[(lo,hi)]:>13.3f}"
    print(row)

# ---------------- 2. 按子命令类型分层，看下降是否仍在 ----------------
print()
print("=" * 78)
print("B3(关键). 固定子命令类型后，前后半段对比")
print("=" * 78)
print(f"  {'子命令':<14}{'前半段':>10}{'后半段':>10}{'差值':>10}{'t':>9}{'n轨迹':>10}")
for ct in range(6):
    fh=nh=sh=ns=0; diffs=[]
    for tr in S:
        y = [s[1] for s in tr['steps'] if s[0]==1 and s[3]==ct]
        r = split_half(y)
        if not r: continue
        a,b = r
        fh+=sum(a); nh+=len(a); sh+=sum(b); ns+=len(b)
        diffs.append(sum(b)/len(b)-sum(a)/len(a))
    if nh < 5000 or ns < 5000: 
        print(f"  {CMDNAME[ct]:<14}{'(样本不足)':>10}  n前={nh:,} n后={ns:,}")
        continue
    ra,rb = fh/nh, sh/ns
    d = np.array(diffs); se = d.std(ddof=1)/np.sqrt(len(d)) if len(d)>1 else float('nan')
    print(f"  {CMDNAME[ct]:<14}{ra:>10.4f}{rb:>10.4f}{rb-ra:>+10.4f}{d.mean()/se:>9.1f}{len(d):>10,}")

# ---------------- 3. 控制「前一个调用是否为测试类 bash」 ----------------
print()
print("=" * 78)
print("B4. 控制语境：editor 调用前一个交互调用是否为测试类 bash")
print("=" * 78)
for pretest in (0,1):
    seqs = []
    for tr in S:
        st = [s for s in tr['steps'] if s[0] in (0,1)]
        cur = []
        for k in range(len(st)):
            if st[k][0] != 1: continue
            prev_test = st[k-1][4] if k>0 and st[k-1][0]==0 else 0
            if prev_test == pretest:
                cur.append(st[k][1])
        if len(cur) >= 8: seqs.append(cur)
    fh=nh=sh=ns=0; diffs=[]
    for y in seqs:
        h=len(y)//2; a,b=y[:h],y[h:]
        fh+=sum(a); nh+=len(a); sh+=sum(b); ns+=len(b)
        diffs.append(sum(b)/len(b)-sum(a)/len(a))
    d=np.array(diffs); se=d.std(ddof=1)/np.sqrt(len(d))
    print(f"  前一调用为测试类bash={pretest}: 前半={fh/nh:.4f} 后半={sh/ns:.4f} "
          f"差={sh/ns-fh/nh:+.4f} t={d.mean()/se:+.1f} n={len(d):,}")

# ---------------- 4. bash 的测试比例随位置 ----------------
print()
print("=" * 78)
print("B5. bash 中测试类命令比例随位置")
print("=" * 78)
cnt2 = collections.defaultdict(lambda: [0,0])
for tr in S:
    bi = 0
    for s in tr['steps']:
        if s[0] != 0: continue
        for lo,hi in B:
            if lo<=bi<hi:
                cnt2[(lo,hi)][1]+=1
                if s[4]: cnt2[(lo,hi)][0]+=1
                break
        bi += 1
for lo,hi in B:
    t,n = cnt2[(lo,hi)]
    if n: print(f"  {lo:>3}-{hi:<4} 测试类占比={t/n:.4f}  n={n:,}")
