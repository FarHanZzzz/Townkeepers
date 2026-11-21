# Feature analysis 3 — Weaknesses and fixes

Date: 22 Nov 2026  
Scope: Amader TOWNHALL after Increments 1–6 first slices (memo, booking, finance forms, publishing, CSV import, handover, reports).  
Tests at analysis: 129 passing. Coverage ~82% of apps / assistance / config.

This note is a critique of product depth, technical craft, and UI. It is not a replacement for `IMPLEMENTATION_CONTEXT.md` or the PRD.

---

## 1. Verdict in one paragraph

The **domain spine is real engineering**: command protocol, access ceilings, immutable memo versions, content-hash signatures, one decision per stage, and PostgreSQL GiST exclusion on reservations. The **product surface is uneven and generic**: later modules are thin checklist slices, and the UI reads as a shadcn / Geist SaaS admin, not an IUB club office. Pride belongs to the workflow engine; pride does not yet belong to the look or the finished breadth.

---

## 2. What is strong (keep)

| Area | Why it is not generic |
|---|---|
| Command protocol (`platform_core/protocol.py`) | Atomic writes, operation keys, replay vs conflict, receipt rollback on domain failure |
| Access engine (`platform_core/access.py`) | Category ceilings, dated assignments, recheck inside the transaction |
| Memo lifecycle | Freeze version → Advisor → optional signers → Head; rejection opens a linked revision; no rewrite of history |
| E-signature | Bound to version content hash; canvas or typed name; digest stored |
| Booking concurrency | Active reservations blocked by exclusion constraint; failed move keeps the original hold |
| Finance language (model level) | Requested / allocated / scheduled / confirmed / verified are separate ideas (BR-05) |
| Test posture | Race tests, requirement markers, Playwright journey, fake provider at the adapter boundary |

Do not “simplify” these into ordinary CRUD. Fixes should sit on top of this spine, not replace it.

---

## 3. Weaknesses and fixes

### W1 — UI looks like a starter-kit dashboard

**Weakness.** Neutral tokens, Geist, metric tiles, and the same white card on every page. First viewport feels like any SaaS “Workspace,” not an institutional memo and money system. Removing the nav would leave a brand that could belong to another product.

**Evidence.** `static/css/app.css` (shadcn-neutral palette, board/metrics patterns); role dashboard metric strip; identical card chrome on Finance, Events, Memos, Publishing.

**Fix.**

1. Drop the big metric strip from the primary work surface. Replace with one **work queue**: club code, memo/event reference, deadline, who acts next.
2. Treat memos and finance like **registry and ledger**: denser tables, text status, clear primary action per row. Fewer identical bordered cards.
3. Put **club + term** in the shell on every signed-in page so context is always visible.
4. One visual direction that is institutional (paper, stamp, queue), not purple/indigo SaaS and not cream-serif “AI default” either. Keep accessibility (labels, errors, keyboard) while changing chrome.
5. Brand test: first viewport must still say Amader TOWNHALL / IUB club work after the nav is ignored.

**Priority.** High for pride. Does not require new domain models.

---

### W2 — Feature depth is uneven

**Weakness.** Eight named features exist; one spine carries most of the weight. Memo → event → booking is deep. Finance UI, publishing, AI assistance, and analytics are thinner: forms and models that pass acceptance slices more than a finished club office.

**Evidence.**

| Feature | Depth today | Gap |
|---|---|---|
| Access / clubs / terms | Strong | Demo permission sharing blurs the story (see W4) |
| Memo workflow | Strong | Queue UX still card-heavy; calendar/priority polish |
| Event + booking | Medium–strong | Calendar screens incomplete; live venue figures synthetic; two-connection race called out as still open in older context notes |
| Finance | Thin–medium | Page is a stack of forms; reconciliation exists but does not feel like an office ledger |
| Publishing | Thin | Internal notices work; external send fails until URL set; no real club site |
| Assistance / OCR | Thin | Fake provider; reading stays unverified (correct) but UI does not teach that clearly |
| Analytics / history | Thin | CSV import with provenance; compare/drill-down not a finished report desk |
| Handover | First slice | Exists as command path; not a memorable EB experience |

