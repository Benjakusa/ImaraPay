#!/usr/bin/env python
"""
test_webhook_local.py
=====================
Simulate a real Meta WhatsApp Cloud API webhook POST directly to your running
Django server (localhost:8000). Tests the full pipeline:

  Meta POST → Django view → signature check → InboundWhatsAppEvent created
  → Celery task (sync fallback) → PhoneIdentity resolved → command parsed
  → handler dispatched → reply composed → WhatsApp adapter (sim mode logs reply)

Usage:
    python test_webhook_local.py [command]

Examples:
    python test_webhook_local.py "today"
    python test_webhook_local.py "request 2500 for INV-001"
    python test_webhook_local.py "last 5"
    python test_webhook_local.py "help"

Prerequisites:
    - Django server running:  python manage.py runserver 8000
    - At least one ACTIVE PhoneIdentity in the DB for the phone number below
      (or leave FROM_PHONE as-is — unrecognised senders get an onboarding reply)

Set FROM_PHONE to match an active PhoneIdentity in your local DB.
"""

import hashlib
import hmac
import json
import sys
import time
import uuid
import requests

# ── Configuration ─────────────────────────────────────────────────────────────
WEBHOOK_URL = "http://localhost:8000/api/v1/whatsapp/webhook/"
# Must match WHATSAPP_APP_SECRET in .env (or leave empty — sim mode bypasses check)
APP_SECRET = ""
# Phone number to simulate message from (must be bound as PhoneIdentity for full flow)
FROM_PHONE = "254722839617"
WABA_ID = "sim-waba-id"
PHONE_NUMBER_ID = "sim-phone-number-id"

def build_meta_payload(from_phone: str, text: str) -> dict:
    """Build a payload that matches Meta's real webhook JSON structure."""
    wamid = f"wamid.sim_{uuid.uuid4().hex[:12]}"
    timestamp = str(int(time.time()))
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": WABA_ID,
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": from_phone,
                                "phone_number_id": PHONE_NUMBER_ID
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test Merchant"},
                                    "wa_id": from_phone
                                }
                            ],
                            "messages": [
                                {
                                    "from": from_phone,
                                    "id": wamid,
                                    "timestamp": timestamp,
                                    "text": {"body": text},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

def make_signature(secret: str, body: bytes) -> str:
    """Generate X-Hub-Signature-256 like Meta does."""
    if not secret:
        return ""
    h = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={h}"

def send_webhook(text: str):
    payload = build_meta_payload(FROM_PHONE, text)
    body = json.dumps(payload).encode()
    sig = make_signature(APP_SECRET, body)

    print(f"\n{'='*60}")
    print(f"  Simulating WhatsApp message from +{FROM_PHONE}")
    print(f"  Command: \"{text}\"")
    print(f"{'='*60}")

    # Use raw socket with HTTP/1.0 — Django dev server handles this reliably.
    # Python's http.client and requests use HTTP/1.1 chunked encoding which
    # can cause the dev server to delay sending the response.
    import socket as _socket
    host, port = 'localhost', 8000
    path = '/api/v1/whatsapp/webhook/'

    extra_headers = ""
    if sig:
        extra_headers += f"X-Hub-Signature-256: {sig}\r\n"

    raw_request = (
        f"POST {path} HTTP/1.0\r\n"
        f"Host: {host}:{port}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"{extra_headers}"
        f"\r\n"
    ).encode() + body

    try:
        sock = _socket.create_connection((host, port), timeout=15)
        sock.sendall(raw_request)
        response_data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_data += chunk
        sock.close()

        response_str = response_data.decode('utf-8', errors='replace')
        first_line = response_str.split('\r\n')[0] if response_str else ''
        status_code = int(first_line.split()[1]) if first_line and len(first_line.split()) >= 2 else 0
        print(f"\n  {first_line}")
        print(f"  {'✓ Webhook accepted (200)' if status_code == 200 else '✗ Unexpected status'}")

    except ConnectionRefusedError:
        print("\n  ✗ Connection refused — is Django running on port 8000?")
        print("    Run:  python manage.py runserver 8000")
        sys.exit(1)
    except OSError as e:
        print(f"\n  ✗ Network error: {e}")
        sys.exit(1)

    print(f"\n  Check Django server logs for the conversation engine output.")
    print(f"  The adapter reply will appear as: [SIM] WhatsApp → ...")


if __name__ == "__main__":
    command = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "today"
    send_webhook(command)
