FROM freeradius/freeradius-server:latest

RUN mkdir -p /certs

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

