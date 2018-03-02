#!/bin/sh
set -e

#
# Starts uWSGi and nginx
#

cd /usr/local/lib/dscomp/
. venv/bin/activate

if ! [ -f "/etc/dscomp/settings.cfg" ]; then
    echo "Error: /etc/dscomp/settings.cfg is missing." 1>&2
    exit 1
fi

export FLASKR_SETTINGS="/etc/dscomp/settings.cfg"
# TODO: add workers with the --processes or --threads option?
uwsgi \
    --uid nginx --gid nginx \
    --uwsgi-socket /var/local/lib/dscomp/uwsgi.sock \
    --master \
    --wsgi-file wsgi.py \
    --callable app &

nginx -g 'daemon off;'
