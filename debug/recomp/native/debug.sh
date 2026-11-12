#!/bin/sh
# Mario Kart DS Modding Trove
# debug/recomp/native/debug.sh — open native lldb/gdb on a recompiled binary
# SPDX-License-Identifier: MIT
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 BINARY [native-symbol]" >&2
    exit 2
fi

BIN=$1
shift
SYMBOL=
if [ $# -ge 1 ]; then
    case "$1" in
        d_*) SYMBOL=$1 ;;
        *) SYMBOL=d_$1 ;;
    esac
fi

if command -v lldb >/dev/null 2>&1; then
    if [ -n "$SYMBOL" ]; then
        exec lldb "$BIN" -o "breakpoint set -n $SYMBOL" -o run
    fi
    exec lldb "$BIN"
fi

if command -v gdb >/dev/null 2>&1; then
    if [ -n "$SYMBOL" ]; then
        exec gdb -q -ex "break $SYMBOL" -ex run "$BIN"
    fi
    exec gdb -q "$BIN"
fi

echo "Neither lldb nor gdb found." >&2
exit 1
