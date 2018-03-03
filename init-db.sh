#!/bin/sh
set -e

#
# Initializes the application database
#

cd /usr/local/lib/dscomp/
. venv/bin/activate

if ! [ -f "/etc/dscomp/settings.cfg" ]; then
    echo "Error: /etc/dscomp/settings.cfg is missing." 1>&2
    exit 1
fi

export FLASK_APP=dscomp
export FLASKR_SETTINGS="/etc/dscomp/settings.cfg"
flask initdb
