FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends wpasupplicant iproute2 ca-certificates procps && \
    rm -rf /var/lib/apt/lists/*

COPY run-victim.sh /run-victim.sh
RUN chmod +x /run-victim.sh

ENTRYPOINT ["/run-victim.sh"]

