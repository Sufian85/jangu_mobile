#!/usr/bin/env bash
# Load a `manage.py dumpdata` file and its media archive into the empty production
# database. First deploy only: run after provision.sh and before update.sh, because
# load_catalogue must not add rows the dump also contains. Run as root:
#   /srv/jangu/app/deploy/restore.sh /tmp/data.json /tmp/media.tar.gz
set -euo pipefail

DATA=${1:?usage: restore.sh <data.json> <media.tar.gz>}
MEDIA=${2:?usage: restore.sh <data.json> <media.tar.gz>}
BACKEND=/srv/jangu/app/backend

cd "$BACKEND"
as_app() { sudo -u jangu -H "$@"; }
manage() { as_app /srv/jangu/venv/bin/python manage.py "$@"; }

manage migrate --no-input -v 0

# loaddata overwrites rows with matching keys, so refuse to run over live data.
products=$(manage shell -v 0 -c "from catalogue.models import Product; print(Product.objects.count())" | tail -1)
if [ "$products" != "0" ]; then
    echo "Refusing to restore: the database already has $products products." >&2
    exit 1
fi

as_app tar xzf "$MEDIA" -C "$BACKEND"
manage loaddata "$DATA"
