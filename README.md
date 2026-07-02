# HMB Presence Map — Deployment Guide

A Streamlit dashboard with login-gated Admin and Viewer access.

## Logins

- **Admin** (built in, always available): `sudipta` / `sudipta@5566`
- **Viewer accounts**: none exist by default. After you deploy, log in as `sudipta`,
  open the **🛠 Admin** tab → **User Accounts**, and create a username/password
  for each viewer. They'll show up as `viewer` role and won't see the Admin tab.

Accounts are stored in `users.json` on the server (passwords are hashed, never
stored in plain text).

---

## 1. Push this project to GitHub

```bash
cd hmb-dashboard
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## 2. Deploy on Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
2. Select the repo you just pushed.
3. Railway auto-detects Python (via `requirements.txt`) and will use the
   `Procfile` / `railway.json` already included here to run:
   ```
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
   ```
4. Click **Deploy**. Once the build finishes, click **Generate Domain** under
   the service's **Settings → Networking** to get a public URL.

That's it — no environment variables are required to get started.

## 3. Make viewer accounts (and other admin edits) survive redeploys

By default, Railway's filesystem is **ephemeral for each new deploy** — any
file changes made while the app was running (new viewer accounts, custom
columns, edited district data) are written to disk and persist as long as the
container isn't redeployed/rebuilt, but a fresh deploy resets the container
back to what's in the GitHub repo.

To make accounts and edits permanent across redeploys:

1. In your Railway service, go to **Settings → Volumes** → **New Volume**.
2. Mount it at `/app` (or a subfolder, e.g. `/app/data`, if you'd rather keep
   only the data files persistent — in that case update the file paths for
   `USERS_FILE`, `CUSTOM_COLUMNS_FILE`, and `CUSTOM_META_FILE` in `app.py`
   accordingly).
3. Redeploy. From then on, `users.json`, `custom_columns.csv`, and
   `custom_columns_meta.json` will persist across deploys.

Without a volume, everything still works fine during normal use — it only
resets if you push a new commit or manually redeploy.

## 4. Change the admin password later

Log in as `sudipta`, and in a future update you can add a "change password"
option — or, for now, edit `users.json` on the server (via the Railway
volume/shell) and replace the password hash:

```python
import hashlib
hashlib.sha256("new_password_here".encode()).hexdigest()
```

---

## Local development

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files

| File | Purpose |
|---|---|
| `app.py` | Main Streamlit app |
| `requirements.txt` | Python dependencies |
| `Procfile` / `railway.json` | Tells Railway how to start the app |
| `users.json` | Auto-created on first run; stores login accounts |
| `custom_columns.csv` / `custom_columns_meta.json` | Admin-added custom data columns |
| `activedistrict.xlsx`, `india-districts-census-2011.xlsx`, `krm.xlsx` | Source data |
