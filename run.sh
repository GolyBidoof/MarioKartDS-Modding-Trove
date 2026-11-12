#!/bin/sh
# Mario Kart DS Modding Trove
# run.sh — wrapper for apply.py
# SPDX-License-Identifier: MIT
exec python3 "$(dirname "$0")/apply.py" "$@"