**Fix.**

1. Stop spreading effort across all eight modules in parallel.
2. Finish **one excellent journey**: draft memo → Advisor → Head → book venue → internal notice → one finance release/expense → see status on the event page.
3. For each side module, either deepen to office quality or mark it explicitly as **advisory / demo-only** in the UI and in `IMPLEMENTATION_CONTEXT.md`.
4. Prefer depth on the spine over polishing every side path.

**Priority.** High for product honesty.

---

### W3 — Screens are odd and overloaded

**Weakness.** Event detail is a long scroll of action blocks. Finance is sequential forms. Memo list mixes queue, filter card, and bare table. Actions look available when the persona demo grants them, so the UI does not teach institutional limits.

**Fix.**

1. **Event page:** one status band (memo / booking / notice / finance), then only the **next permitted action**, with history below.
2. **Finance page:** ledger table first (allocations, releases, expenses); forms behind “Record …” actions, not all open at once.
3. **Memo list:** one queue table; filters as lightweight controls, not a second card composition.
4. Hide or disable actions the **real** category ceiling would deny; keep demo sharing for walkthroughs but show a “demo powers” banner when D-20 unions are active.
5. Move booking form only when booking is confirmed (already intended); apply the same “state-gated forms” rule everywhere.

**Priority.** High for “everything looks odd.”

---

### W4 — Demo access vs real authorization story

**Weakness.** D-20: demo Admin / DoSA / Advisor / five presidents share permission-giving so the picker walkthrough works. Real profiles stay on category ceilings. Reviewers who only click demos learn the wrong permission model. Buttons driven by `can_*` can look like “everyone can do everything.”

**Fix.**

1. Keep D-20 for the demo picker, but label the session: **Demonstration powers — not production ceilings.**
2. Add a second demo mode (or seed path) that uses **strict ceilings** for assessment demos.
3. Never let a template alone establish permission; keep recheck inside commands (already true — do not regress).
4. Document in ASSESSMENT evidence which walkthrough used shared powers vs strict ceilings.

**Priority.** Medium for integrity; high for assessment honesty.

---

### W5 — Synthetic institutional values look like product truth

**Weakness.** Venues, capacities, lead times, and external publish destination are synthetic or unset (D-22, D-23, D-25). If the UI does not mark them, the app pretends official IUB figures exist.

**Fix.**

1. Label every synthetic venue and policy value in the UI (`Synthetic — not official IUB`).
2. Keep `is_synthetic` (or equivalent) on catalogue rows; surface it in templates and exports.
3. External publish: keep fail-until-configured; show destination status on the event/publishing screen.
4. Do not invent official lead times, domains, or capacities; route to PRD Appendix C owners.

**Priority.** Medium. Already partly decided; UI labeling is the missing piece.

---

### W6 — Documentation drift

**Weakness.** Handover / implementation notes still talk in places as if publishing apps were empty shells or booking race work was only planned, while code and tests already exist. That makes the project feel less deliberate than it is.

**Evidence.** `IMPLEMENTATION_CONTEXT.md` section 3 still lists `publishing` / `analytics` as empty shells in one map row while section 1 and later increments describe working slices. “Last updated” blurb can lag the finance/move/receipt/CSV work.

**Fix.**

1. Reconcile the repository map, command list, and “next increment” with the actual apps and 129-test suite.
2. Update the traceability table for FR/UC/AC touched by Increments 3–6.
3. Add a short “known thin slices” list so reviewers do not confuse checklist coverage with finished features.
4. Keep this file (`featureanalysis3.md`) linked from the handover reading order until the UI redesign closes W1–W3.

**Priority.** Medium. Cheap; improves trust.

---

### W7 — Finance feels like forms, not a ledger

**Weakness.** Domain language is good; the page does not teach BR-05. Users see inputs before they see balances and evidence.

**Fix.**

1. Top of Finance: period, opening figures, allocated / released / verified / remaining, with the worked fixture (2750 / 1250 / -150) as the regression story.
2. Chronological ledger of immutable rows; corrections as linked adjustments only.
3. Receipt upload → show **unverified reading** distinctly from **verified expense**; human verify remains the decision.
4. One conversion record UI when currencies differ; never silent mix.

