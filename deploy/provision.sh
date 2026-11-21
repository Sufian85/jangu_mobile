#!/usr/bin/env bash
# First-time setup for Jangu on an Ubuntu server that may already host other
# sites. Only adds Jangu's own user, database, service and nginx site. Safe to
# re-run. The first run stops once the server can receive code; push it (see
# DEPLOY.md) and run this again. Run as root:
#   ssh root@<server> 'bash -s' < deploy/provision.sh
set -euo pipefail
cd /

ROOT=/srv/jangu
APP=$ROOT/app
ENV_FILE=$APP/backend/.env
SITE=/etc/nginx/sites-available/jangu

as_app() { sudo -u jangu -H "$@"; }

# --no-upgrade leaves packages alone if another site already depends on them.
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-upgrade \
    certbot curl git nginx openssl postgresql python3-certbot-nginx python3-venv sudo

id jangu >/dev/null 2>&1 || adduser --system --group --home "$ROOT" --shell /usr/sbin/nologin jangu
chmod 755 "$ROOT"  # nginx has to reach media/ through here

# Code arrives by `git push` over SSH, and updateInstead checks it out on arrival.
if [ ! -d "$APP/.git" ]; then
    as_app git init -q -b main "$APP"
    as_app git -C "$APP" config receive.denyCurrentBranch updateInstead
fi
if [ ! -f "$APP/requirements.txt" ]; then
    echo "Ready to receive code. Run: git push vps main (see DEPLOY.md), then re-run this script."
    exit 3
fi

[ -d "$ROOT/venv" ] || as_app python3 -m venv "$ROOT/venv"
as_app "$ROOT/venv/bin/pip" install -q -r "$APP/requirements.txt"

# The database password lives only in .env, so it is set once, together with it.
if [ ! -f "$ENV_FILE" ]; then
    db_password=$(openssl rand -hex 24)
    db_port=$(sudo -u postgres psql -Atc 'show port')
    sudo -u postgres psql -q -v ON_ERROR_STOP=1 <<SQL
DO \$\$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jangu') THEN
        CREATE ROLE jangu LOGIN;
    END IF;
END \$\$;
ALTER ROLE jangu PASSWORD '$db_password';
SELECT 'CREATE DATABASE jangu OWNER jangu ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'jangu') \gexec
SQL
    (
        umask 077
        cat > "$ENV_FILE" <<ENV
SECRET_KEY=$(openssl rand -hex 50)
DEBUG=False
DATABASE_URL=postgresql://jangu:$db_password@127.0.0.1:$db_port/jangu
CSRF_TRUSTED_ORIGINS=https://jangumobile.site,https://www.jangumobile.site
ENV
    )
    chown jangu:jangu "$ENV_FILE"
fi

install -m 644 "$APP/deploy/jangu.service" /etc/systemd/system/jangu.service
systemctl daemon-reload
systemctl enable -q jangu

# certbot adds TLS to this file, so never overwrite it once it exists.
[ -e "$SITE" ] || install -m 644 "$APP/deploy/nginx-jangu.conf" "$SITE"
ln -sfn "$SITE" /etc/nginx/sites-enabled/jangu
# Other sites share this nginx: never leave it with a config that fails to load.
if ! nginx -t -q; then
    rm -f /etc/nginx/sites-enabled/jangu
    echo "nginx config test failed; Jangu site disabled, nginx not reloaded." >&2
    exit 1
fi
systemctl reload nginx

echo "Provisioned. Next: restore.sh (first deploy only), then update.sh."
