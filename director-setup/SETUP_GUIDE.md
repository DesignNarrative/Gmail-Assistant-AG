# Director's PC — Setup Guide

Everything runs locally on the director's PC at `http://localhost:8000`.
No cloud, no deployment. Confidential emails never leave his machine
(only AI questions go to Groq, and Gmail sync talks to Google).

---

## Step 0 — Before you go to his PC (do these on YOUR side)

1. **Google Cloud Console** → APIs & Services → OAuth consent screen →
   **Test users → + Add users** → add `gkankariya@gmail.com` → Save.
   *Without this, Connect Gmail fails with "Error 403: access_denied".*
2. Copy the whole project folder to a USB drive — **exclude** these folders:
   `backend\venv`, `frontend\node_modules`, `backend\uploads`, `backend\logs`.
   (`frontend\dist` MUST be included — it's the ready-built app, so Node.js
   is not needed on his PC.)

## Step 1 — Install these programs on the director's PC

| Program | Where | Notes |
|---|---|---|
| Python 3.10 or 3.11 | python.org | Tick **"Add python.exe to PATH"** |
| PostgreSQL 16 | enterprisedb.com | Remember the password you choose. Add `C:\Program Files\PostgreSQL\16\bin` to PATH |
| pgvector extension | github.com/pgvector/pgvector (Windows: install via the released `.zip` for PG16, copy files into the PostgreSQL folders as per its README) | Needed for AI memory |
| Tesseract OCR 5.x | github.com/UB-Mannheim/tesseract/wiki | For reading scanned files |
| Poppler for Windows | github.com/oschwartz10612/poppler-windows/releases | Unzip, add its `bin` folder to PATH |

Redis/Memurai is **optional** — the app runs fine without it in single-process mode.

## Step 2 — Copy the project folder onto his PC

For example to `C:\Gmail-Assistant-AG`.

## Step 3 — Run the installer (once)

Double-click **`director-setup\INSTALL_ON_DIRECTOR_PC.bat`**.
It checks the programs above, asks for the PostgreSQL password,
creates the database, writes `backend\.env`, installs Python packages
(10–20 min, needs internet) and creates the tables.

## Step 4 — Start the app

Double-click **`START_PROJECT.bat`** (project root). The browser opens
`http://localhost:8000` automatically.

- **First time:** click **Sign up** → enter his name, `gkankariya@gmail.com`
  and a password of his own choice (nobody else needs to know it).
  Forgot it later? The **Forgot password?** link on the sign-in page
  lets him set a new one.
- **Every day after:** just **Sign in** with his email + password
- Click **Connect Gmail** → sign in as `gkankariya@gmail.com` → allow access
- In Gmail, create the label **"Director's AI Assistant"** and apply it to
  the emails the assistant should learn
- In the app, click **Update emails** — then ask anything in AI Chat

## Daily use

- Start: `START_PROJECT.bat` · Stop: `STOP_PROJECT.bat`
- First "Update emails" run also downloads small AI models (one time, internet needed)

## Known limits

- **Every ~7 days** Google disconnects the Gmail link (the app is in Google's
  "Testing" mode) — the director just clicks **Connect Gmail** again.
- Internet is required for answering questions (Groq AI) and syncing emails.

## If something goes wrong

| Problem | Fix |
|---|---|
| "Error 403: access_denied" on Connect Gmail | His email isn't added as a Google test user (Step 0.1) |
| Login says email not allowed | Email must be in `ALLOWED_REGISTRATION_EMAILS` in `backend\.env` |
| Installer fails on pgvector | pgvector wasn't installed into PostgreSQL (Step 1) |
| Scanned PDFs/images not readable | Tesseract or Poppler missing from PATH (Step 1) |
| Port 8000 already in use | Close the other program or restart the PC |
