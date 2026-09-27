#!/usr/bin/env python3
"""构造 str_replace_editor 准严格标签，并做双侧标签效度检验。

发现：editor 的失败 observation 以字面量 "ERROR:" 开头（工具自身的输出约定），
而成功 observation 以固定若干前缀开头（"Here's the ..." / "File created successfully" /
"The file ... has been edited" 等）。这给出一个远比关键词正则可靠的判据。

本脚本：
 1) 统计 editor observation 的实际前缀分布，给出严格判据
 2) 计算 editor 宽松标签 vs 严格标签的混淆矩阵与精确率/召回率
 3) 在同一批 editor 对上比较两种标签下的持续性
 4) 同样给出 bash 的对照
"""
from paths import work, corpus, results
import collections, re, json
import numpy as np, pyarrow.parquet as pq

ERR = re.compile(
    r"(Traceback \(most recent call last\)|\b[A-Za-z_]*Error\b|\berror:"
    r"|command not found|No such file or directory|not found|fatal:"
    r"|FAILED|AssertionError|\bException\b)", re.I)
EXITCODE = re.compile(r"(?:exit code|exit status)\s*[:=]?\s*(-?\d+)", re.I)
FINISHED = re.compile(r"finished with exit code\s*(\d+)", re.I)

# editor 成功/失败前缀（由勘察得出）
ED_FAIL = re.compile(r"^\s*ERROR:")
ED_OK = re.compile(
    r"^\s*(Here's the|File created successfully|The file|"
    r"Successfully|Inserted|Edited|Undo)")


def bash_strict(c):
    m = EXITCODE.search(c)
    if m:
        try: return int(m.group(1)) != 0
        except ValueError: return False
    m = FINISHED.search(c)
    if m: return int(m.group(1)) != 0
    return False


def ed_strict(c):
    """editor 严格：ERROR: 前缀 = 失败；已知成功前缀 = 成功；其余记为不可判"""
    if ED_FAIL.match(c): return 1
    if ED_OK.match(c):   return 0
    return -1        # 不可判


f = pq.ParquetFile(corpus())

# ---- 1. 前缀分布 + 混淆矩阵 ----
pfx_fail = collections.Counter(); pfx_ok = collections.Counter()
conf = {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0}
pairs = {'lenient': [0, 0, 0, 0], 'strict': [0, 0, 0, 0], 'strict_bash': [0, 0, 0, 0]}
unjudged = 0
n_traj = 0
processed = 0

for b in f.iter_batches(batch_size=256, columns=['trajectory']):
    for r in b.to_pylist():
        n_traj += 1
        edseq = []; bseq = []
        for m in r['trajectory']:
            if m['role'] != 'tool': continue
            nm = m.get('name'); c = m.get('content') or ''
            if nm == 'str_replace_editor':
                s = ed_strict(c)
                l = 1 if ERR.search(c) else 0
                edseq.append((s, l))
                if s == 1: conf['tp'] += 1
                elif s == 0:
                    (conf['fp'] if l else conf['tn']) if l else None
                    if l: conf['fp'] += 1
                    else: conf['tn'] += 1
                else:
                    unjudged += 1
                    if l: pfx_fail[c[:50].replace('\n',' ')] += 1
                    else: pfx_ok[c[:50].replace('\n',' ')] += 1
            elif nm == 'execute_bash':
                s = bash_strict(c)
                l = 1 if (s or ERR.search(c)) else 0
                bseq.append((s, l, l))
        # 相邻对统计
        for k in range(1, len(edseq)):
            sp, lp = edseq[k-1]; sc, lc = edseq[k]
            if lp == 1: pairs['lenient'][0] += lc; pairs['lenient'][1] += 1
            else:       pairs['lenient'][2] += lc; pairs['lenient'][3] += 1
            if sp in (0,1) and sc in (0,1):
                if sp == 1: pairs['strict'][0] += sc; pairs['strict'][1] += 1
                else:       pairs['strict'][2] += sc; pairs['strict'][3] += 1
        for k in range(1, len(bseq)):
            sp, lp, _ = bseq[k-1]; sc, lc, _ = bseq[k]
            if sp == 1: pairs['strict_bash'][0] += sc; pairs['strict_bash'][1] += 1
            else:       pairs['strict_bash'][2] += sc; pairs['strict_bash'][3] += 1
    processed += 256
    if processed >= 20000:
        break

print("=" * 78)
print(f"采样 {n_traj:,} 轨迹")
print("=" * 78)
print()
print("editor 严格标签（ERROR: 前缀）混淆矩阵 vs 宽松标签:")
tp, fp, tn = conf['tp'], conf['fp'], conf['tn']
print(f"  严格=失败 & 宽松=失败 (tp) = {tp:,}")
print(f"  严格=成功 & 宽松=失败 (fp) = {fp:,}")
print(f"  严格=成功 & 宽松=成功 (tn) = {tn:,}")
if tp + fp:
    print(f"  => 宽松标签精确率 = {tp/(tp+fp):.4f}")
print(f"  不可判 (既无 FAIL 也无 OK 前缀) = {unjudged:,}")

print()
print("不可判样本中「宽松判为失败」的前缀 Top 10:")
for k, v in pfx_fail.most_common(10):
    print(f"  {v:>8,}  {k}")
print()
print("不可判样本中「宽松判为成功」的前缀 Top 10:")
for k, v in pfx_ok.most_common(10):
    print(f"  {v:>8,}  {k}")

print()
print("=" * 78)
print("editor 持续性：宽松 vs 严格")
print("=" * 78)
print(f"  {'标签':<16}{'P(f|f)':>10}{'P(f|s)':>10}{'ratio':>9}{'OR':>9}{'n对':>12}")
for mode in ('lenient', 'strict'):
    pf, nf, ps, ns = pairs[mode]
    if nf and ns:
        a = pf/nf; b2 = ps/ns
        orv = (a/(1-a))/(b2/(1-b2)) if 0 < a < 1 and 0 < b2 < 1 else float('nan')
        print(f"  {mode:<16}{a:>10.4f}{b2:>10.4f}{a/b2:>9.3f}{orv:>9.3f}{nf+ns:>12,}")
print()
print("bash 持续性（严格，对照）:")
pf, nf, ps, ns = pairs['strict_bash']
a = pf/nf; b2 = ps/ns
print(f"  {'strict':<16}{a:>10.4f}{b2:>10.4f}{a/b2:>9.3f}"
      f"{(a/(1-a))/(b2/(1-b2)):>9.3f}{nf+ns:>12,}")

json.dump({'editor_conf': conf, 'unjudged': unjudged,
           'editor_pairs': pairs,
           'editor_precision': tp/(tp+fp) if tp+fp else None},
          open(results('editor_label.json'),'w'), indent=1)
print("\n-> editor_label.json")
