#!/usr/bin/env bash
# Installe la veille sur un VPS Debian/Ubuntu, en service systemd.
# Usage (sur le serveur, en root) :
#   bash install.sh git@github.com:ttaourirt/freelance-pipeline.git
set -euo pipefail

REPO_URL="${1:-}"
APP_DIR="/opt/freelance-pipeline"
RUN_USER="fpwatch"

if [[ -z "$REPO_URL" ]]; then
  echo "Usage: bash install.sh <url-du-depot-git>" >&2
  exit 1
fi

echo "== 1/6  paquets systeme"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git

echo "== 2/6  utilisateur $RUN_USER"
id -u "$RUN_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$RUN_USER"

echo "== 3/6  depot dans $APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi
chown -R "$RUN_USER:$RUN_USER" "$APP_DIR"

echo "== 4/6  environnement python"
sudo -u "$RUN_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$RUN_USER" "$APP_DIR/.venv/bin/pip" install -q --upgrade pip
sudo -u "$RUN_USER" "$APP_DIR/.venv/bin/pip" install -q requests python-dotenv

echo "== 5/6  configuration"
if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chown "$RUN_USER:$RUN_USER" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  echo "   .env cree. Renseigne TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID dans $APP_DIR/.env"
fi
mkdir -p "$APP_DIR/data" "$APP_DIR/output"
chown -R "$RUN_USER:$RUN_USER" "$APP_DIR/data" "$APP_DIR/output"

echo "== 6/6  service systemd"
cp "$APP_DIR/deploy/fp-watch.service" /etc/systemd/system/fp-watch.service
systemctl daemon-reload
systemctl enable --now fp-watch

echo
echo "Installé. Commandes utiles :"
echo "  journalctl -u fp-watch -f          # voir les passages en direct"
echo "  systemctl status fp-watch          # etat"
echo "  systemctl restart fp-watch         # apres modification du .env"
