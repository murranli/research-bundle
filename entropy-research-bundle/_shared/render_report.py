#!/usr/bin/env python3
"""
render_report.py —— report-render 阶段执行层

把 05_outline.json 渲染为自包含的 06_report.html，并按状态契约推进 render。
内容判断仍由 report-compose 完成；本脚本只做结构到 HTML 组件的映射。

CLI:
  python render_report.py <run_id> [--root .] [--no-advance]
"""
import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_io


def _load_json_artifact(run_id, key, root="."):
    text = state_io.read_artifact(run_id, key, root)
    return json.loads(text)


def _esc(value):
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _scope_label(scope):
    names = {"investment": "商业投资", "product": "产品分析", "design": "设计落地"}
    primary = names.get(scope.get("primary"), scope.get("primary") or "未标注")
    serves = names.get(scope.get("serves"), scope.get("serves") or "")
    return primary + ("，服务于" + serves if serves else "")


def _evidence_index(evidence_doc):
    return {item.get("eid"): item for item in evidence_doc.get("evidence", []) if item.get("eid")}


def _collect_sources(outline, evidence_by_id):
    source_index = {}
    sources = []
    support_sources = {}
    for section in outline.get("sections", []):
        for support in section.get("supports", []):
            support_key = id(support)
            support_sources[support_key] = []
            for eid in support.get("evidence_refs") or []:
                ev = evidence_by_id.get(eid, {})
                for src in ev.get("sources") or []:
                    url = src.get("url") or ""
                    title = src.get("title") or src.get("locus") or src.get("req_id") or "未命名来源"
                    key = (url, title)
                    if key not in source_index:
                        source_index[key] = len(sources) + 1
                        sources.append({
                            "num": source_index[key],
                            "title": title,
                            "url": url,
                            "source_type": src.get("source_type") or "来源",
                            "locus": src.get("locus") or "",
                        })
                    support_sources[support_key].append(source_index[key])
    return sources, support_sources


def _source_refs(nums):
    unique = []
    for num in nums or []:
        if num not in unique:
            unique.append(num)
    if not unique:
        return ""
    links = [
        '<a href="#source-%d" title="查看参考来源 %d">[%d]</a>' % (num, num, num)
        for num in unique
    ]
    return '<sup class="cite">%s</sup>' % "".join(links)


def _source_list(sources):
    if not sources:
        return '<p class="muted">本报告未记录可展示的外部来源。</p>'
    items = []
    for src in sources:
        title = _esc(src.get("title"))
        source_type = _esc(src.get("source_type"))
        locus = _esc(src.get("locus"))
        url = src.get("url")
        title_html = f'<a href="{_esc(url)}" target="_blank" rel="noopener">{title}</a>' if url else title
        items.append(
            """
            <li id="source-%d">
              <div><strong>[%d] %s</strong></div>
              <div class="muted">%s%s</div>
            </li>
            """
            % (
                src["num"],
                src["num"],
                title_html,
                source_type,
                (" · " + locus) if locus else "",
            )
        )
    return '<ol class="source-list">%s</ol>' % "\n".join(items)


