#!/usr/bin/with-contenv bash
if [ -f /goloop/.env ]; then
    export $(cat /goloop/.env)
fi
export BASE_DIR=${BASE_DIR:-"/goloop"}
export LOG_OUTPUT_TYPE=${LOG_OUTPUT_TYPE:-"file"}
export GOLOOP_CONFIG=${GOLOOP_CONFIG:-"${BASE_DIR}/config/server.json"}
export GOLOOP_NODE_SOCK=${GOLOOP_NODE_SOCK:-"${BASE_DIR}/data/cli.sock"}
export LOGDIR=${LOGDIR:-"${BASE_DIR}/logs"}
export BOOTING_LOG=${BOOTING_LOG:-"${LOGDIR}/booting.log"}
export LOGFILE=${LOGFILE:-"${LOGDIR}/goloop.log"}


function logging() {
    MSG=${1:-""}
    APPEND_STRING=${2:-"\n"}
    LOG_TYPE=${3:-"booting"}
    LOG_DATE=$(date +%Y%m%d)
    SCRIPT_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
    if [[ ! -e "$LOGDIR" ]];then
        mkdir -p "$LOGDIR"
    fi
    if [[ ${APPEND_STRING} == "\n" ]] ;then
        echo -ne "I|$(date '+%Y%m%d-%T.000000')|-|${SCRIPT_PATH}| $MSG ${APPEND_STRING}" >> "${LOGDIR}/${LOG_TYPE}.log"
    else
        echo -ne "$MSG ${APPEND_STRING}" >> "${LOGDIR}/${LOG_TYPE}.log"
    fi
}

