#!/usr/bin/env python3
"""
retrieval_io.py —— 检索返回落盘 + 预算闸门（契约执行层，retrieval 阶段用）

每一次检索调用（一次 search 或一次 read）落一条 03_retrieval/rNNNN.json，
并自动累加 budget.retrievals_used。触顶则拒绝写入并置 budget.stop_reason。

CLI：
  add-record <run_id> --qid q2 --channel xiaohongshu --op search --backend OpenCLI \
      --cmd "opencli xiaohongshu search '...'" --query "..." --raw <file|-> \
      [--source-meta '<json>'] [--root .]
        → 写 rNNNN.json，自增编号，累加预算；打印 req_id 与剩余预算。
          若已触顶：不写、打印 BUDGET_CAPPED、退出码 3。
  budget   <run_id> [--root .]            # 打印 used/max/remaining/stop_reason
  list     <run_id> [--qid q2] [--root .] # 列出已落记录（req_id/qid/channel/op）
  annotate <run_id> <req_id> --filter '<json>' [--root .]  # 给某 search 记录补"粗筛裁决"

可被 import：from retrieval_io import add_record, budget_left, list_records
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_io  # 复用 run_dir / load / save / log_event

TZ = timezone(timedelta(hours=8))


def _retr_dir(run_id, root="."):
    return os.path.join(state_io.run_dir(run_id, root), "03_retrieval")


def _next_req_id(run_id, root="."):
    d = _retr_dir(run_id, root)
    os.makedirs(d, exist_ok=True)
    existing = glob.glob(os.path.join(d, "r*.json"))
    nums = []
    for f in existing:
        base = os.path.basename(f)[1:-5]  # strip 'r' and '.json'
        if base.isdigit():
            nums.append(int(base))
    return "r%04d" % ((max(nums) + 1) if nums else 1)


def budget_left(run_id, root="."):
    m = state_io.load(run_id, root)
    b = m["budget"]
    return b["max_retrievals"] - b["retrievals_used"], b


def add_record(run_id, qid, channel, op, backend, cmd, query, raw, source_meta=None, root="."):
    m = state_io.load(run_id, root)
    b = m["budget"]
    if b["retrievals_used"] >= b["max_retrievals"]:
        if not b.get("stop_reason"):
            state_io.set_key(run_id, "budget.stop_reason", "max_retrievals", root)
        return None, 0  # capped

    req_id = _next_req_id(run_id, root)
    rec = {
        "req_id": req_id,
        "qid": qid,
        "channel": channel,
        "op": op,
        "backend": backend,
        "cmd": cmd,
        "query": query,
        "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "raw": raw,
    }
    if source_meta is not None:
        rec["source_meta"] = source_meta
    if op == "search":
        rec["filter"] = None  # 待 annotate 补两层粗筛裁决

    path = os.path.join(_retr_dir(run_id, root), req_id + ".json")
    state_io._atomic_write(path, json.dumps(rec, ensure_ascii=False, indent=2))

    # 累加预算
    state_io.set_key(run_id, "budget.retrievals_used", b["retrievals_used"] + 1, root)
    left, _ = budget_left(run_id, root)
    return req_id, left


def list_records(run_id, qid=None, root="."):
    out = []
    for f in sorted(glob.glob(os.path.join(_retr_dir(run_id, root), "r*.json"))):
        rec = json.load(open(f, encoding="utf-8"))
        if qid and rec.get("qid") != qid:
            continue
        out.append(rec)
    return out


def annotate(run_id, req_id, filter_obj, root="."):
    path = os.path.join(_retr_dir(run_id, root), req_id + ".json")
    rec = json.load(open(path, encoding="utf-8"))
    rec["filter"] = filter_obj
    state_io._atomic_write(path, json.dumps(rec, ensure_ascii=False, indent=2))
    return rec


# ----------------------------- CLI -----------------------------
def _main():
    p = argparse.ArgumentParser(prog="retrieval_io")
    sub = p.add_subparsers(dest="action", required=True)

    pa = sub.add_parser("add-record")
    pa.add_argument("run_id")
    pa.add_argument("--qid", required=True)
    pa.add_argument("--channel", required=True)
    pa.add_argument("--op", required=True, choices=["search", "read"])
    pa.add_argument("--backend", default="")
    pa.add_argument("--cmd", default="")
    pa.add_argument("--query", default="")
    pa.add_argument("--raw", required=True, help="文件路径或 - (stdin)")
    pa.add_argument("--source-meta", default=None)
    pa.add_argument("--root", default=".")

    pb = sub.add_parser("budget")
    pb.add_argument("run_id")
    pb.add_argument("--root", default=".")

    pl = sub.add_parser("list")
    pl.add_argument("run_id")
    pl.add_argument("--qid", default=None)
    pl.add_argument("--root", default=".")

    pn = sub.add_parser("annotate")
    pn.add_argument("run_id")
    pn.add_argument("req_id")
    pn.add_argument("--filter", required=True)
    pn.add_argument("--root", default=".")

    a = p.parse_args()

    if a.action == "add-record":
        raw_text = sys.stdin.read() if a.raw == "-" else open(a.raw, encoding="utf-8").read()
        # raw 尽量按 JSON 存；非 JSON 则按字符串存
        try:
            raw_val = json.loads(raw_text)
        except Exception:
            raw_val = raw_text
        sm = json.loads(a.source_meta) if a.source_meta else None
        req_id, left = add_record(a.run_id, a.qid, a.channel, a.op, a.backend, a.cmd, a.query, raw_val, sm, a.root)
        if req_id is None:
            print("BUDGET_CAPPED：已达 max_retrievals，未写入。请收尾或回环判断。", file=sys.stderr)
            sys.exit(3)
        print("%s (剩余预算 %d)" % (req_id, left))
    elif a.action == "budget":
        left, b = budget_left(a.run_id, a.root)
        print(json.dumps({"used": b["retrievals_used"], "max": b["max_retrievals"],
                          "left": left, "stop_reason": b.get("stop_reason")}, ensure_ascii=False))
    elif a.action == "list":
        recs = list_records(a.run_id, a.qid, a.root)
        for r in recs:
            print("%s  %-4s  %-12s  %s" % (r["req_id"], r.get("qid", ""), r.get("channel", ""), r.get("op", "")))
        print("# total %d" % len(recs), file=sys.stderr)
    elif a.action == "annotate":
        annotate(a.run_id, a.req_id, json.loads(a.filter), a.root)
        print("annotated %s" % a.req_id)


if __name__ == "__main__":
    _main()
