# pps-chat-wa — isolated WhatsApp link service (dashboard Client Chat)

Per-user WhatsApp linking for the bitumen dashboard's **Client Chat**, kept
**completely separate** from the bulk `whatsapp-server` (`/opt/whatsapp-dashboard`).
Own dir, own pm2 app, own port (`127.0.0.1:8530`), own `.sessions/`, own `node_modules`.

## What it does
- Each dashboard user links their own WhatsApp via QR.
- Inbound 1:1 customer messages → appended to `/opt/pps-bitumen/wa_inbound.jsonl`
  (the dashboard drains it into `chat_messages`).
- Approved replies are sent from that user's linked number.

## API (localhost + `x-token` header only)
| Method | Path | Body / Query | Returns |
|--------|------|--------------|---------|
| GET  | `/health` | — | `{ok, users}` |
| GET  | `/status` | `?user=` | `{status, number, qr}` |
| POST | `/link/start` | `{user}` | `{status, qr?, number?}` |
| POST | `/unlink` | `{user}` | `{status:'idle'}` |
| POST | `/send` | `{user, phone, text}` | `{ok, number}` |

`status`: `idle | init | qr | authenticated | connected | disconnected | auth_failure | error`.

## Deploy (manual — NOT part of the dashboard auto-deploy)
```bash
# on the VPS, as root
mkdir -p /opt/pps-chat-wa && cd /opt/pps-chat-wa
# copy server.js, package.json, ecosystem.config.js here
openssl rand -hex 24 > .token            # shared secret (dashboard reads this same file)
npm install --omit=dev
pm2 start ecosystem.config.js && pm2 save
curl -s -H "x-token: $(cat .token)" http://127.0.0.1:8530/health
```
The dashboard reads the token from `/opt/pps-chat-wa/.token` automatically
(`whatsapp_bridge.py`). Both run on the same VPS, so localhost works.

## Resource note
Each linked user = one headless Chrome (~200–250 MB). On the shared 8 GB box keep
the number of simultaneously-linked users small (start with 1–2). Sessions persist
across restarts (LocalAuth), and `autoInit()` re-links them without a new QR.

## Isolation
Never imports, edits, or restarts the bulk `whatsapp-server`. The only shared
files are the dashboard's own `/opt/pps-bitumen/wa_inbound.jsonl` (+ pos).
