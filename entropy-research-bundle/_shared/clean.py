#!/usr/bin/env python3
"""
clean.py —— 正文机械去噪 + 按原文切块（audit 阶段用）

只做"去噪 + 切块 + 保序"，**不做关键词计数打分**——这正是修 v1.0 清洗的几处根因：
  - 不用财务/通用词表，不做 text.count 子串计数（会让长水块赢、词表内部重复计数）
  - 不按分数重排（块按原文 idx 保序输出）
  - 中文无需分词算词频（相关性判断交给上游 LLM 语义处理）

块的"是否相关"由 audit skill 语义判断，本脚本只把正文整理成干净、带序号的块。

CLI:
  python clean.py <file|-stdin> [--min-len 8] [--max-block-chars 1200]
    → 打印 JSON: {"blocks":[{"idx":0,"text":"…"}, …], "dropped_noise": N}
"""
import argparse
import json
import re
import sys

# 噪音模式：图片、HTML 标签、纯链接行、常见导航/样板碎片
_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_HTML = re.compile(r"<[^>]+>")
_MD_LINK = re.compile(r"\[([^\]]*)\]\((?:[^)]*)\)")  # 保留链接文字，去 URL
_URL_ONLY = re.compile(r"^\s*https?://\S+\s*$")
_NAV_HINTS = ("登录", "注册", "下载App", "扫码", "关注我们", "版权所有", "Cookie",
              "广告", "©", "All Rights Reserved", "分享到", "上一篇", "下一篇")


def _denoise_line(line: str) -> str:
    line = _IMG.sub("", line)
    line = _MD_LINK.sub(r"\1", line)
    line = _HTML.sub("", line)
    return line.rstrip()


def clean(text, min_len=8, max_block_chars=1200):
    if not isinstance(text, str):
        # read 记录的 raw 可能是已被存成字符串的正文；非字符串则转成字符串
        text = json.dumps(text, ensure_ascii=False)

    lines = text.replace("\r\n", "\n").split("\n")
    cleaned_lines, dropped = [], 0
    for ln in lines:
        raw = ln.strip()
        if not raw:
            cleaned_lines.append("")  # 保留空行作分块边界
            continue
        if _URL_ONLY.match(raw):
            dropped += 1
            continue
        if any(h in raw for h in _NAV_HINTS) and len(raw) < 40:
            dropped += 1
            continue
        dn = _denoise_line(ln)
        if dn.strip():
            cleaned_lines.append(dn)
        else:
            dropped += 1

    # 按空行 / markdown 标题切块；折叠多余空行
    blocks, buf = [], []
    def _flush():
        if buf:
            t = "\n".join(buf).strip()
            if t:
                blocks.append(t)
        buf.clear()

    for ln in cleaned_lines:
        if ln.strip() == "":
            _flush()
        elif re.match(r"^#{1,6}\s", ln):  # 标题独立成块边界
            _flush()
            buf.append(ln)
            _flush()
        else:
            buf.append(ln)
    _flush()

    # 过滤过短碎块；超长块软切
    out = []
    for b in blocks:
        if len(b) < min_len:
            dropped += 1
            continue
        if len(b) > max_block_chars:
            for i in range(0, len(b), max_block_chars):
                out.append(b[i:i + max_block_chars])
        else:
            out.append(b)

    return {"blocks": [{"idx": i, "text": t} for i, t in enumerate(out)],
            "dropped_noise": dropped}


def _main():
    p = argparse.ArgumentParser(prog="clean")
    p.add_argument("src")
    p.add_argument("--min-len", type=int, default=8)
    p.add_argument("--max-block-chars", type=int, default=1200)
    a = p.parse_args()
    text = sys.stdin.read() if a.src == "-" else open(a.src, encoding="utf-8").read()
    # 若输入是 read 记录 JSON，自动取其 raw 字段
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "raw" in obj:
            text = obj["raw"] if isinstance(obj["raw"], str) else json.dumps(obj["raw"], ensure_ascii=False)
    except Exception:
        pass
    print(json.dumps(clean(text, a.min_len, a.max_block_chars), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
