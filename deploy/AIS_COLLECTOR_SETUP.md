# Deploy the AIS collector on the VPS

Prereq: a free AISStream API key from https://aisstream.io (sign in with GitHub
→ API Keys → Create). Keep it secret.

1. SSH in and pull latest:
   ```
   ssh root@82.112.231.3
   cd /opt/pps-bitumen && git pull
   ```

2. Find the venv python the app uses and install the new dep:
   ```
   ls /opt/pps-bitumen          # locate venv (e.g. venv/ or .venv/)
   /opt/pps-bitumen/venv/bin/pip install "websocket-client>=1.7.0"
   ```
   If the venv path differs, update `ExecStart` in the service file accordingly.

3. Install the service with your key:
   ```
   cp deploy/pps-ais-collector.service /etc/systemd/system/
   sed -i 's/REPLACE_WITH_KEY/<YOUR_KEY>/' /etc/systemd/system/pps-ais-collector.service
   systemctl daemon-reload
   systemctl enable --now pps-ais-collector
   ```

4. Verify:
   ```
   systemctl status pps-ais-collector --no-pager
   journalctl -u pps-ais-collector -n 30 --no-pager   # expect "flushed N tankers"
   cat /opt/pps-bitumen/tbl_live_vessels.json | head    # real vessels
   ```

5. Auto-deploy: add a restart to the existing 10-min deploy cron so code pulls
   also restart the collector:
   ```
   # in the deploy script, after 'git pull && systemctl restart pps-bitumen':
   systemctl restart pps-ais-collector
   ```

## Rollback
`systemctl disable --now pps-ais-collector` — the app immediately falls back to
simulated vessels (no code change needed).
