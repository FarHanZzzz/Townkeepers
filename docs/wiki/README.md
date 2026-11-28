# Wiki Source

This folder contains GitHub Wiki-ready markdown pages for Amader TOWNHALL.

## Publish to GitHub Wiki

GitHub Wiki is a separate git repository (`Townkeepers.wiki.git`). If the wiki is not initialized in GitHub yet, create the first page from the GitHub web UI (Repository → Settings → enable Wiki, then open Wiki → Create the first page). After that, you can push these files:

```powershell
git clone https://github.com/FarHanZzzz/Townkeepers.wiki.git
Copy-Item .\docs\wiki\*.md .\Townkeepers.wiki\ -Force
cd Townkeepers.wiki
git add .
git commit -m "Add Amader TOWNHALL wiki"
git push
```

## Pages

- `Home.md` — wiki landing page
- `Getting-Started.md` — local setup
- `Architecture.md` — system design/command protocol
- `Configuration.md` — env vars/policy/synthetic values
- `Deployment-and-Operations.md` — release/ops/runbook
- `Security-and-Compliance.md` — security controls/checklist
- `Contributing.md` — dev workflow/PR standards
- `FAQ-and-Troubleshooting.md` — common issues
- `_Sidebar.md` / `_Footer.md` — GitHub Wiki navigation/footer