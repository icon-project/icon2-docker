#!/bin/bash
SRC_DIR="/s6-int/"
DST_DIR="/etc"

if [ -d "${SRC_DIR}" ]; then
    echo "Copying S6 files ...."
    cp -rfv /s6-int/* /etc/
else
    echo "It does working the debug_mode"
fi
