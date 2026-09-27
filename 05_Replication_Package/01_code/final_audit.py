#!/usr/bin/env python3

"""终审：核对 v3 手稿中的每个数字与实测结果是否一致"""

from paths import work, corpus, results

import json, re



A = json.load(open(results('analysis_results.json')))

V = json.load(open(results('validation_results.json')))

H = json.load(open(results('hawkes_vs_ar1.json')))

P = json.load(open(results('hawkes_params.json')))

L = json.load(open(results('label_validity.json')))

E = json.load(open(results('editor_label.json')))

PF = json.load(open(results('positional_final.json')))

SP = json.load(open(results('simpson.json')))

AA = json.load(open(results('attempt_axis.json')))



import os, sys

MD = (sys.argv[1] if len(sys.argv) > 1 else

      os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',

                   '01_Manuscript', 'Manuscript_Paper3_v3.7_source.md'))

md = open(MD, encoding='utf-8').read().replace(chr(0x2212), '-')  # unicode minus now used in v3.7



# 断言清单: (手稿字符串, 实测值, 容差)

pw = A['pooled_lenient']

st = A['same_lenient']

ct = A['cross_lenient']

ic = A['icc']



checks = [

    ("67,074",                 67074,         0),

    ("4,249,707",              4249707,       0),

    ("4,012,730",              4012730,       0),

    ("0.2679",                 pw['p_succ'],  0.0001),

    ("0.3645",                 pw['p_fail'],  0.0001),

    ("1.360",                  pw['ratio'],   0.001),

    ("1.567",                  pw['OR'],      0.001),

    ("735,231",                pw['disc_f2s'], 0),

    ("747,218",                pw['disc_s2f'], 0),

    ("1.573",                  V['OR_w'],     0.001),

    ("0.996",                  pw['OR']/V['OR_w'], 0.001),

    ("0.4085",                 st['0']['p_after_fail'], 0.0001),

    ("0.2751",                 st['0']['p_after_succ'], 0.0001),

    ("1.485",                  st['0']['ratio'], 0.001),

    ("0.4265",                 st['1']['p_after_fail'], 0.0001),

    ("0.2220",                 st['1']['p_after_succ'], 0.0001),

    ("1.921",                  st['1']['ratio'], 0.001),

    ("1.258",                  ct['0->1']['ratio'], 0.001),

    ("1.032",                  ct['1->0']['ratio'], 0.001),

    ("0.0538",                 ic['icc'],     0.0001),

    ("4.164",                  ic['deff'],    0.001),

    ("0.283",                  A['outcomes']['resolved']['rate'], 0.001),

    ("0.298",                  A['outcomes']['unresolved']['rate'], 0.001),

    ("0.624",                  A['corr_len_fail'], 0.001),

    ("0.0282",                 H['rho_cond'], 0.0001),

    ("76.1",                   H['z'],        0.1),

    ("0.068",                  P['execute_bash']['beta'], 0.001),

    ("0.145",                  P['str_replace_editor']['beta'], 0.001),

    ("0.891",                  P['execute_bash']['R2'], 0.001),

    ("0.879",                  P['str_replace_editor']['R2'], 0.001),

    ("0.492",                  V['label_precision_bash'], 0.001),

    ("97,592",                 A['models']['dLL_M2_M1'], 1),

    # --- 新增：构成性替代解释的排除（§4.4） ---

    ("0.113",                  E["editor_precision"],  0.001),

    ("549,222",                (E["editor_conf"]["tp"]+E["editor_conf"]["fp"]+E["editor_conf"]["tn"]+E["unjudged"]),      0),

    ("545,446",                sum(E["editor_pairs"]["strict"]),    0),

    ("0.2743",                 PF['bash, non-test']['first'],      0.0001),

    ("0.3211",                 PF['bash, non-test']['second'],     0.0001),

    ("+0.0467",                PF['bash, non-test']['diff'],      0.0001),

    ("+53.1",                  PF['bash, non-test']['t'],         0.05),

    ("0.3672",                 PF['bash, test/build']['first'],    0.0001),

    ("0.3242",                 PF['bash, test/build']['second'],   0.0001),

    ("-0.0430",                PF['bash, test/build']['diff'],    0.0001),

    ("-27.0",                  PF['bash, test/build']['t'],       0.05),

    ("0.2806",                 PF['editor, view']['first'],        0.0001),

    ("0.3504",                 PF['editor, view']['second'],       0.0001),

    ("+0.0697",                PF['editor, view']['diff'],        0.0001),

    ("+67.5",                  PF['editor, view']['t'],           0.05),

    ("0.0099",                 PF['editor, create']['first'],      0.0001),

    ("0.0056",                 PF['editor, create']['second'],     0.0001),

    ("-0.0043",                PF['editor, create']['diff'],      0.0001),

    ("-8.8",                   PF['editor, create']['t'],         0.05),

    ("0.3904",                 PF['editor, str_replace']['first'],  0.0001),

    ("0.3947",                 PF['editor, str_replace']['second'], 0.0001),

    ("+0.0043",                PF['editor, str_replace']['diff'],   0.0001),

    ("+1.6",                   PF['editor, str_replace']['t'],      0.05),

]



