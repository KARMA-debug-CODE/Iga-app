# nginx with Iga's configuration only: the tests of the nginx layer build this stage alone (no npm needed).
FROM nginx:1.27-alpine AS web-base
COPY nginx/nginx.conf /etc/nginx/nginx.conf
# A template: the entrypoint fills in the NGINX_* settings (defaults in nginx/defaults.envsh) at start.
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY nginx/proxy.conf nginx/cloudflare-ips.txt /etc/nginx/iga/
COPY --chmod=755 nginx/defaults.envsh /docker-entrypoint.d/05-iga-defaults.envsh
COPY --chmod=755 nginx/real-ip.sh /docker-entrypoint.d/25-iga-real-ip.sh
RUN rm -f /etc/nginx/conf.d/default.conf
EXPOSE 80

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

FROM web-base
COPY --from=build /app/dist /usr/share/nginx/html
