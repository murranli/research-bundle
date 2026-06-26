#!/usr/bin/env python3
"""
jsonsafe.py —— 统一 JSON 容错解析（契约 R7）

v1.0 的问题：目标解析 / 子问题数组 / URL数组 / 工作流档案 各写了一份容错逻辑，
强度不一，且"合法 JSON 但 schema 不对时静默返回空"。这里收口成唯一实现：

  parse(text)            -> (data, meta)   尽最大努力解析；data 为 dict/list 或 None
  parse_or(text, default)-> data           解析失败返回 default
  expect(text, required) -> (data, ok, missing)  解析 + 校验顶层必填键

容错策略（按序尝试，越靠后越激进）：
  1. 直接 json.loads
  2. 去掉 ```json ... ``` / ``` ... ``` 代码块包裹后再试
  3. 截取第一个 { 到最后一个 } （或 [ ... ]）再试
  4. 把"文本字段值内部"的裸英文双引号收敛为中文引号 ” 再试
     （网页标题、检索式里的英文引号是 v1.0 解析失败的头号根因）

用法：
  from jsonsafe import parse, parse_or, expect
  CLI: python jsonsafe.py <file|-stdin>   # 打印解析结果与诊断
"""
import json
import re
import sys

_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*|\s*```\s*$")
# 易含裸引号的字段名（值内部的英文引号收敛为中文引号）
_QUOTE_FIELDS = (
    "title|reason|quality_basis|confidence_basis|dropped_note|relevance_reason|"
    "drop_reason|query|question|focus|answer|point|summary|note"
)
_FIELD_RE = re.compile(
    r'"(' + _QUOTE_FIELDS + r')"\s*:\s*"(.*?)"(\s*[,}\]\n])',
    flags=re.S,
)


def _strip_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # 去掉首行 ```json / ``` 和结尾 ```
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```\s*$", "", s)
    return s.strip()


def _slice_braces(s: str):
    """截取最外层 {...} 或 [...]，丢弃前后噪音文字。"""
    candidates = []
    for open_c, close_c in (("{", "}"), ("[", "]")):
        i, j = s.find(open_c), s.rfind(close_c)
        if i != -1 and j != -1 and j > i:
            candidates.append(s[i : j + 1])
    # 取更长的那个（通常是真正的载荷）
    return max(candidates, key=len) if candidates else s


def _converge_inner_quotes(s: str) -> str:
    """把指定字段值内部的英文双引号 " 换成中文引号 ”，避免破坏 JSON 结构。"""
    return _FIELD_RE.sub(
        lambda m: '"%s": "%s"%s'
        % (m.group(1), m.group(2).replace('"', "\u201d"), m.group(3)),
        s,
    )


def parse(text):
    """返回 (data, meta)。meta.method 记录命中哪一层；data 为 None 表示彻底失败。"""
    meta = {"method": None, "tried": []}
    if text is None:
        return None, {"method": None, "tried": ["empty"]}
    if not isinstance(text, str):
        # 已经是 dict/list，直接通过
        return text, {"method": "passthrough", "tried": []}

    raw = text

    def _try(label, candidate):
        meta["tried"].append(label)
        try:
            return json.loads(candidate)
        except Exception:
            return None

    d = _try("direct", raw)
    if d is not None:
        meta["method"] = "direct"
        return d, meta

    stripped = _strip_fence(raw)
    d = _try("fence", stripped)
    if d is not None:
        meta["method"] = "fence"
        return d, meta

    sliced = _slice_braces(stripped)
    d = _try("slice", sliced)
    if d is not None:
        meta["method"] = "slice"
        return d, meta

    fixed = _converge_inner_quotes(sliced)
    d = _try("quote_fix", fixed)
    if d is not None:
        meta["method"] = "quote_fix"
        return d, meta

    return None, meta


def parse_or(text, default=None):
    d, _ = parse(text)
    return d if d is not None else default


def expect(text, required):
    """解析并校验顶层必填键。返回 (data, ok, missing)。
    解决 v1.0 '合法 JSON 但 schema 不对时静默返回空' —— 这里显式报缺。"""
    d, _ = parse(text)
    if d is None:
        return None, False, list(required)
    if not isinstance(d, dict):
        return d, False, list(required)
    missing = [k for k in required if k not in d]
    return d, len(missing) == 0, missing


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    text = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    data, meta = parse(text)
    if data is None:
        print("PARSE FAILED. tried=%s" % meta["tried"], file=sys.stderr)
        sys.exit(1)
    print("# parsed via: %s" % meta["method"], file=sys.stderr)
    print(json.dumps(data, ensure_ascii=False, indent=2))
