ARG BASE_IMAGE
ARG IS_NTP_BUILD
ARG NTP_VERSION=ntp-4.2.8p15

FROM ${BASE_IMAGE}
ENV IS_DOCKER=true \
    PATH=$PATH:/ctx/bin \
    GOLOOP_ENGINES='python,java' \
    GOLOOP_P2P_LISTEN=':7100' \
    GOLOOP_RPC_ADDR=':9000' \
    GOLOOP_RPC_DUMP='true' \
    GOLOOP_CONSOLE_LEVEL='debug' \
    GOLOOP_LOG_LEVEL='debug' \
    BASE_DIR='/goloop'


RUN apk update && \
    apk add --no-cache bash vim tree nmap git ncurses curl gomplate logrotate aria2 jq&& \
    python -m pip install --upgrade pip

ADD https://github.com/just-containers/s6-overlay/releases/download/v2.2.0.3/s6-overlay-amd64-installer /tmp/
RUN chmod +x /tmp/s6-overlay-amd64-installer && /tmp/s6-overlay-amd64-installer /

ADD src/ntpdate /usr/sbin/ntpdate
ADD ctx /ctx
ADD s6 /etc/


RUN if [ "${IS_NTP_BUILD}" == "true" ]; then \
        wget http://www.eecis.udel.edu/~ntp/ntp_spool/ntp4/ntp-4.2/${NTP_VERSION}.tar.gz && \
        tar -xzf ${NTP_VERSION}.tar.gz && \
        cd ${NTP_VERSION} && \
        ./configure && \
        make && \
        cp ntpdate/ntpdate /usr/sbin/ && \
        cd ../ && rm -rf ${NTP_VERSION}* ;\
    fi

RUN pip install --no-cache-dir -r /ctx/requirements.txt

ENTRYPOINT ["/init"]

