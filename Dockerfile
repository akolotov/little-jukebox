FROM nginxinc/nginx-unprivileged:alpine

ENV JUKEBOX_BASE_PATH=/apps/little-jukebox \
    NGINX_ENVSUBST_FILTER=^JUKEBOX_BASE_PATH$

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY site/ /usr/share/nginx/html/

EXPOSE 8080