def render_html(manifest, outline, evidence_doc):
    evidence_by_id = _evidence_index(evidence_doc or {})
    scope = manifest.get("scope") or {}
    title = outline.get("report_title") or "信息降熵调研报告"
    thesis = outline.get("thesis") or ""
    original_request = manifest.get("original_request") or ""
    report_sources, support_sources = _collect_sources(outline, evidence_by_id)

    section_html = []
    for idx, section in enumerate(outline.get("sections", []), 1):
        supports = []
        for support in section.get("supports", []):
            support_type = support.get("type") or "fact"
            source_refs = _source_refs(support_sources.get(id(support), []))
            supports.append(
                """
                <li>
                  <div class="support-main">
                    <span class="tag tag-%s">%s</span>
                    <span class="support-text">%s%s</span>
                  </div>
                </li>
                """
                % (
                    _esc(support_type),
                    _esc("事实" if support_type == "fact" else "推断"),
                    _esc(support.get("point")),
                    source_refs,
                )
            )
        implication = section.get("design_implication") or ""
        section_html.append(
            """
            <section class="report-section">
              <div class="section-kicker">观点 %02d</div>
              <h2>%s</h2>
              <ul class="support-list">%s</ul>
              %s
            </section>
            """
            % (
                idx,
                _esc(section.get("claim")),
                "\n".join(supports),
                (
                    '<div class="implication"><strong>设计启示</strong><p>%s</p></div>' % _esc(implication)
                    if implication
                    else ""
                ),
            )
        )

    limitations = []
    for item in outline.get("limitations", []):
        limitations.append(
            """
            <li>
              <strong>%s</strong>
              <p>%s</p>
            </li>
            """
            % (
                _esc(item.get("gap")),
                _esc(item.get("note")),
            )
        )

    css = """
    :root {
      --bg: #f7f5ef;
      --paper: #fffdf8;
      --ink: #1f2428;
      --muted: #687077;
      --line: #ded8cb;
      --brand: #245f73;
      --accent: #b2563b;
      --fact: #e9f3ef;
      --infer: #f6eadf;
      --gap: #fff3c9;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      line-height: 1.65;
    }
    main { width: min(980px, calc(100vw - 32px)); margin: 0 auto; padding: 48px 0 64px; }
    header { border-bottom: 1px solid var(--line); padding-bottom: 28px; margin-bottom: 28px; }
    h1 { font-size: clamp(30px, 4vw, 48px); line-height: 1.14; margin: 12px 0 16px; letter-spacing: 0; }
    h2 { font-size: 25px; line-height: 1.35; margin: 6px 0 18px; letter-spacing: 0; }
    h3 { margin-top: 28px; }
    p { margin: 0 0 12px; }
    .meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
    .pill, .tag, .source {
      border: 1px solid var(--line);
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 3px 10px;
      font-size: 13px;
      text-decoration: none;
      color: var(--ink);
      background: rgba(255,255,255,.56);
    }
    .source { margin: 4px 6px 0 0; }
    .tag-fact { background: var(--fact); border-color: #bfd8cc; }
    .tag-inference { background: var(--infer); border-color: #e0c2a9; }
    .tag-confidence { background: #eef0f1; }
    .cite {
      font-size: 12px;
      line-height: 0;
      margin-left: 3px;
      white-space: nowrap;
      vertical-align: super;
    }
    .cite a {
      color: var(--brand);
      text-decoration: none;
      font-weight: 700;
    }
    .cite a:hover { text-decoration: underline; }
    .thesis {
      background: var(--paper);
      border-left: 5px solid var(--brand);
      padding: 18px 20px;
      margin: 18px 0 0;
      font-size: 18px;
    }
    .report-section, .limitations, .method, .references {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 24px;
      margin: 18px 0;
    }
    .section-kicker { color: var(--brand); font-size: 13px; font-weight: 700; }
    .support-list { list-style: none; padding: 0; margin: 0; }
    .support-list li { border-top: 1px solid var(--line); padding: 14px 0; }
    .support-list li:first-child { border-top: 0; }
    .support-main { display: flex; flex-wrap: wrap; gap: 8px; align-items: flex-start; }
    .support-text { flex: 1 1 420px; min-width: 0; }
    .sources { margin-top: 8px; }
    .implication {
      background: #edf4f6;
      border: 1px solid #c7dde4;
      border-radius: 8px;
      margin-top: 16px;
      padding: 14px 16px;
    }
    .limitations { background: var(--gap); border-color: #e1ca7b; }
    .limitations ul { margin: 0; padding-left: 20px; }
    .source-list { margin: 0; padding-left: 20px; }
    .source-list li { margin: 10px 0; }
    .muted { color: var(--muted); }
    footer { color: var(--muted); margin-top: 28px; font-size: 13px; }
    @media print {
      body { background: white; }
      main { width: 100%; padding: 16px 18px; }
      .report-section, .limitations, .method, .thesis { break-inside: avoid; }
    }
    """

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)}</title>
  <style>{css}</style>
</head>
<body>
  <main>
    <header>
      <div class="meta">
        <span class="pill">类型：{_esc(outline.get("report_type"))}</span>
        <span class="pill">范围：{_esc(_scope_label(scope))}</span>
      </div>
      <h1>{_esc(title)}</h1>
      <p class="muted">原始诉求：{_esc(original_request)}</p>
      <div class="thesis"><strong>核心判断</strong><p>{_esc(thesis)}</p></div>
    </header>
    {''.join(section_html)}
    <section class="limitations">
      <h2>局限与待补</h2>
      <ul>{''.join(limitations) if limitations else '<li>本轮未记录显式证据缺口。</li>'}</ul>
    </section>
    <section class="method">
      <h2>方法与忠实度</h2>
      <p>{_esc(outline.get("scope_fidelity"))}</p>
      <p class="muted">事实与推断已用不同标签标记；证据出处统一列在文末，便于独立阅读与核验。</p>
    </section>
    <section class="references">
      <h2>参考来源</h2>
      {_source_list(report_sources)}
    </section>
    <footer>Generated by research v2.0</footer>
  </main>
</body>
</html>
"""
    return html_doc


def main():
    parser = argparse.ArgumentParser(prog="render_report")
    parser.add_argument("run_id")
    parser.add_argument("--root", default=".")
    parser.add_argument("--no-advance", action="store_true")
    args = parser.parse_args()

    manifest = state_io.load(args.run_id, args.root)
    outline = _load_json_artifact(args.run_id, "outline", args.root)
    try:
        evidence = _load_json_artifact(args.run_id, "evidence", args.root)
    except Exception:
        evidence = {"evidence": []}

    html_doc = render_html(manifest, outline, evidence)
    path = state_io.write_artifact(args.run_id, "report_html", html_doc, args.root)

    if not args.no_advance:
        state_io.advance(args.run_id, "render", "done", args.root)
        state_io.log_event(
            args.run_id,
            "render",
            "stage_done",
            "已渲染 HTML 报告：%s" % os.path.basename(path),
            root=args.root,
        )

    print(path)


if __name__ == "__main__":
    main()
