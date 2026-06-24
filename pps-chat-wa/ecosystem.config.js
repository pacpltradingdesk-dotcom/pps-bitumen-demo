// pm2 config for the isolated WhatsApp link service.
// Runs as its OWN app `pps-chat-wa` — never merge with the bulk `whatsapp-server`.
module.exports = {
  apps: [
    {
      name: "pps-chat-wa",
      cwd: "/opt/pps-chat-wa",
      script: "server.js",
      env: {
        PORT: "8530",
        PPS_INBOUND: "/opt/pps-bitumen/wa_inbound.jsonl",
      },
      max_memory_restart: "600M",
      autorestart: true,
    },
  ],
};
