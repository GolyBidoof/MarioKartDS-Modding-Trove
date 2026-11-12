# Mario Kart DS Modding Trove
# tools/verify.py — shared mod verification helpers
# SPDX-License-Identifier: MIT
"""Shared verification helpers for mods."""
from __future__ import annotations


class VerifyError(RuntimeError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerifyError(message)
