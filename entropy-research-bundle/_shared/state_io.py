#!/usr/bin/env python3
"""
state_io.py —— 状态文件读写的唯一入口（契约执行层）

所有子 skill 不直接 open() manifest，一律走这里，保证：
  - 原子写入（先写临时文件再 rename，避免半截写坏 manifest）
  - updated_at 自动维护
  - 产物落盘后自动回填 artifacts 指针
  - 中途入口 / 断点续跑的 stage 推进逻辑集中在一处

CLI：
  init   --request "<一句话>" [--scope investment|product|design] [--entry intent] [--root .]
  get    <run_id> [dotted.key]
  set    <run_id> <dotted.key> <json_value>
  write-artifact <run_id> <artifact_key> <path | -（读 stdin）>
  read-artifact  <run_id> <artifact_key>
  log    <run_id> <stage> <event> <summary>
  next-stage <run_id>            # 打印下一个待执行 stage（断点续跑用）
  advance <run_id> <stage> <status>   # 标记某 stage 状态

可被 import：from state_io import load, save, set_key, write_artifact, log_event, init_run
"""
import argparse
import json
import os
import random
import string
import sys
import tempfile
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))  # 东八区，避免 UTC 日期差一天
SCHEMA_VERSION = "2.0"
STAGES = ["intent", "decompose", "strategy", "retrieval", "audit", "compose", "render", "deliver"]
ARTIFACT_FILES = {
    "intent": "00_intent.json",
    "questions": "01_questions.json",
    "strategy": "02_strategy.json",
    "retrieval_dir": "03_retrieval/",
    "evidence": "04_evidence.json",
    "outline": "05_outline.json",
    "report_html": "06_report.html",
}


def _now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def run_dir(run_id, root="."):
    return os.path.join(root, ".entropy", run_id)


def _manifest_path(run_id, root="."):
    return os.path.join(run_dir(run_id, root), "run.json")


def _atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=os.path.basename(path) + ".",
        suffix=".tmp",
        dir=os.path.dirname(path),
        text=True,
    )
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def load(run_id, root="."):
    with open(_manifest_path(run_id, root), encoding="utf-8") as f:
        return json.load(f)


