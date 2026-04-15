#!/usr/bin/env bash
# =============================================================================
# PPS Anantam — Bitumen Dashboard · Hostinger VPS One-Shot Deployer
# =============================================================================
# Tested on: Ubuntu 24.04 LTS (KVM VPS)
#
# USAGE (paste into Hostinger VPS Terminal as root):
#   curl -sL https://raw.githubusercontent.com/pacpltradingdesk-dotcom/pps-bitumen-demo/main/deploy/hostinger_setup.sh | bash
#
# What this does:
#   1. Installs Python 3.12, git, nginx, certbot, build tools
#   2. Clones the dashboard repo into /opt/pps-bitumen
#   3. Creates a venv and installs all Python dependencies
#   4. Writes a Streamlit secrets template at ~/.streamlit/secrets.toml
#   5. Registers a systemd service that runs Streamlit on :8501 24x7
#   6. Configures nginx as reverse proxy on :80 (and :443 if domain set)
#   7. Opens UFW ports 80/443
#
# After this completes, dashboard will be live at:
#   http://82.112.231.3  (or your custom domain if you set DOMAIN below)
#
# To make it HTTPS with a custom domain:
#   export DOMAIN="dashboard.yourdomain.com"
#   Then point A-record at 82.112.231.3, and run:
#     certbot --nginx -d $DOMAIN
# =============================================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/pacpltradingdesk-dotcom/pps-bitumen-demo.git"
APP_DIR="/opt/pps-bitumen"
APP_USER="root"                       # change if you create a dedicated user
SVC_NAME="pps-bitumen"
PORT="8501"
DOMAIN="${DOMAIN:-}"                  # set externally to enable SSL
VPS_IP="$(curl -s https://api.ipify.org || hostname -I | awk '{print $1}')"

