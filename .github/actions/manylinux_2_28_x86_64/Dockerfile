FROM quay.io/pypa/manylinux_2_28_x86_64:latest

COPY  /entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
