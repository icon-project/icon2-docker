ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG IS_NTP_BUILD
ARG VERSION
ARG BUILD_DATE
ARG VCS_REF
ARG NTP_VERSION=ntp-4.2.8p15

LABEL maintainer="infra team" \
      org.label-schema.build-date="${BUILD_DATE}" \
      org.label-schema.name="icon2-docker" \
      org.label-schema.description="Docker images for operating the ICON2 network." \
      org.label-schema.url="https://www.parametacorp.com/" \
      org.label-schema.vcs-ref="${VCS_REF}" \
      org.label-schema.vcs-url="https://github.com/icon-project/icon2-docker" \
      org.label-schema.vendor="PARAMETA Corp." \
      org.label-schema.version="${VERSION}-${VCS_REF}"

ENV IS_DOCKER=true \
    PATH=$PATH:/ctx/bin \
    GOLOOP_ENGINES='python,java' \
    GOLOOP_P2P_LISTEN=':7100' \
    GOLOOP_RPC_ADDR=':9000' \
    GOLOOP_RPC_DUMP='false' \
    GOLOOP_CONSOLE_LEVEL='debug' \
    GOLOOP_LOG_LEVEL='debug' \
    BASE_DIR='/goloop' \
    VERSION=$VERSION \
    BUILD_DATE=$BUILD_DATE \
    VCS_REF=$VCS_REF \
    COLUMNS=120

COPY src/ntpdate /usr/sbin/ntpdate
COPY ctx /ctx
COPY s6 /etc/

RUN apk update && \
        apk add --no-cache bash vim tree nmap git ncurses curl gomplate logrotate aria2 jq && \
        python -m pip install --no-cache-dir --upgrade pip  && \
        pip install --no-cache-dir -r /ctx/requirements.txt && \
        if [ "${IS_NTP_BUILD}" == "true" ]; then \
            wget --progress=dot:giga http://www.eecis.udel.edu/~ntp/ntp_spool/ntp4/ntp-4.2/${NTP_VERSION}.tar.gz ;\
            tar -xzf ${NTP_VERSION}.tar.gz ;\
            cd ${NTP_VERSION} ;\
            ./configure ;\
            make ;\
            cp ntpdate/ntpdate /usr/sbin/ ;\
            cd ../; rm -rf ${NTP_VERSION}*; fi && \
        apk del build-base linux-headers zlib-dev libffi-dev openssl-dev libressl-dev bsd-compat-headers gvim && \
        rm -rf /var/cache/apk/* && \
        wget -O /tmp/s6-overlay-amd64-installer https://github.com/just-containers/s6-overlay/releases/download/v2.2.0.3/s6-overlay-amd64-installer && \
        chmod +x /tmp/s6-overlay-amd64-installer && \
        /tmp/s6-overlay-amd64-installer / && \
        rm -rf /tmp/s6-overlay-amd64-installer

ENTRYPOINT []
CMD /init
