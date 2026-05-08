FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends hostapd iw iproute2 ca-certificates procps && \
    rm -rf /var/lib/apt/lists/*

COPY run-hostapd.sh /run-hostapd.sh
RUN chmod +x /run-hostapd.sh

ENTRYPOINT ["/run-hostapd.sh"]