log()  { echo -e "\n\033[1;36m=== $* ===\033[0m"; }
warn() { echo -e "\033[1;33m[warn] $*\033[0m"; }
die()  { echo -e "\033[1;31m[fail] $*\033[0m" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root. In Hostinger Terminal you already are."

# ── 1. System packages ───────────────────────────────────────────────────────
log "Updating apt + installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
    python3 python3-venv python3-pip python3-dev \
    git curl build-essential \
    nginx certbot python3-certbot-nginx \
    ufw \
    libffi-dev libssl-dev \
    sqlite3

# ── 2. Clone or update repo ──────────────────────────────────────────────────
if [[ -d "$APP_DIR/.git" ]]; then
    log "Repo already present — pulling latest"
    cd "$APP_DIR"
    git fetch --all --prune
    git reset --hard origin/main
else
    log "Cloning repo into $APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# ── 3. Python venv + deps ────────────────────────────────────────────────────
log "Building Python venv"
if [[ ! -d "$APP_DIR/.venv" ]]; then
    python3 -m venv "$APP_DIR/.venv"
fi
# shellcheck disable=SC1091
source "$APP_DIR/.venv/bin/activate"
pip install --upgrade pip wheel setuptools
pip install -r "$APP_DIR/requirements.txt"
deactivate

# ── 4. Streamlit config + secrets template ───────────────────────────────────
log "Writing Streamlit config + secrets template"
mkdir -p /root/.streamlit
cat > /root/.streamlit/config.toml <<'EOF'
[server]
port = 8501
address = "127.0.0.1"
headless = true
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 50

[browser]
gatherUsageStats = false

[theme]
base = "light"
primaryColor = "#4F46E5"
EOF

SECRETS_FILE="/root/.streamlit/secrets.toml"
if [[ ! -f "$SECRETS_FILE" ]]; then
    cat > "$SECRETS_FILE" <<'EOF'
# =============================================================================
# PPS Anantam — Credential secrets
# Edit this file with: nano /root/.streamlit/secrets.toml
# Uncomment + fill the sections you actually use. Leave others empty.
# After editing, restart service: systemctl restart pps-bitumen
# =============================================================================

# auth_secret = "paste a random long string here to stabilize session tokens"

# [telegram]
# api_id = "12345678"
# api_hash = "your_hash_from_my_telegram_org"
# phone = "+919876543210"

# [email]
# smtp_host = "smtp.gmail.com"
# smtp_port = 587
# username = "your@email.com"
# password = "your_app_password"
# from_name = "PPS Anantam"
# from_email = "your@email.com"

# [whatsapp]
# api_key = "your_360dialog_api_key"
# phone_number_id = "your_phone_number_id"
# business_name = "PPS Anantam"

# [news]
# newsapi_key = "..."
# gnews_key = "..."

# [api_keys]
# api_key_eia = "..."
# api_key_fred = "..."
# api_key_data_gov_in = "..."
# api_key_openweather = "..."

# [ai]
# openai = "sk-..."
# anthropic = "sk-ant-..."
EOF
    chmod 600 "$SECRETS_FILE"
    warn "Template secrets.toml written to $SECRETS_FILE — fill it in + systemctl restart $SVC_NAME"
else
    log "secrets.toml already present — leaving it alone"
fi

# ── 5. systemd service ───────────────────────────────────────────────────────
log "Installing systemd service"
cat > "/etc/systemd/system/${SVC_NAME}.service" <<EOF
[Unit]
Description=PPS Anantam Bitumen Dashboard (Streamlit)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/.venv/bin:/usr/bin:/usr/local/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="HOME=/root"
ExecStart=${APP_DIR}/.venv/bin/streamlit run dashboard.py \\
    --server.port=${PORT} \\
    --server.address=127.0.0.1 \\
    --server.headless=true \\
    --browser.gatherUsageStats=false
Restart=always
RestartSec=10
StandardOutput=append:/var/log/${SVC_NAME}.log
StandardError=append:/var/log/${SVC_NAME}.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SVC_NAME"
systemctl restart "$SVC_NAME"

# ── 6. nginx reverse proxy ───────────────────────────────────────────────────
log "Configuring nginx reverse proxy"
SERVER_NAME="${DOMAIN:-_}"
NGINX_CONF="/etc/nginx/sites-available/${SVC_NAME}"
cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name ${SERVER_NAME};

    client_max_body_size 50M;

    # Streamlit WebSocket support
    location / {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
EOF
ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/${SVC_NAME}"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# ── 7. Firewall ──────────────────────────────────────────────────────────────
log "Opening firewall ports 80 + 443 + 22"
ufw allow 22/tcp comment "SSH"        >/dev/null 2>&1 || true
ufw allow 80/tcp comment "HTTP"       >/dev/null 2>&1 || true
ufw allow 443/tcp comment "HTTPS"     >/dev/null 2>&1 || true
ufw --force enable                    >/dev/null 2>&1 || true

# ── 8. SSL (only if DOMAIN is set) ───────────────────────────────────────────
if [[ -n "$DOMAIN" ]]; then
    log "Requesting Let's Encrypt SSL for $DOMAIN"
    if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
               -m "pacpl.tradingdesk@gmail.com" --redirect; then
        log "SSL active at https://$DOMAIN"
    else
        warn "Certbot failed — DNS may not yet point at this VPS. Retry later with:"
        warn "  certbot --nginx -d $DOMAIN"
    fi
fi

# ── 9. Status report ─────────────────────────────────────────────────────────
sleep 3
STATUS="$(systemctl is-active "$SVC_NAME" || true)"
log "DONE"
cat <<EOF

  Service:    $SVC_NAME  (state: $STATUS)
  App dir:    $APP_DIR
  Log tail:   journalctl -u $SVC_NAME -f    (or tail -f /var/log/${SVC_NAME}.log)
  Restart:    systemctl restart $SVC_NAME
  Secrets:    nano /root/.streamlit/secrets.toml
  URL:        http://${VPS_IP}
$( [[ -n "$DOMAIN" ]] && echo "  Custom:     https://$DOMAIN" )

  Next steps:
    1. Open:  http://${VPS_IP}  in your browser
    2. Login: admin / 0000
    3. Edit:  nano /root/.streamlit/secrets.toml  to paste your real credentials
    4. Apply: systemctl restart $SVC_NAME

  Redeploy (to pull latest from GitHub):
    cd $APP_DIR && git pull && systemctl restart $SVC_NAME

EOF
