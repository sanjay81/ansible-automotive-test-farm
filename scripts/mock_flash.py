#!/usr/bin/env python3

import argparse
import hashlib
import hmac
import json
import re
from pathlib import Path
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(
        description="Simulated ECU firmware flashing"
    )

    parser.add_argument("--image", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sha256", required=True)

    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-fA-F]{64}", args.sha256):
        raise SystemExit("Invalid SHA-256 checksum: expected 64 hexadecimal characters")

    if not re.fullmatch(r"ECU-[A-Za-z0-9][A-Za-z0-9._-]*", args.device):
        raise SystemExit("Invalid device ID: expected a simulated ECU-... identifier")

    image = Path(args.image)

    if not image.is_file():
        raise SystemExit(f"Firmware not found: {image}")

    actual_checksum = hashlib.sha256(
        image.read_bytes()
    ).hexdigest()

    if not hmac.compare_digest(actual_checksum, args.sha256.lower()):
        raise SystemExit("Firmware checksum mismatch")

    result = {
        "device": args.device,
        "firmware": image.name,
        "checksum": actual_checksum,
        "status": "SIMULATED_FLASH_SUCCESS",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(result, indent=2) + "\n"
    )

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
