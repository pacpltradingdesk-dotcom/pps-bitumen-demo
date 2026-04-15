# Hostinger VPS Deployment

One-shot deployment of the PPS Anantam Bitumen Dashboard onto a
Hostinger KVM VPS running Ubuntu.

## Step 1 — Open Hostinger terminal

From your Hostinger dashboard, open your VPS (`srv1209036.hstgr.cloud`)
and click the **Terminal** button at the top right. This gives you a
browser-based root shell on the VPS.

(Or SSH in yourself: `ssh root@82.112.231.3`)

## Step 2 — Paste this ONE command

```bash
curl -sL https://raw.githubusercontent.com/pacpltradingdesk-dotcom/pps-bitumen-demo/main/deploy/hostinger_setup.sh | bash
```

That's it. The script will:

1. Install Python 3.12 / git / nginx / certbot / build tools
2. Clone the dashboard into `/opt/pps-bitumen`
3. Build a Python venv and install all dependencies
4. Write a `secrets.toml` template at `/root/.streamlit/secrets.toml`
5. Register a `pps-bitumen` systemd service (auto-restart, runs 24x7)
6. Configure nginx reverse proxy on port 80
7. Open firewall ports 80/443

Wait ~3-5 minutes. When it finishes, you'll see a "DONE" banner with
the live URL.

## Step 3 — Open the dashboard

```
http://82.112.231.3
```

Login: `admin` / `0000`

## Step 4 — Plug in your real credentials (one-time)

Edit the secrets file:
```bash
nano /root/.streamlit/secrets.toml
```

Uncomment + fill the sections you use (Telegram, Email, WhatsApp, etc.).
Save with `Ctrl+O`, `Enter`, `Ctrl+X`.

Apply:
```bash
systemctl restart pps-bitumen
```

The `cloud_secrets.py` helper inside the app reads this file
automatically — every credential page will now show:

> ✅ loaded from Streamlit Cloud secrets — survives every restart

(Same file path/format works here because Streamlit treats
`~/.streamlit/secrets.toml` the same whether on Cloud or self-hosted.)

## Step 5 (optional) — Custom domain + HTTPS

If you have a domain like `dashboard.ppsanantam.com`:

1. Point the A-record to `82.112.231.3` in your DNS provider
2. Wait 5-10 min for DNS to propagate
3. On the VPS:
   ```bash
   certbot --nginx -d dashboard.ppsanantam.com
   ```

Dashboard will then be live at `https://dashboard.ppsanantam.com` with
free auto-renewing SSL.

## Day-to-day commands

| Task | Command |
|---|---|
| Tail live logs | `journalctl -u pps-bitumen -f` |
| Restart dashboard | `systemctl restart pps-bitumen` |
| Pull latest code from GitHub | `cd /opt/pps-bitumen && git pull && systemctl restart pps-bitumen` |
| Check status | `systemctl status pps-bitumen` |
| Edit secrets | `nano /root/.streamlit/secrets.toml` |
| Check disk | `df -h /` |

## How updates work

Whenever I push a new commit to `main` (like we've been doing all day),
just SSH in and run:

```bash
cd /opt/pps-bitumen && git pull && systemctl restart pps-bitumen
```

DB, contacts, secrets — all stay intact. Only code + UI updates.

If you want auto-deploy on every push, add a cron job:
```bash
(crontab -l 2>/dev/null; echo "*/10 * * * * cd /opt/pps-bitumen && git pull && systemctl restart pps-bitumen >/dev/null 2>&1") | crontab -
```

This checks for updates every 10 min and restarts the service if
anything new. Safe because `git pull` is a no-op when there's nothing
new.
