FROM ghcr.io/nikteliy/manylinux_2_24_armv7l:python3.7

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
