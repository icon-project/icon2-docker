#!/usr/bin/with-contenv bash
if [ -f /goloop/.env ]; then
    while IFS='=' read -r key temp || [[ -n "$key" ]]; do
        value=$(echo $temp | sed -e 's/^"//' -e 's/"$//')
        eval export $key=\"$value\"
    done < /goloop/.env
fi

export BASE_DIR=${BASE_DIR:-"/goloop"}
export LOG_OUTPUT_TYPE=${LOG_OUTPUT_TYPE:-"file"}
export GOLOOP_CONFIG=${GOLOOP_CONFIG:-"${BASE_DIR}/config/server.json"}
export GOLOOP_NODE_SOCK=${GOLOOP_NODE_SOCK:-"${BASE_DIR}/data/cli.sock"}
export LOGDIR=${LOGDIR:-"${BASE_DIR}/logs"}
export BOOTING_LOG=${BOOTING_LOG:-"${LOGDIR}/booting.log"}
export LOGFILE=${LOGFILE:-"${LOGDIR}/goloop.log"}
export ERROR_LOGFILE=${ERROR_LOGFILE:-"${LOGDIR}/error.log"}


function get_current_datetime_with_milliseconds() {
    python -c "import datetime; print(datetime.datetime.now().strftime('%Y%m%d-%H:%M:%S.%f'))"
}


function logging() {
    MSG=${1:-""}
    LOG_LEVEL=${2:-"INFO"}
    APPEND_STRING=${3:-"\n"}
    LOG_TYPE=${4:-"booting"}
    LOG_DATE=$(date +%Y%m%d)
    SCRIPT_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

    RED='\e[0;91m'
    GREEN='\e[0;92m'
    WHITE='\e[97m'
    ORANGE='\e[0;33m'
    BOLD_WHITE='\e[1;37m'
    RESET='\e[0m'  # RESET

    if [[ ! -e "$LOGDIR" ]];then
        mkdir -p "$LOGDIR"
    fi

    case ${LOG_LEVEL,,} in
        "info")
            LOG_LEVEL="I"
            COLOR=$BOLD_WHITE
            ;;
        "error")
            LOG_LEVEL="E"
            COLOR=$RED
            ;;
        "warn")
            LOG_LEVEL="W"
            COLOR=$ORANGE
            ;;
        *)
            LOG_LEVEL="U"  # Unknown
            COLOR=$WHITE
            ;;
    esac

    if [[ ${APPEND_STRING} == "\n" ]] ;then
        MESSAGE="${LOG_LEVEL}|$(get_current_datetime_with_milliseconds)|-|${SCRIPT_PATH}|${COLOR} ${MSG} ${APPEND_STRING}${RESET}"
        echo -ne "${MESSAGE}" | tee >(sed 's/\x1b\[[0-9;]*m//g' >> "${LOGDIR}/${LOG_TYPE}.log")
    else
        echo -ne "$MSG ${APPEND_STRING}" | tee -a  "${LOGDIR}/${LOG_TYPE}.log"
    fi
}


function CPrint {
    MSG=$1
    COLOR=$2
    if [[ "$COLOR" == "" ]];then
        MSG=$*
    fi
    DATE=$(get_current_datetime_with_milliseconds)
    RED='\e[0;91m'
    GREEN='\e[0;92m'
    WHITE='\e[97m'
    BOLD_WHITE='\e[1;37m'
    RESET='\e[0m'  # RESET

    if [[ "$COLOR" == "RED" ]];then
        MSG="[ERROR] $MSG"
    fi

    case $2 in
        "RED")
            printf "%b%s %b \n" "${RED}" "[$DATE] $MSG" "${RESET}" ;;
        "GREEN")
            printf "%b%s %b \n" "${GREEN}" "[$DATE] $MSG" "${RESET}" ;;
        "WHITE")
            printf "%b%s %b \n" "${WHITE}" "[$DATE] $MSG" "${RESET}" ;;
        *)
            printf "%b%s %b \n" "${BOLD_WHITE}" "[$DATE] $MSG" "${RESET}" ;;
    esac
}
