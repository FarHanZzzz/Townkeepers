# UI system and Nielsen heuristics

The interface uses the visual language of `iub.ac.bd`: brand blue `#2F3391`,
navy `#04062D`, orange `#F7941D` as a single accent, purple `#812990` reserved
for data marks, Geist as the working typeface, flat surfaces and 12px corners.
It is an administrative product, not a marketing site, so the layout is dense
and task-first.

Tokens live at the top of `static/css/app.css`. Components are class-based and
shared by all 40 templates.

## How each heuristic is implemented

| # | Heuristic | Where it lives | What the user sees |
|---|---|---|---|
| 1 | Visibility of system status | `app.css` `.sidebar a[aria-current]`, `.badge`, `.metric`, `button[data-loading]`; `app.js` loading state | Current page is a filled blue pill with an orange bar; counts sit on dashboard tiles; badges combine colour, dot and words; submit buttons show a spinner and disable |
| 2 | Match between system and the real world | `ui.py` `local_dt`, `money`; `status_tone`; template copy | Dates read "26 Nov 2026, 03:58 (Dhaka)", money reads "BDT 1,250.00", statuses use workflow words (Draft, Pending DoSA Approval) rather than codes |
| 3 | User control and freedom | `app.js` dialogs, dirty-form guard; `base.html` dialogs with a Close button; `data-confirm` | Escape closes any dialog; leaving a half-filled form asks first; irreversible actions confirm; sign-out is always visible |
| 4 | Consistency and standards | the whole of `app.css` | One button hierarchy (primary blue, secondary outlined, danger red), one badge set, one table pattern, one empty state, one focus ring |
| 5 | Error prevention | `includes/field.html`, `includes/form.html`, `app.js` double-submit guard | Required fields marked, invalid fields tinted red, submits disabled while in flight, confirmations on destructive actions |
| 6 | Recognition rather than recall | `base.html` top bar, quick jump, `.memo-strip`, breadcrumbs | The page name is always in the top bar; `/` lists every destination by name; related facts (club, template, status, next actor) sit next to the memo instead of in another screen |
| 7 | Flexibility and efficiency | quick jump (`/`), help (`?`), keyboard-visible focus, sticky table headers | Power users never touch the sidebar; everyone else keeps the visual nav |
| 8 | Aesthetic and minimalist design | tokens, spacing scale, `.panel`, `.metric` | One accent colour, no gradients, borders instead of heavy shadows, muted metadata so the primary action wins |
| 9 | Help users recognise, diagnose and recover from errors | `includes/form.html` error summary, `field.html`, `app.css` `.error-summary` | A top summary states how many fields failed and links to each one; the matching field is tinted and receives focus on load |
| 10 | Help and documentation | `base.html` shortcuts dialog; `.help` under fields; `.empty` states | `?` opens a shortcut reference; every empty list says what it is and what to do next |

## Keyboard

| Key | Action |
|---|---|
| `/` | Open quick jump |
| `?` | Open shortcut help |
| `↑` `↓` `Enter` | Move through quick-jump results and open one |
| `Esc` | Close a dialog or the mobile drawer |

## Things that are deliberately not done

- No icon set: the product has 12 destinations and the labels are unambiguous;
  decorative icons would add weight without adding recognition.
- No dark mode yet: the palette is tuned for a light workspace with a dark
  chrome, which matches the institution's own site.
- Colour is never the only signal. Every badge, warning and error carries words.

## Verifying

```powershell
uv run pytest -q
```

`tests/browser/test_memo_journey.py` needs Playwright browsers
(`uv run playwright install chromium`); the rest of the suite does not.
