#!/usr/bin/env python3
"""Emit a current JumpCloud TOTP code to stdout.

Reads the base32-encoded seed from the macOS login Keychain (service:
jumpcloud-totp, account: jcrawley) and computes the current 6-digit
RFC 6238 TOTP code (SHA-1, 30-second window).

Exit codes:
  0  success — 6 digits printed to stdout
  2  Keychain entry missing (actionable operator error)
  3  invalid seed or computation failure
"""
import base64
import hmac
import struct
import subprocess
import sys
import time


_WHITESPACE = str.maketrans("", "", " \t\n\r")


def main() -> int:
    try:
        seed = subprocess.check_output(
            ["security", "find-generic-password", "-s", "jumpcloud-totp", "-a", "jcrawley", "-w"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.stderr.write(
            "jumpcloud-totp: Keychain entry jumpcloud-totp/jcrawley missing (or `security` binary unavailable) — "
            "see ~/docs/superpowers/specs/2026-04-21-jumpcloud-totp-fallback-design.md "
            "§One-time setup\n"
        )
        return 2

    try:
        key = base64.b32decode(seed.upper().translate(_WHITESPACE))
    except Exception:
        sys.stderr.write(
            "jumpcloud-totp: invalid base32 seed in Keychain (check padding and that the seed contains only A-Z and 2-7)\n"
        )
        return 3

    counter = int(time.time()) // 30
    digest = hmac.new(key, struct.pack(">Q", counter), "sha1").digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    print(f"{code % 1_000_000:06d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
