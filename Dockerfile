#
# Stage 1: build
#

FROM alpine:latest AS build

RUN apk update && apk add --no-cache \
    build-base \
    gfortran \
    lapack \
    lapack-dev \
    libffi \
    libffi-dev \
    libgfortran \
    linux-headers \
    musl-dev \
    python3 \
    python3-dev

# Initialize Python virtual environment.
WORKDIR /usr/local/lib/dscomp/
RUN python3 -m venv venv

# Install dependencies.
COPY requirements.*.txt ./
RUN . venv/bin/activate \
    && pip install -r requirements.0.txt \
    && pip install -r requirements.1.txt

# Install this package.
COPY MANIFEST.in setup.py wsgi.py ./
COPY dscomp ./dscomp
RUN ls \
    &&. venv/bin/activate \
    && pip install uwsgi \
    && pip install -e .

#
# Stage 2: deploy
#

FROM alpine:latest

RUN apk update && apk add --no-cache \
    lapack \
    libffi \
    libgfortran \
    libstdc++ \
    nginx \
    python3 \
    tini

# Create directories to hold the uWSGi socket file, nginx PID file,
# and Flask app configuration file.
RUN mkdir -p /var/local/lib/dscomp /run/nginx /etc/dscomp \
    && chown nginx:nginx /var/local/lib/dscomp/

COPY --from=build /usr/local/lib/dscomp /usr/local/lib/dscomp
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY run-server.sh init-db.sh /usr/local/bin/

# Create and link CSV upload locations.
RUN mkdir /var/local/lib/dscomp/csvs /var/local/lib/dscomp/privatecsvs \
    && chown nginx:nginx /var/local/lib/dscomp/* \
    && ln -s /var/local/lib/dscomp/csvs /usr/local/lib/dscomp/dscomp/csvs \
    && ln -s /var/local/lib/dscomp/privatecsvs /usr/local/lib/dscomp/dscomp/privatecsvs

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/usr/local/bin/run-server.sh"]

EXPOSE 80
VOLUME /var/local/lib/dscomp/csvs
VOLUME /var/local/lib/dscomp/privatecsvs