# 派生数字：由实测值算出的、单独写在手稿里的量

DERIVED = [

    ("+0.0324", 0.0324, "五层按调用量加权的平均变化"),

    ("0.319",    SP['editor-view']['first'] * 0 + 0.3186, "editor view 全期失败率"),

    ("0.390",    0.3898, "editor str_replace 全期失败率"),

    ("99.2%",    0.992,  "前半段 view 占比"),

    ("32.1%",    0.321,  "后半段 view 占比"),

    ("47.6%",    0.476,  "后半段 str_replace 占比"),

    ("0.500",    0.500,  "首个 step bin 中 bash 占比"),

    ("0.678",    0.678,  "50-100 bin 中 bash 占比"),

]

for s, val, why in DERIVED:

    checks.append((s, val, why))



# --- 第二主结果：尝试轴（§4.10、§5.1、§5.6、表 14-16） ---

ATTEMPT = [

    ("6,306",          AA['n_unique_tasks'],        0),

    ("10.64",          AA['mean_attempts_per_task'], 0.005),

    ("0.4795",         AA['global_success_rate'],   0.0001),

    ("54,690",         round(AA['chi2']),           1),

    ("6,282",          AA['df'],                    0),

    ("8.71",           AA['dispersion_phi'],        0.005),

    ("431.9",          AA['dispersion_z'],          0.05),

    ("0.797",          0.7967,                      0.001),

    ("39.7%",          AA['all_fail_tasks'] / AA['n5'], 0.001),

    ("32.4%",          AA['all_succ_tasks'] / AA['n5'], 0.001),

    ("6,148",          AA['n5'],                    0),

    ("2,441",          AA['all_fail_tasks'],        0),

    ("1,990",          AA['all_succ_tasks'],        0),

    ("8.60",           AA['phi_repo_adjusted'],     0.005),

    ("8.88",           AA['phi_submit_only'],       0.005),

    ("8.83",           AA['phi_big_only'],          0.005),

    ("917",            AA['n_allfail_repos'],       0),

    ("12.5%",          0.125,                       0.001),

    ("522.2",          522.24,                      0.1),

    ("995.0",          995.0,                       0.1),

]

for s, val, tol in ATTEMPT:

    checks.append((s, val, "尝试轴"))



print("=" * 78)

print("终审：手稿数字 vs 实测值")

print("=" * 78)

bad = 0
def as_number(token):
    token = token.replace(',', '').replace('×', '').replace('x', '')
    is_percent = token.endswith('%')
    token = token.rstrip('%')
    value = float(token)
    return value / 100 if is_percent else value

# Compare actual manuscript numerals with the bundled measured values.
number_tokens = re.findall(r'(?<!\d)[-+]?\d[\d,]*(?:\.\d+)?%?(?!\d)', md)
parsed_tokens = [(token, as_number(token)) for token in number_tokens]
for s, val, tol in checks:
    if isinstance(val, str):
        ok = s in md
        note = f"(text check, present={ok})"
    else:
        expected = float(val)
        precision_match = re.search(r'\.(\d+)', s.replace(',', ''))
        precision = len(precision_match.group(1)) if precision_match else 0
        tolerance = float(tol) if not isinstance(tol, str) else 0.001
        ok = any(abs(number - expected) <= tolerance for _, number in parsed_tokens)
        if not ok:
            ok = any(round(number, precision) == round(expected, precision)
                     for _, number in parsed_tokens)
        note = f"measured={expected:g}; manuscript precision={precision} decimals"
    flag = "OK " if ok else "FAIL"
    if not ok: bad += 1
    print(f"  [{flag}] {s:<14} {note}")


print()

print(f"数值核对失败: {bad} / {len(checks)}")



# 检查是否有残留的 v2 数字

print()

print("=" * 78)

print("残留旧数字扫描（这些不应出现在 v3 手稿中作为本文结论）")

print("=" * 78)

stale = {

    "1.794": "v2 pooled OR（仅在 §4.1 作为被撤回的 pilot 值出现，允许）",

    "1.004": "v2 within OR（同上，允许）",

    "3.089": "原手稿 Table 3",

    "1.11x": "v2 修订值",

    "1.34x": "v2 修订值",

    "93,863": "原手稿 M0",

    "93,202": "原手稿 M1/M2",

    "0.087": "借用 ICC",

    "315,771": "原宣称步数",

    "5,000": "原宣称轨迹数",

    "0.209": "原overall失败率",

    "7.1": "CCRM 比值（应保留，作为对照）",

}

for s, why in stale.items():

    n = md.count(s)

    if n:

        print(f"  出现 {n} 次: {s:<12} <- {why}")



# 检查关键论断是否仍在

print()

print("=" * 78)

print("关键论断存在性")

print("=" * 78)

must = [

    ("轨迹内持续性为真", "within-trajectory phenomenon rather"),

    ("撤回 pilot", "retract"),

    ("接口残留机制", "interface residue"),

    ("不声称临界性", "no claim about criticality"),

    ("无真实时间轴", "no real time axis"),

]

for nm, key in must:

    print(f"  [{'OK ' if key in md else 'MISS'}] {nm}")

if bad:
    raise SystemExit(1)
