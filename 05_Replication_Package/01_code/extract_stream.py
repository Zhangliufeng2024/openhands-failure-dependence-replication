#!/usr/bin/env python3
"""流式提取：小 batch，低内存。输出紧凑格式以控制文件体积。"""
import json, re, time
import pyarrow.parquet as pq

SRC = "trajectories.parquet"
OUT = "full_seqs.json"

ERR = re.compile(
    r"(Traceback \(most recent call last\)|\b[A-Za-z_]*Error\b|\berror:"
    r"|command not found|No such file or directory|not found|fatal:"
    r"|FAILED|AssertionError|\bException\b)", re.I)
EXITCODE = re.compile(r"(?:exit code|exit status)\s*[:=]?\s*(-?\d+)", re.I)
EXITSTATUS = re.compile(r"returned non-zero exit status (\d+)", re.I)
FINISHED = re.compile(r"finished with exit code\s*(\d+)", re.I)

TOOL_ID = {'execute_bash': 0, 'str_replace_editor': 1,
           'think': 2, 'finish': 3, 'task_tracker': 4}


def bash_strict(c):
    if not c:
        return False
    m = EXITCODE.search(c)
    if m:
        try:
            return int(m.group(1)) != 0
        except ValueError:
            return False
    if EXITSTATUS.search(c):
        return True
    m = FINISHED.search(c)
    if m:
        return int(m.group(1)) != 0
    return False


def tool_failed(name, c, mode):
    if name == 'execute_bash':
        s = bash_strict(c)
        if mode == 'strict':
            return s
        return s or bool(ERR.search(c or ''))
    if name == 'str_replace_editor':
        if mode == 'strict':
            return False
        return bool(ERR.search(c or ''))
    return False


def main():
    f = pq.ParquetFile(SRC)
    out = []
    t0 = time.time()
    nbatch = 0
    for b in f.iter_batches(batch_size=256,
                            columns=['trajectory_id', 'instance_id', 'repo',
                                     'trajectory', 'resolved']):
        nbatch += 1
        for r in b.to_pylist():
            steps = []
            for m in r['trajectory']:
                if m['role'] != 'tool':
                    continue
                n = m.get('name') or '?'
                c = m.get('content') or ''
                steps.append([TOOL_ID.get(n, 9),
                              int(tool_failed(n, c, 'lenient')),
                              int(tool_failed(n, c, 'strict'))])
            if steps:
                out.append({'id': r['trajectory_id'],
                            'inst': r['instance_id'],
                            'repo': r['repo'],
                            'resolved': int(r['resolved'] or 0),
                            'steps': steps})
        if nbatch % 20 == 0:
            print(f"  batch {nbatch:4d}  traces {len(out):6,d}  {time.time()-t0:6.1f}s",
                  flush=True)

    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    nsteps = sum(len(t['steps']) for t in out)
    print(f"DONE traces={len(out):,} steps={nsteps:,} elapsed={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
