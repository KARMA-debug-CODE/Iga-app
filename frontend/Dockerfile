# nginx with Iga's configuration only: the tests of the nginx layer build this stage alone (no npm needed).
# nginx's stable line (even minor version), kept current by Dependabot; 1.27 was end-of-life with unpatched
# OpenSSL and other Alpine packages (critical and high CVEs).
FROM nginx:1.30-alpine AS web-base
COPY nginx/nginx.conf /etc/nginx/nginx.conf
# A template: the entrypoint fills in the NGINX_* settings (defaults in nginx/defaults.envsh) at start.
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY nginx/proxy.conf nginx/headers-common.conf nginx/headers-app.conf nginx/errors-api.conf nginx/cloudflare-ips.txt /etc/nginx/iga/
# HTTPS served by nginx itself: mount a tls.conf here (nginx/tls.conf.example).
# /srv/maintenance: maintenance mode's switch, a marker file on a volume shared with the backend, which
# writes it as a non-root user (docker-compose.yml). 1777 (sticky, like /tmp) so the volume is writable
# whichever container first initialises it; nginx only reads it.
RUN mkdir -p /etc/nginx/iga/tls /var/www/certbot \
    && mkdir -p /srv/maintenance && chmod 1777 /srv/maintenance
COPY --chmod=755 nginx/defaults.envsh /docker-entrypoint.d/05-iga-defaults.envsh
COPY --chmod=755 nginx/real-ip.sh /docker-entrypoint.d/25-iga-real-ip.sh
RUN rm -f /etc/nginx/conf.d/default.conf
EXPOSE 80

FROM node:25-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

FROM web-base
COPY --from=build /app/dist /usr/share/nginx/html
