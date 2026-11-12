#!/bin/sh
# Mario Kart DS Modding Trove
# run.command — double-click wrapper for macOS
# SPDX-License-Identifier: MIT
cd "$(dirname "$0")" || exit 1
ROM=$(osascript -e 'POSIX path of (choose file with prompt "Choose a Mario Kart DS ROM")' 2>/dev/null)
[ -n "$ROM" ] || exit 1
python3 apply.py "$ROM"
printf "\nPress Return to close..."
read -r _
