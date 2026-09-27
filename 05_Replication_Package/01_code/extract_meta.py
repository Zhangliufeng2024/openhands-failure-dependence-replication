#!/usr/bin/env python3
"""抽取 editor 的子命令类型 + bash 是否含测试关键词，用于固定构成后的条件分析。
输出: step_meta.json  [{'id','resolved','steps':[[tool_id, lenient, strict, cmd_type, is_test],...]}]
  tool_id: 0=bash 1=editor
  cmd_type: editor 的 command (view/create/str_replace/insert/undo_edit/other)
            或 bash 的 0
  is_test:  bash 命令是否像测试/构建（pytest|unittest|tox|make|npm test|...）
"""
import json, re, time
import pyarrow.parquet as pq

SRC = 'trajectories.parquet'
OUT = 'step_meta.json'

ERR = re.compile(
    r"(Traceback \(most recent call last\)|\b[A-Za-z_]*Error\b|\berror:"
    r"|command not found|No such file or directory|not found|fatal:"
    r"|FAILED|AssertionError|\bException\b)", re.I)
EXITCODE = re.compile(r"(?:exit code|exit status)\s*[:=]?\s*(-?\d+)", re.I)
FINISHED = re.compile(r"finished with exit code\s*(\d+)", re.I)
ED_FAIL = re.compile(r"^\s*ERROR:")
ED_OK = re.compile(r"^\s*(Here's the|File created successfully|The file|"
                   r"Successfully|Inserted|Edited|Undo)")
TESTRE = re.compile(
    r"\b(pytest|py\.test|unittest|tox|nox|make|setup\.py\s+test|"
    r"npm\s+(run\s+)?test|yarn\s+test|cargo\s+test|go\s+test|"
    r"mvn\s+test|gradle\s+test|jest|mocha|rspec|doctest|"
    r"python\s+-m\s+(pytest|unittest))\b", re.I)

TOOL_ID = {'execute_bash': 0, 'str_replace_editor': 1,
           'think': 2, 'finish': 3, 'task_tracker': 4}
CMD = {'view': 0, 'create': 1, 'str_replace': 2, 'insert': 3,
       'undo_edit': 4, 'other': 5}


def bash_strict(c):
    m = EXITCODE.search(c)
    if m:
        try: return int(m.group(1)) != 0
        except ValueError: return False
    m = FINISHED.search(c)
    if m: return int(m.group(1)) != 0
    return False


f = pq.ParquetFile(SRC)
out = []
t0 = time.time()
nb = 0
for b in f.iter_batches(batch_size=256,
                        columns=['trajectory_id', 'trajectory', 'resolved']):
    nb += 1
    for r in b.to_pylist():
        # 先建立 tool_call_id -> (name, arguments) 映射
        callmap = {}
        for m in r['trajectory']:
            if m['role'] != 'assistant':
                continue
            for tc in (m.get('tool_calls') or []):
                try:
                    callmap[tc['id']] = (tc['function']['name'],
                                         tc['function']['arguments'])
                except Exception:
                    pass
        steps = []
        for m in r['trajectory']:
            if m['role'] != 'tool':
                continue
            nm = m.get('name') or '?'
            c = m.get('content') or ''
            if nm == 'execute_bash':
                s = bash_strict(c)
                l = 1 if (s or ERR.search(c)) else 0
                steps.append([0, l, int(s), 0, int(bool(TESTRE.search(c)))])
            elif nm == 'str_replace_editor':
                l = 1 if ERR.search(c) else 0
                s = -1
                if ED_FAIL.match(c): s = 1
                elif ED_OK.match(c): s = 0
                ct = 5
                got = callmap.get(m.get('tool_call_id'))
                if got:
                    args = got[1]
                    try:
                        if isinstance(args, str):
                            args = json.loads(args)
                        ct = CMD.get(str(args.get('command', '')).lower(), 5)
                    except Exception:
                        ct = 5
                steps.append([1, l, s, ct, 0])
        if steps:
            out.append({'id': r['trajectory_id'],
                        'resolved': int(r['resolved'] or 0),
                        'steps': steps})
    if nb % 40 == 0:
        print(f"  batch {nb:4d}  {len(out):6,d}  {time.time()-t0:6.1f}s", flush=True)

json.dump(out, open(OUT, 'w'), separators=(',', ':'))
n = sum(len(t['steps']) for t in out)
print(f"DONE traces={len(out):,} steps={n:,} {time.time()-t0:.0f}s")
