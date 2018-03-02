#!/bin/sh
set -e

#
# Builds and runs the image locally for testing purposes
#
# To run a specific command inside the image, pass the command to this script.
#

if ! [ -f settings.cfg ]; then
    echo > settings.cfg <<EOF
DATABASE_HOST = 'localhost'
DATABASE = 'dscomp'
USERNAME = 'dsuser'
PASSWORD = 'dspassword'
SECRET_KEY = 'devkey'
ADMIN_SECRET = 'admin'
EOF
fi

docker build -t dscomp .
docker run -it --rm \
    -p 8080:80 \
    --mount "type=bind,source=$(pwd)/settings.cfg,target=/etc/dscomp/settings.cfg" \
    dscomp "$@"
