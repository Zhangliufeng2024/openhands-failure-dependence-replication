#!/usr/bin/env python3
"""确认 Simpson 悖论，并用正确的方式重做两个工具的位置对比。

关键发现: editor 的「下降」是子命令混合构成的伪影。
  view 的失败率其实随位置【上升】(0.2954 -> 0.3405)
  str_replace 基本持平 (0.3860 -> 0.3910)
  但 view 的占比从 0.99 掉到 0.32，而 view 的失败率【低于】str_replace
  -> 后期低失败率的 view 变少、高失败率的 str_replace 变多，
     合并后却显示下降 —— 典型 Simpson 悖论。

本脚本:
 1) 用固定子命令的方式重算 editor 的位置效应
 2) 用同样的方式重算 bash（bash 无子命令类型，改用「是否测试类」分层）
 3) 给出构成校正后的正确结论
"""
from paths import work, corpus, results
import json, collections
import numpy as np

S = json.load(open(work('step_meta.json')))
CMDNAME = {0:'view',1:'create',2:'str_replace',3:'insert',4:'undo_edit',5:'other'}

def halves(y):
    if len(y) < 8: return None
    h = len(y)//2
    return y[:h], y[h:]

print("=" * 78)
print("1. 验证 Simpson 悖论：editor 各子命令的失败率与占比")
print("=" * 78)
# 全期各子命令失败率
rate = collections.defaultdict(lambda: [0,0])
share = collections.defaultdict(lambda: collections.Counter())
for tr in S:
    for s in tr['steps']:
        if s[0]!=1: continue
        rate[s[3]][0]+=s[1]; rate[s[3]][1]+=1
print(f"  {'子命令':<14}{'全期失败率':>12}{'样本':>12}")
for ct in sorted(rate):
    f,n = rate[ct]
    print(f"  {CMDNAME[ct]:<14}{f/n:>12.4f}{n:>12,}")

print()
print("  说明: view 失败率最低，str_replace 最高。")
print("        后期 view 占比下降、str_replace 占比上升 -> 合并失败率应【上升】")
print("        但实际合并显示【下降】-> 说明各子命令内部的真实趋势被掩盖")

print()
print("=" * 78)
print("2. 构成校正后的 editor 位置效应（按子命令分层后加权）")
print("=" * 78)
print(f"  {'子命令':<14}{'前半段':>10}{'后半段':>10}{'变化':>10}{'t':>8}{'n轨迹':>9}")
tot_f=tot_n=tot_s=tot_sn=0
for ct in (0,1,2):
    fh=nh=sh=ns=0; diffs=[]
    for tr in S:
        y=[s[1] for s in tr['steps'] if s[0]==1 and s[3]==ct]
        r=halves(y)
        if not r: continue
        a,b=r
        fh+=sum(a); nh+=len(a); sh+=sum(b); ns+=len(b)
        diffs.append(sum(b)/len(b)-sum(a)/len(a))
    if nh<5000: continue
    d=np.array(diffs); se=d.std(ddof=1)/np.sqrt(len(d))
    ra,rb=fh/nh,sh/ns
    print(f"  {CMDNAME[ct]:<14}{ra:>10.4f}{rb:>10.4f}{rb-ra:>+10.4f}{d.mean()/se:>8.1f}{len(d):>9,}")

print()
print("=" * 78)
print("3. bash 同样处理：按「是否测试类命令」分层")
print("=" * 78)
print(f"  {'类型':<14}{'前半段':>10}{'后半段':>10}{'变化':>10}{'t':>8}{'n轨迹':>9}")
for istest in (0,1):
    fh=nh=sh=ns=0; diffs=[]
    for tr in S:
        y=[s[1] for s in tr['steps'] if s[0]==0 and s[4]==istest]
        r=halves(y)
        if not r: continue
        a,b=r
        fh+=sum(a); nh+=len(a); sh+=sum(b); ns+=len(b)
        diffs.append(sum(b)/len(b)-sum(a)/len(a))
    if nh<5000: continue
    d=np.array(diffs); se=d.std(ddof=1)/np.sqrt(len(d))
    nm = '测试/构建类' if istest else '其他命令'
    print(f"  {nm:<14}{fh/nh:>10.4f}{sh/ns:>10.4f}{sh/ns-fh/nh:>+10.4f}{d.mean()/se:>8.1f}{len(d):>9,}")

print()
print("=" * 78)
print("4. 完整构成校正（同时控制工具 x 子类型）")
print("=" * 78)
# 按 (tool, subtype) 分层，各层内做前后半段对比，再按层内样本量加权
layers = {}
for tool, sub, nm in [(0,0,'bash-其他'),(0,1,'bash-测试'),(1,0,'editor-view'),
                      (1,1,'editor-create'),(1,2,'editor-str_replace')]:
    fh=nh=sh=ns=0; diffs=[]
    for tr in S:
        y=[s[1] for s in tr['steps'] if s[0]==tool and s[4 if tool==0 else 3]==sub]
        r=halves(y)
        if not r: continue
        a,b=r
        fh+=sum(a); nh+=len(a); sh+=sum(b); ns+=len(b)
        diffs.append(sum(b)/len(b)-sum(a)/len(a))
    if nh>=5000:
        d=np.array(diffs)
        layers[nm] = (fh/nh, sh/ns, d.mean()/ (d.std(ddof=1)/np.sqrt(len(d))), nh, ns)

print(f"  {'分层':<18}{'前半段':>10}{'后半段':>10}{'变化':>10}{'t':>9}")
for nm,(ra,rb,t,nh,ns) in layers.items():
    print(f"  {nm:<18}{ra:>10.4f}{rb:>10.4f}{rb-ra:>+10.4f}{t:>9.1f}")
print()
print("  -> 若各层内均【不下降】，则「失败率随轨迹推进下降」这一说法被推翻。")

json.dump({nm:{'first':v[0],'second':v[1],'t':v[2],'n_first':v[3],'n_second':v[4]}
           for nm,v in layers.items()},
          open(results('simpson.json'),'w'), indent=1)
print("\n-> simpson.json")
