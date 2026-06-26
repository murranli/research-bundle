#!/usr/bin/env python3
"""
deliver.py —— review-deliver 阶段执行层

读取 run 产物，生成 deliverables/review.md、deliverables/index.html、deliverables/report.pdf，
并按状态契约推进 deliver。

CLI:
  python deliver.py <run_id> [--root .] [--no-advance]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_io


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _read_text(path, default=""):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return default


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "auth_token",
    "session",
    "token",
    "xsec_token",
}


def _sanitize_url(url):
    try:
        parts = urlsplit(str(url))
    except Exception:
        return str(url)
    if parts.scheme not in ("http", "https"):
        return str(url)
    pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _SENSITIVE_QUERY_KEYS
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), parts.fragment))


def _sanitize_text_urls(text):
    if text is None:
        return ""
    return re.sub(r"https?://[^\s`<>\"]+", lambda m: _sanitize_url(m.group(0)), str(text))


def _artifact_path(run_id, key, root):
    fname = state_io.ARTIFACT_FILES[key]
    return os.path.join(state_io.run_dir(run_id, root), fname)


def _load_artifacts(run_id, root):
    base = state_io.run_dir(run_id, root)
    return {
        "intent": _read_json(os.path.join(base, "00_intent.json"), {}),
        "questions": _read_json(os.path.join(base, "01_questions.json"), {}),
        "strategy": _read_json(os.path.join(base, "02_strategy.json"), {}),
        "evidence": _read_json(os.path.join(base, "04_evidence.json"), {}),
        "outline": _read_json(os.path.join(base, "05_outline.json"), {}),
        "audit_log": [
            json.loads(line)
            for line in _read_text(os.path.join(base, "audit_log.jsonl")).splitlines()
            if line.strip()
        ],
        "retrieval_records": [
            _read_json(str(path), {})
            for path in sorted(Path(base, "03_retrieval").glob("r*.json"))
        ],
    }


def build_review(manifest, artifacts):
    intent = artifacts["intent"] or {}
    questions = artifacts["questions"] or {}
    strategy = artifacts["strategy"] or {}
    evidence = artifacts["evidence"] or {}
    outline = artifacts["outline"] or {}
    audit_log = artifacts["audit_log"]
    retrieval_records = artifacts["retrieval_records"]
    scope = manifest.get("scope") or {}
    budget = manifest.get("budget") or {}
    audit = manifest.get("audit") or {}
    channels = manifest.get("channels") or {}

    lines = []
    add = lines.append
    add("# 工作流复盘\n")
    add("## 0. Run 概览")
    add(f"- run_id：`{manifest.get('run_id')}`")
    add(f"- 原始诉求：{manifest.get('original_request')}")
    add(f"- 覆盖范围：`{scope.get('primary')}` → `{scope.get('serves')}`")
    add(f"- 审计裁决：`{audit.get('verdict')}`")
    add(f"- 检索预算：{budget.get('retrievals_used')}/{budget.get('max_retrievals')}")
    add(f"- 可用渠道：{', '.join(channels.get('available') or []) or '未记录'}")
    add("")

    add("## 1. 目标拆解")
    add(f"- 标准陈述：{intent.get('standard_statement') or '未记录'}")
    for idx, target in enumerate(intent.get("targets") or [], 1):
        add(
            "- 坐标%d：%s × %s（%s）→ %s"
            % (
                idx,
                target.get("purpose", "?"),
                target.get("object_dimension", "?"),
                target.get("object_category", "?"),
                target.get("focus", ""),
            )
        )
    add("")

    add("## 2. 子问题")
    total_q = 0
    for block in questions.get("decompositions") or []:
        add(f"### {block.get('coordinate', '未命名坐标')}")
        add(f"- 模型：`{block.get('model_index', '')}` {block.get('selected_model', '')}")
        for q in block.get("sub_questions") or []:
            total_q += 1
            add(f"- `{q.get('id', '?')}` {q.get('question')}")
    if total_q == 0:
        add("- 未记录子问题。")
    add("")

    add("## 3. 检索策略")
    selection = strategy.get("selection") or {}
    add(f"- 入选上限：{selection.get('limit', '未记录')}")
    for item in selection.get("selected") or []:
        qid = item.get("qid") or item.get("sub_question") or "?"
        add(f"- 入选：`{qid}`，理由：{item.get('relevance_reason', '')}")
    for item in selection.get("dropped") or []:
        qid = item.get("qid") or item.get("sub_question") or "?"
        reason = item.get("drop_reason") or item.get("relevance_reason") or ""
        add(f"- 暂缓：`{qid}`，理由：{reason}")
    add("")

    add("## 4. 检索执行")
    search_count = len([r for r in retrieval_records if r.get("op") == "search"])
    read_count = len([r for r in retrieval_records if r.get("op") == "read"])
    channels_used = sorted({r.get("channel") for r in retrieval_records if r.get("channel")})
    add(f"- 记录数：{len(retrieval_records)}（search={search_count}, read={read_count}）")
    add(f"- 已用渠道：{', '.join(channels_used) or '无'}")
    for r in retrieval_records:
        add(
            f"- `{r.get('req_id')}` `{r.get('qid')}` {r.get('channel')} / {r.get('op')}："
            f"{_sanitize_text_urls(r.get('query'))}"
        )
    add("")

    add("## 5. 内容审计")
    audit_doc = evidence.get("audit") or {}
    add(f"- 裁决：`{audit_doc.get('verdict') or audit.get('verdict')}`")
    add(f"- 理由：{audit_doc.get('reasoning', '')}")
    for cov in evidence.get("coverage") or []:
        add(f"- `{cov.get('qid')}` {cov.get('status')}：{cov.get('note', '')}")
    gaps = audit_doc.get("open_gaps") or audit.get("open_gaps") or []
    for gap in gaps:
        add(f"- 待补：`{gap.get('qid')}` {gap.get('gap')}；建议渠道：{', '.join(gap.get('suggest_channels') or [])}")
    add("")

    add("## 6. 报告组织")
    add(f"- 报告标题：{outline.get('report_title', '')}")
    add(f"- 核心判断：{outline.get('thesis', '')}")
    for section in outline.get("sections") or []:
        add(f"- `{section.get('sid')}` {section.get('claim')}")
    for item in outline.get("limitations") or []:
        add(f"- 留白：{item.get('gap')} / {item.get('note')}")
    add("")

    add("## 7. 事件日志")
    if audit_log:
        for event in audit_log:
            add(f"- {event.get('ts')} `{event.get('stage')}` `{event.get('event')}`：{event.get('summary')}")
    else:
        add("- 未记录事件日志。")
    add("")
    add("> 这份复盘用于断点接管：可从检索式、渠道选择、证据缺口继续补充，而不必重跑已完成阶段。")
    return "\n".join(lines) + "\n"


def _candidate_soffice_paths():
    paths = []
    env = os.environ.get("SOFFICE_BIN")
    if env:
        paths.append(env)
    found = shutil.which("soffice")
    if found:
        paths.append(found)
    paths.append(str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/bin/soffice"))
    return [p for p in paths if p and os.path.exists(p)]


def _pdf_with_soffice(html_path, pdf_path):
    last_error = ""
    for soffice in _candidate_soffice_paths():
        outdir = os.path.dirname(pdf_path)
        proc = subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", outdir, html_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=90,
        )
        generated = os.path.join(outdir, Path(html_path).with_suffix(".pdf").name)
        if proc.returncode == 0 and os.path.exists(generated):
            if generated != pdf_path:
                os.replace(generated, pdf_path)
            return True, "soffice"
        last_error = (proc.stderr or proc.stdout or "").strip()
    return False, last_error or "soffice unavailable or failed"


def _pdf_with_reportlab(manifest, artifacts, pdf_path):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except Exception as exc:
        return False, "reportlab unavailable: %s" % exc

    font_candidates = [
        os.environ.get("ENTROPY_PDF_FONT"),
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    font_path = next((p for p in font_candidates if p and os.path.exists(p)), None)
    font_name = "Helvetica"
    if font_path:
        pdfmetrics.registerFont(TTFont("EntropyCJK", font_path))
        font_name = "EntropyCJK"
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "BaseCN",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=16,
        spaceAfter=7,
    )
    title = ParagraphStyle(
        "TitleCN",
        parent=base,
        fontSize=20,
        leading=26,
        spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "H2CN",
        parent=base,
        fontSize=14,
        leading=20,
        spaceBefore=10,
        spaceAfter=8,
    )

    outline = artifacts["outline"] or {}
    evidence = artifacts["evidence"] or {}
    evidence_by_id = {item.get("eid"): item for item in evidence.get("evidence", []) if item.get("eid")}
    story = [
        Paragraph(outline.get("report_title") or "信息降熵调研报告", title),
        Paragraph("原始诉求：" + str(manifest.get("original_request", "")), base),
        Paragraph("核心判断：" + str(outline.get("thesis", "")), base),
        Spacer(1, 4 * mm),
    ]
    for section in outline.get("sections") or []:
        story.append(Paragraph(section.get("claim", ""), h2))
        for support in section.get("supports") or []:
            kind = "事实" if support.get("type") == "fact" else "推断"
            story.append(Paragraph("- %s（%s）" % (
                support.get("point", ""),
                kind,
            ), base))
        if section.get("design_implication"):
            story.append(Paragraph("设计启示：" + section.get("design_implication", ""), base))
    if outline.get("limitations"):
        story.append(Paragraph("局限与待补", h2))
        for item in outline.get("limitations") or []:
            story.append(Paragraph("- %s：%s" % (item.get("gap", ""), item.get("note", "")), base))
    if outline.get("scope_fidelity"):
        story.append(Paragraph("方法忠实度：" + outline.get("scope_fidelity", ""), base))
    source_rows = []
    seen = set()
    for section in outline.get("sections") or []:
        for support in section.get("supports") or []:
            for eid in support.get("evidence_refs") or []:
                ev = evidence_by_id.get(eid, {})
                for src in ev.get("sources") or []:
                    key = (src.get("url") or "", src.get("title") or src.get("locus") or "")
                    if key in seen:
                        continue
                    seen.add(key)
                    source_rows.append(src)
    if source_rows:
        story.append(Paragraph("参考来源", h2))
        for idx, src in enumerate(source_rows, 1):
            label = src.get("title") or src.get("locus") or src.get("url") or "未命名来源"
            detail = src.get("source_type") or "来源"
            url = src.get("url") or ""
            story.append(Paragraph("[%d] %s - %s %s" % (idx, label, detail, url), base))

    doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    doc.build(story)
    return True, "reportlab"


def _candidate_python_paths():
    paths = []
    env = os.environ.get("ENTROPY_PYTHON")
    if env:
        paths.append(env)
    paths.append(str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"))
    return [p for p in paths if p and os.path.exists(p)]


def _pdf_with_bundled_python(run_id, root):
    if os.environ.get("ENTROPY_DELIVER_NO_REEXEC"):
        return False, "bundled python re-exec disabled"
    for python_bin in _candidate_python_paths():
        if os.path.realpath(python_bin) == os.path.realpath(sys.executable):
            continue
        env = os.environ.copy()
        env["ENTROPY_DELIVER_NO_REEXEC"] = "1"
        proc = subprocess.run(
            [python_bin, __file__, run_id, "--root", root, "--pdf-only"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=90,
            env=env,
        )
        if proc.returncode == 0:
            return True, "reportlab via %s" % python_bin
    return False, "bundled python reportlab unavailable or failed"


def create_pdf(manifest, artifacts, html_path, pdf_path, run_id=None, root=None):
    ok, method = _pdf_with_soffice(html_path, pdf_path)
    if ok:
        return method
    ok, method = _pdf_with_reportlab(manifest, artifacts, pdf_path)
    if ok:
        return method
    if run_id and root:
        ok, method = _pdf_with_bundled_python(run_id, root)
        if ok:
            return method
    raise RuntimeError(method)


def main():
    parser = argparse.ArgumentParser(prog="deliver")
    parser.add_argument("run_id")
    parser.add_argument("--root", default=".")
    parser.add_argument("--no-advance", action="store_true")
    parser.add_argument("--pdf-only", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    manifest = state_io.load(args.run_id, args.root)
    run_dir = state_io.run_dir(args.run_id, args.root)
    deliver_dir = os.path.join(run_dir, "deliverables")
    os.makedirs(deliver_dir, exist_ok=True)

    artifacts = _load_artifacts(args.run_id, args.root)
    if args.pdf_only:
        pdf_path = os.path.join(deliver_dir, "report.pdf")
        ok, method = _pdf_with_reportlab(manifest, artifacts, pdf_path)
        if not ok:
            raise RuntimeError(method)
        print(json.dumps({"report_pdf": pdf_path, "pdf_method": method}, ensure_ascii=False))
        return

    review_md = build_review(manifest, artifacts)
    review_path = os.path.join(deliver_dir, "review.md")
    _write(review_path, review_md)

    html_path = _artifact_path(args.run_id, "report_html", args.root)
    index_path = os.path.join(deliver_dir, "index.html")
    if not os.path.exists(html_path):
        raise FileNotFoundError("report_html not found: %s" % html_path)
    shutil.copyfile(html_path, index_path)

    pdf_path = os.path.join(deliver_dir, "report.pdf")
    pdf_method = create_pdf(manifest, artifacts, index_path, pdf_path, args.run_id, args.root)

    if not args.no_advance:
        state_io.advance(args.run_id, "deliver", "done", args.root)
        state_io.log_event(
            args.run_id,
            "deliver",
            "stage_done",
            "已生成交付三件套：review.md / report.pdf / index.html（PDF: %s）" % pdf_method,
            root=args.root,
        )

    print(json.dumps({
        "review_md": review_path,
        "report_pdf": pdf_path,
        "index_html": index_path,
        "pdf_method": pdf_method,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
