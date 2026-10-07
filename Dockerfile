FROM nginxinc/nginx-unprivileged:alpine

ENV JUKEBOX_BASE_PATH=/apps/little-jukebox \
    NGINX_ENVSUBST_FILTER=^JUKEBOX_BASE_PATH$

USER root
RUN sed -i '1i load_module /usr/lib/nginx/modules/ngx_http_image_filter_module.so;' /etc/nginx/nginx.conf \
    && mkdir -p /var/cache/nginx/thumbnails \
    && chown 101:101 /var/cache/nginx/thumbnails
USER 101
RUN nginx -t -e stderr

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY site/ /usr/share/nginx/html/

EXPOSE 8080