**Priority.** Medium after the memo/booking spine UI.

---

### W8 — Publishing and assistance feel bolted on

**Weakness.** Internal notice path works; external path is correctly pessimistic but visually unfinished. OCR is fake and easy to misread as “AI magic.”

**Fix.**

1. Publishing screen: Internal | External | Delivery status (queued / sent / failed / timeout).
2. On fail: reason in plain language (“No club website configured”).
3. Assistance: always label suggestions and receipt readings as **advisory**; preserve manual entry and human verify.
4. Do not enable live providers by default with production data.

**Priority.** Lower than spine UI; required before claiming Increment 5–6 “done.”

---

### W9 — Analytics / history is import-first, report-second

**Weakness.** CSV import with provenance and draft exclusion is a solid slice; compare views and drill-downs are not a finished report desk.

**Fix.**

1. After import: show provenance (file, time, actor) and reject-whole-file behavior in the UI message.
2. Completed counts must exclude drafts (already in logic — make it visible in the report copy).
3. Defer heavy BI; ship one honest term comparison table with frozen filters and revision basis (NFR-AUD-01).

**Priority.** Lower.

---

### W10 — Ops and release gates incomplete for pride

**Weakness.** CI workflow exists but has not run on a pushed GitHub remote. Live OCR, official venues, and external site are intentionally unconnected. Without a green remote CI and a strict-ceiling demo, the project looks local-only.

**Fix.**

1. Push and confirm `.github/workflows/ci.yml` green on PostgreSQL 17.
2. Keep production rejecting `DEMO_AUTH` (`townhall.E001`).
3. Record restore/load and `check --deploy` evidence in `ASSESSMENT.md`.
4. Separate “course demo” from “production readiness” in the Wiki / assessment.

**Priority.** Medium for course evidence; not the UI oddness root cause.

---

## 4. Technicality — where pride is fair vs unfair

| Claim | Fair? | Note |
|---|---|---|
| “We built a real approval and booking system with concurrency control” | Yes | Protocol + GiST + memo immutability |
| “We have eight finished product features” | No | Spine deep; sides thin |
| “The UI is a distinctive IUB product” | No | Generic admin chrome |
| “Authorization is role-based like most apps” | Misleading | Real model is ceilings + grants + dated assignments; demo unions hide that |
| “AI runs the club office” | No | Assistance is advisory / fake; keep it that way until a real provider and policy exist |

---

## 5. Recommended fix order

Do these in order. Do not open a parallel redesign of every module.

| Step | Target weakness | Outcome |
|---|---|---|
| 1 | W6 | Docs match code; thin slices named honestly |
| 2 | W1 + W3 | Shell, memo queue, event page — institutional, not SaaS metrics |
| 3 | W5 + W4 | Synthetic labels + demo-powers banner / strict demo path |
| 4 | W7 | Finance as ledger-first |
| 5 | W8 + W9 | Publishing status clarity; one honest report surface |
| 6 | W10 | Remote CI green + assessment evidence |

Success test for pride: a stranger opens the memo queue and event page and understands **who acts next**, **which version was approved**, and **which figure is verified** — without mistaking the app for a generic dashboard template.

---

## 6. Out of scope for this analysis

- Inventing official IUB venue capacities, lead times, or Domains
- Enabling live OCR or a real club website by default
- Rewriting the PRD
- Replacing the command protocol or access engine with a simpler framework

---

## 7. Related documents

- [`IMPLEMENTATION_CONTEXT.md`](IMPLEMENTATION_CONTEXT.md) — current state and decisions (D-19–D-25)
- [`../AGENTS.md`](../AGENTS.md) — coding practice
- [`../GRAND_PRD.md`](../GRAND_PRD.md) — product behavior
- [`../TECHNICAL_REQUIREMENTS.md`](../TECHNICAL_REQUIREMENTS.md) — architecture and verification
- [`../ASSESSMENT.md`](../ASSESSMENT.md) — evidence collected
