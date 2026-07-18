#!/bin/bash
# Check if JumpCloud TOTP seed exists in Keychain.
# Exits silently if found; emits a systemMessage warning if missing.

if ! security find-generic-password -s "jumpcloud-totp" -a "jcrawley" -w > /dev/null 2>&1; then
    jq -nc '{systemMessage: "⚠️ JumpCloud TOTP not in Keychain — MFA workflows will rely on push only. If push times out, add the seed: security add-generic-password -a jcrawley -s jumpcloud-totp -w <SEED>"}'
fi
