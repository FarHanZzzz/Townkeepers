# Nielsen Heuristics UI Audit (Integrated Tooling)

This folder integrates automated and manual tools for evaluating the UI against **Nielsen's 10 Usability Heuristics**.

## Tools/plugins integrated

1. **Lighthouse (browser tool)** — automated audit for accessibility, best practices, and SEO. Available via OpenCode browser tools: `tools.browser.lighthouse({ tabID })`. Produces JSON + HTML reports.
2. **Lighthouse-to-Nielsen mapper** — `scripts/nielsen/lighthouse_to_nielsen.py` maps Lighthouse audit failures to Nielsen heuristics and generates a Markdown report.
3. **Manual Nielsen checklist** — `nielsen-heuristics-checklist.md` for qualitative expert review (the part automation cannot fully cover).

## How to run

1. Open the target page in the OpenCode in-app browser and run Lighthouse:
   - `tools.browser.lighthouse({ tabID })`
2. Copy/export the resulting `lighthouse.json`.
3. Generate a Nielsen-mapped report:

```powershell
& ".venv\Scripts\python.exe" scripts/nielsen/lighthouse_to_nielsen.py docs/nielsen/dashboard.lighthouse.json docs/nielsen/dashboard-nielsen-report.md
```

4. Complete the manual checklist in `nielsen-heuristics-checklist.md` and attach screenshots/severity ratings.

## Current artifacts

- `dashboard.lighthouse.json` / `dashboard.lighthouse.html` — Lighthouse audit for Dashboard (DoSA Head).
- `dashboard-nielsen-report.md` — automated Nielsen-mapped report generated from the dashboard audit.
- `nielsen-heuristics-checklist.md` — manual 10-heuristics checklist.

## Notes

- Automated audits are **proxies** only; Nielsen heuristic evaluation requires human judgment.
- Lighthouse accessibility/best-practices issues often map to heuristics 1, 4, 5, 6, 8, and 9.
