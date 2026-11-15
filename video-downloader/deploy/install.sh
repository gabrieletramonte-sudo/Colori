#!/usr/bin/env bash
# Installa/aggiorna Scarica Video su un VPS Debian/Ubuntu.
#   curl -fsSL https://raw.githubusercontent.com/gabrieletramonte-sudo/Colori/ccr-e3bf69b6-oq3rp2/video-downloader/deploy/install.sh | sudo bash
# Con dominio (HTTPS automatico):  ... | sudo DOMAIN=video.tuodominio.it bash
set -euo pipefail

REPO="https://github.com/gabrieletramonte-sudo/Colori.git"
BRANCH="${BRANCH:-ccr-e3bf69b6-oq3rp2}"
DIR=/opt/scarica-video
APP="$DIR/video-downloader"
ENVFILE=/etc/scarica-video.env
PORT="${PORT:-8000}"
DOMAIN="${DOMAIN:-}"

[ "$(id -u)" = 0 ] || { echo "Esegui come root (sudo)."; exit 1; }
command -v apt-get >/dev/null || { echo "Serve Debian/Ubuntu (apt)."; exit 1; }

echo "==> Pacchetti di sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv ffmpeg git curl >/dev/null

echo "==> Utente di servizio"
id scarica >/dev/null 2>&1 || useradd --system --home "$DIR" --shell /usr/sbin/nologin scarica

echo "==> Codice"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch -q origin "$BRANCH" && git -C "$DIR" reset -q --hard "origin/$BRANCH"
else
  git clone -q -b "$BRANCH" "$REPO" "$DIR"
fi
python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" install -q -U pip
"$DIR/venv/bin/pip" install -q -U -r "$APP/requirements.txt"
chown -R scarica:scarica "$DIR"

echo "==> Configurazione"
if [ ! -f "$ENVFILE" ]; then
  PASS="${APP_PASSWORD:-}"
  if [ -z "$PASS" ] && [ -r /dev/tty ]; then
    read -r -s -p "Scegli la password del sito: " PASS </dev/tty; echo
  fi
  [ -n "$PASS" ] || PASS="$(head -c 12 /dev/urandom | base64 | tr -d '/+=')"
  if [ -n "$DOMAIN" ]; then BIND=127.0.0.1; else BIND=0.0.0.0; fi
  umask 077
  cat > "$ENVFILE" <<CONF
APP_PASSWORD=$PASS
HOST=$BIND
PORT=$PORT
COOKIES_FILE=/var/lib/scarica-video/cookies.txt
CONF
  chown root:scarica "$ENVFILE"; chmod 640 "$ENVFILE"
  NEWPASS="$PASS"
fi

cat > /etc/systemd/system/scarica-video.service <<UNIT
[Unit]
Description=Scarica Video (Instagram/TikTok)
After=network-online.target
Wants=network-online.target

[Service]
User=scarica
EnvironmentFile=$ENVFILE
WorkingDirectory=$APP
ExecStart=$DIR/venv/bin/python $APP/app.py --no-browser
Restart=on-failure
StateDirectory=scarica-video
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
UNIT

# Aggiorna yt-dlp ogni notte (Instagram/TikTok cambiano spesso)
cat > /etc/cron.daily/scarica-video-update <<CRON
#!/bin/sh
$DIR/venv/bin/pip install -q -U yt-dlp && systemctl restart scarica-video
CRON
chmod +x /etc/cron.daily/scarica-video-update

systemctl daemon-reload
systemctl enable -q scarica-video
systemctl restart scarica-video

if [ -n "$DOMAIN" ]; then
  echo "==> HTTPS con Caddy per $DOMAIN"
  if ! command -v caddy >/dev/null; then
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https gnupg >/dev/null
    curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq && apt-get install -y -qq caddy >/dev/null
  fi
  cat > /etc/caddy/Caddyfile <<CADDY
$DOMAIN {
	reverse_proxy 127.0.0.1:$PORT
}
CADDY
  systemctl reload caddy || systemctl restart caddy
  command -v ufw >/dev/null && ufw status | grep -q "Status: active" && ufw allow 80,443/tcp >/dev/null || true
  URL="https://$DOMAIN"
else
  command -v ufw >/dev/null && ufw status | grep -q "Status: active" && ufw allow "$PORT"/tcp >/dev/null || true
  IP="$(curl -fsS -4 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
  URL="http://$IP:$PORT"
fi

sleep 1
systemctl is-active -q scarica-video && STATUS="attivo" || STATUS="NON partito (vedi: journalctl -u scarica-video -n 50)"
echo
echo "============================================"
echo " Scarica Video: $STATUS"
echo " Apri dal telefono:  $URL"
[ -n "${NEWPASS:-}" ] && echo " Password:           $NEWPASS   (utente: qualsiasi)"
echo " Cambia password:    sudo nano $ENVFILE && sudo systemctl restart scarica-video"
echo " Cookie Instagram:   /var/lib/scarica-video/cookies.txt (poi riavvia)"
echo "============================================"
