#!/usr/bin/env python3
"""
doctor.py —— 把 agent-reach doctor 的状态转成契约里的 channels 三档快照（契约 R9）

两类（doctor OK 的渠道一律同级，不做信任分档）：
  available   —— ok，可用于检索；具体选哪个由"子问题↔渠道匹配度"决定，不是按渠道优劣预排序
  unavailable —— warn / off，本 run 不可用，不得写进检索策略

用法：
  python doctor.py snapshot [--run-id <id>] [--root .]      # 跑 doctor、分类、（可选）写入 manifest
  python doctor.py snapshot --from-file doctor.txt          # 离线：从已保存的 doctor 输出解析
"""
import argparse
import json
import re
import subprocess
import sys

# 显示名 / 别名 -> 规范 slug。覆盖 doctor 输出里可能出现的中英文写法。
NAME2SLUG = {
    "小红书": "xiaohongshu", "xiaohongshu": "xiaohongshu", "xhs": "xiaohongshu",
    "雪球": "xueqiu", "xueqiu": "xueqiu",
    "twitter": "twitter", "twitter/x": "twitter", "x": "twitter",
    "github": "github",
    "reddit": "reddit",
    "b站": "bilibili", "bilibili": "bilibili", "哔哩哔哩": "bilibili",
    "youtube": "youtube",
    "v2ex": "v2ex",
    "rss": "rss",
    "全网语义搜索": "exa", "exa": "exa", "全网语义搜索(exa)": "exa",
    "任意网页": "jina", "jina": "jina", "任意网页(jina)": "jina", "jina reader": "jina",
    "小宇宙播客转文字": "xiaoyuzhou", "小宇宙": "xiaoyuzhou", "xiaoyuzhou": "xiaoyuzhou",
    "linkedin": "linkedin",
}



def _slug(name):
    key = name.strip().lower()
    if key in NAME2SLUG:
        return NAME2SLUG[key]
    # 容忍 "全网语义搜索 (Exa)" 这类带空格/括号的写法
    key2 = re.sub(r"\s+", "", key)
    return NAME2SLUG.get(key2, key2)


def _run_doctor():
    try:
        out = subprocess.run(
            ["agent-reach", "doctor"], capture_output=True, text=True, timeout=120
        )
        return (out.stdout or "") + "\n" + (out.stderr or "")
    except FileNotFoundError:
        return None
    except Exception as e:  # noqa
        return "ERROR: %s" % e


def parse_doctor(text):
    """从 doctor 文本里抽 (slug -> status)。status ∈ {ok, warn, off}。
    宽松解析：每行若同时含一个已知渠道名和一个状态词，就记一条。

    Agent-Reach 当前输出既可能使用 emoji，也可能使用 ASCII 状态标记：
    [!] = 已安装但需配置/登录/代理，视为 warn；[X] = 未安装/未配置，视为 off。
    """
    status_map = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        low = line.lower()
        # 判定状态：优先看符号/关键词
        if "✅" in line or re.search(r"\bok\b", low):
            st = "ok"
        elif "⚠" in line or "[!]" in line or "warn" in low:
            st = "warn"
        elif "❌" in line or "[x]" in low or re.search(r"\boff\b|disabled|unavailable|未安装|未配置", low):
            st = "off"
        else:
            continue
        # 找渠道名：长名优先（避免 "v2ex" 被短名误吞）；
        # 短 ASCII 别名（如 "x"）要求词边界，否则会命中 "v2ex"/"exa" 里的字母。
        found = None
        for name in sorted(NAME2SLUG, key=len, reverse=True):
            if name.isascii() and len(name) <= 3:
                if re.search(r"\b%s\b" % re.escape(name), low):
                    found = NAME2SLUG[name]
                    break
            elif name in low:
                found = NAME2SLUG[name]
                break
        if found:
            status_map.setdefault(found, st)
    return status_map


def classify(status_map):
    available, unavail = [], []
    for slug, st in status_map.items():
        (available if st == "ok" else unavail).append(slug)
    return sorted(available), sorted(unavail)


def _main():
    from datetime import datetime, timedelta, timezone

    p = argparse.ArgumentParser(prog="doctor")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--run-id", default=None)
    s.add_argument("--root", default=".")
    s.add_argument("--from-file", default=None, help="离线解析已保存的 doctor 输出")
    a = p.parse_args()

    if a.from_file:
        text = open(a.from_file, encoding="utf-8").read()
    else:
        text = _run_doctor()
        if text is None:
            print("agent-reach 未安装或不在 PATH。请先安装，或用 --from-file 提供 doctor 输出。", file=sys.stderr)
            sys.exit(2)

    status_map = parse_doctor(text)
    available, unavail = classify(status_map)

    tz = timezone(timedelta(hours=8))
    snap = {
        "snapshot_at": datetime.now(tz).isoformat(timespec="seconds"),
        "available": available,
        "unavailable": unavail,
    }
    print(json.dumps(snap, ensure_ascii=False, indent=2))

    if a.run_id:
        sys.path.insert(0, __file__.rsplit("/", 1)[0])
        import state_io
        state_io.set_key(a.run_id, "channels", snap, a.root)
        print("→ written to manifest channels of %s" % a.run_id, file=sys.stderr)


if __name__ == "__main__":
    _main()