def save(manifest, root="."):
    manifest["updated_at"] = _now()
    path = _manifest_path(manifest["run_id"], root)
    _atomic_write(path, json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def init_run(request, scope=None, serves=None, scope_note=None, entry="intent", root="."):
    rid = "%s-%s" % (
        datetime.now(TZ).strftime("%Y%m%d-%H%M%S"),
        "".join(random.choices(string.hexdigits.lower(), k=4)),
    )
    manifest = {
        "run_id": rid,
        "schema_version": SCHEMA_VERSION,
        "created_at": _now(),
        "updated_at": _now(),
        "original_request": request,
        "scope": {"primary": scope, "serves": serves, "note": scope_note},
        "entry_stage": entry,
        "current_stage": entry,
        "language": "zh",
        "stage_status": {s: ("skipped" if STAGES.index(s) < STAGES.index(entry) else "pending") for s in STAGES},
        "artifacts": {k: None for k in ARTIFACT_FILES},
        "audit": {"round": 0, "max_rounds": 3, "verdict": None, "open_gaps": [], "next_strategy_seed": []},
        "budget": {"max_retrievals": 20, "retrievals_used": 0, "max_sources_per_dimension": 2, "stop_reason": None},
        "channels": {"snapshot_at": None, "available": [], "unavailable": []},
    }
    os.makedirs(run_dir(rid, root), exist_ok=True)
    os.makedirs(os.path.join(run_dir(rid, root), "03_retrieval"), exist_ok=True)
    os.makedirs(os.path.join(run_dir(rid, root), "deliverables"), exist_ok=True)
    save(manifest, root)
    return manifest


def _dig_set(d, dotted, value):
    keys = dotted.split(".")
    cur = d
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def _dig_get(d, dotted):
    cur = d
    for k in dotted.split("."):
        cur = cur[k]
    return cur


def set_key(run_id, dotted, value, root="."):
    m = load(run_id, root)
    _dig_set(m, dotted, value)
    return save(m, root)


def write_artifact(run_id, artifact_key, content, root="."):
    if artifact_key not in ARTIFACT_FILES:
        raise KeyError("unknown artifact_key: %s (valid: %s)" % (artifact_key, list(ARTIFACT_FILES)))
    fname = ARTIFACT_FILES[artifact_key]
    path = os.path.join(run_dir(run_id, root), fname)
    _atomic_write(path, content)
    m = load(run_id, root)
    m["artifacts"][artifact_key] = fname
    save(m, root)
    return path


def read_artifact(run_id, artifact_key, root="."):
    fname = ARTIFACT_FILES[artifact_key]
    path = os.path.join(run_dir(run_id, root), fname)
    with open(path, encoding="utf-8") as f:
        return f.read()


def log_event(run_id, stage, event, summary, metrics=None, cost_note=None, root="."):
    line = {"ts": _now(), "stage": stage, "event": event, "summary": summary}
    if metrics:
        line["metrics"] = metrics
    if cost_note:
        line["cost_note"] = cost_note
    path = os.path.join(run_dir(run_id, root), "audit_log.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


def next_stage(run_id, root="."):
    m = load(run_id, root)
    for s in STAGES:
        if m["stage_status"].get(s) not in ("done", "skipped"):
            return s
    return None


def advance(run_id, stage, status, root="."):
    m = load(run_id, root)
    m["stage_status"][stage] = status
    if status == "done":
        nxt = None
        idx = STAGES.index(stage)
        for s in STAGES[idx + 1 :]:
            if m["stage_status"].get(s) not in ("skipped",):
                nxt = s
                break
        if nxt:
            m["current_stage"] = nxt
    return save(m, root)


# ----------------------------- CLI -----------------------------
def _main():
    p = argparse.ArgumentParser(prog="state_io")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init")
    pi.add_argument("--request", required=True)
    pi.add_argument("--scope", default=None, help="诉求核心落点：investment|product|design")
    pi.add_argument("--serves", default=None, help="最终要导向/服务的下游目的（跨段诉求时填）")
    pi.add_argument("--scope-note", default=None, help="一句话：分析应聚焦什么、以什么为终点导向")
    pi.add_argument("--entry", default="intent", choices=STAGES)
    pi.add_argument("--root", default=".")

    pg = sub.add_parser("get")
    pg.add_argument("run_id")
    pg.add_argument("key", nargs="?", default=None)
    pg.add_argument("--root", default=".")

    ps = sub.add_parser("set")
    ps.add_argument("run_id")
    ps.add_argument("key")
    ps.add_argument("value")
    ps.add_argument("--root", default=".")

    pw = sub.add_parser("write-artifact")
    pw.add_argument("run_id")
    pw.add_argument("artifact_key")
    pw.add_argument("src")
    pw.add_argument("--root", default=".")

    pr = sub.add_parser("read-artifact")
    pr.add_argument("run_id")
    pr.add_argument("artifact_key")
    pr.add_argument("--root", default=".")

    pl = sub.add_parser("log")
    pl.add_argument("run_id")
    pl.add_argument("stage")
    pl.add_argument("event")
    pl.add_argument("summary")
    pl.add_argument("--root", default=".")

    pn = sub.add_parser("next-stage")
    pn.add_argument("run_id")
    pn.add_argument("--root", default=".")

    pa = sub.add_parser("advance")
    pa.add_argument("run_id")
    pa.add_argument("stage", choices=STAGES)
    pa.add_argument("status", choices=["done", "pending", "skipped", "failed", "blocked"])
    pa.add_argument("--root", default=".")

    a = p.parse_args()

    if a.cmd == "init":
        m = init_run(a.request, a.scope, a.serves, a.scope_note, a.entry, a.root)
        print(m["run_id"])
    elif a.cmd == "get":
        m = load(a.run_id, a.root)
        out = _dig_get(m, a.key) if a.key else m
        print(json.dumps(out, ensure_ascii=False, indent=2) if not isinstance(out, str) else out)
    elif a.cmd == "set":
        try:
            val = json.loads(a.value)
        except Exception:
            val = a.value  # 非 JSON 当字符串
        set_key(a.run_id, a.key, val, a.root)
        print("ok")
    elif a.cmd == "write-artifact":
        content = sys.stdin.read() if a.src == "-" else open(a.src, encoding="utf-8").read()
        path = write_artifact(a.run_id, a.artifact_key, content, a.root)
        print(path)
    elif a.cmd == "read-artifact":
        print(read_artifact(a.run_id, a.artifact_key, a.root))
    elif a.cmd == "log":
        log_event(a.run_id, a.stage, a.event, a.summary, root=a.root)
        print("logged")
    elif a.cmd == "next-stage":
        print(next_stage(a.run_id, a.root) or "")
    elif a.cmd == "advance":
        advance(a.run_id, a.stage, a.status, a.root)
        print("ok")


if __name__ == "__main__":
    _main()
