"""Interactively create a daily FYERS access token for CQRP market data.

This tool sends no orders and never writes credentials to disk.  Enter the
resulting token yourself in Streamlit Secrets after the flow completes.
"""

from __future__ import annotations

from getpass import getpass
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests


REDIRECT_URI = "http://localhost:8501"
AUTH_CODE_URL = "https://api-t1.fyers.in/api/v3/generate-authcode"
TOKEN_URL = "https://api-t1.fyers.in/api/v3/validate-authcode"


class _CallbackHandler(BaseHTTPRequestHandler):
    """Receive the one-time localhost redirect without logging its query string."""

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        auth_code = parse_qs(urlparse(self.path).query).get("auth_code", [None])[0]
        if auth_code:
            self.server.auth_code = auth_code  # type: ignore[attr-defined]
            message = "FYERS authorization received. You can close this browser tab."
        else:
            message = "Waiting for the FYERS authorization code."
        payload = message.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    app_id = input("FYERS App ID: ").strip()
    secret_key = getpass("FYERS Secret Key (input hidden): ").strip()
    if not app_id or not secret_key:
        raise ValueError("FYERS App ID and Secret Key are required.")

    login_url = f"{AUTH_CODE_URL}?{urlencode({
        'client_id': app_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'state': 'cqrp_market_data',
    })}"
    print("\nOpen this FYERS login URL in a browser:\n")
    print(login_url)
    try:
        callback = HTTPServer(("localhost", 8501), _CallbackHandler)
    except OSError as exc:
        raise RuntimeError("Port 8501 is unavailable. Stop Streamlit, then run this script again.") from exc
    callback.timeout = 1
    callback.auth_code = None  # type: ignore[attr-defined]
    print("\nAfter approval, FYERS will return to localhost and this script will continue automatically.")
    print("Keep this PowerShell window open while you complete login in the browser.\n")
    try:
        while callback.auth_code is None:  # type: ignore[attr-defined]
            callback.handle_request()
    except KeyboardInterrupt:
        print("\nAuthorization cancelled.")
        return
    finally:
        callback.server_close()
    auth_code = callback.auth_code  # type: ignore[attr-defined]

    app_id_hash = hashlib.sha256(f"{app_id}:{secret_key}".encode()).hexdigest()
    response = requests.post(
        TOKEN_URL,
        json={"grant_type": "authorization_code", "appIdHash": app_id_hash, "code": auth_code},
        timeout=20,
    ).json()
    if not isinstance(response, dict) or not response.get("access_token"):
        message = response.get("message", "FYERS did not return an access token.") if isinstance(response, dict) else "Unexpected FYERS response."
        raise RuntimeError(message)

    print("\nDaily FYERS access token (copy it directly into Streamlit Secrets):\n")
    print(response["access_token"])
    print("\nNever commit this token or paste it into chat. It is data-only in CQRP.")


if __name__ == "__main__":
    main()
