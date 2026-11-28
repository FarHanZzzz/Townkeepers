"""Map Lighthouse audit results to Nielsen's 10 usability heuristics.

Usage:
  python scripts/nielsen/lighthouse_to_nielsen.py <lighthouse.json> [output.md]

This provides an automated proxy for some Nielsen heuristics; manual review is still required.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

HEURISTICS = {
    "H1 Visibility of system status": ["first-contentful-paint", "interactive", "speed-index", "server-response-time", "redirects", "bootup-time", "mainthread-work-breakdown"],
    "H2 Match between system and real world": ["label", "link-name", "document-title", "meta-description", "hreflang", "canonical"],
    "H3 User control and freedom": ["bypass", "no-document-write", "external-anchors-use-rel-noopener"],
    "H4 Consistency and standards": ["doctype", "html-has-lang", "valid-lang", "meta-viewport", "font-size", "tap-targets"],
    "H5 Error prevention": ["errors-in-console", "image-size-responsive", "password-inputs-can-be-pasted-into", "valid-source-maps", "js-libraries"],
    "H6 Recognition rather than recall": ["label", "image-alt", "input-image-alt", "link-name", "button-name", "heading-order"],
    "H7 Flexibility and efficiency of use": ["viewport", "tap-targets", "uses-responsive-images", "font-size", "interactive"],
    "H8 Aesthetic and minimalist design": ["unused-css-rules", "unused-javascript", "dom-size", "render-blocking-resources", "cumulative-layout-shift"],
    "H9 Help users recognize, diagnose, and recover from errors": ["errors-in-console", "server-response-time", "http-status-code", "console-time-usage"],
    "H10 Help and documentation": ["document-title", "meta-description", "link-text", "crawlable-anchors"],
}

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/nielsen/lighthouse_to_nielsen.py <lighthouse.json> [output.md]")
        sys.exit(1)
    data = load(sys.argv[1])
    audits = data.get("audits", {})
    cats = data.get("categories", {})
    url = data.get("finalDisplayedUrl") or data.get("requestedUrl") or "unknown"
    out = sys.argv[2] if len(sys.argv) > 2 else None

    lines = []
    lines.append("# Nielsen Heuristics Audit (Lighthouse Proxy)")
    lines.append("")
    lines.append(f"- **URL:** {url}")
    lines.append(f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- **Source:** `{os.path.basename(sys.argv[1])}`")
    lines.append(
        "- **Note:** Automated Lighthouse mapping is a proxy. "
        "Nielsen heuristics still require manual expert review."
    )
    lines.append("")
    lines.append("## Lighthouse category scores")
    for k, v in cats.items():
        score = v.get('score')
        pct = f"{score*100:.0f}%" if isinstance(score, (int,float)) else "N/A"
        lines.append(f"- **{v.get('title',k)}:** {pct}")
    lines.append("")

    for h, keys in HEURISTICS.items():
        lines.append(f"## {h}")
        found = []
        for k in keys:
            a = audits.get(k)
            if not a:
                continue
            score = a.get('score')
            if score is None:
                continue
            if score < 1:
                found.append((k, a.get('title',k), score, a.get('displayValue','')))
        if not found:
            lines.append(
                "- No failing/flagged automated checks mapped to this heuristic "
                "(manual review still recommended)."
            )
        else:
            for k, title, score, dv in found:
                pct = f"{score*100:.0f}%"
                extra = f" ({dv})" if dv else ""
                lines.append(f"- **{title}** [{k}] — score {pct}{extra}")
        lines.append("")

    lines.append("## Manual review checklist")
    lines.append("Use `docs/nielsen/nielsen-heuristics-checklist.md` for qualitative evaluation.")
    report = "\n".join(lines)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(report)
        print(out)
    else:
        print(report)

if __name__ == "__main__":
    main()
