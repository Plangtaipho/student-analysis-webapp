"""Sign in with Google (OAuth 2.0 authorization-code flow, server side).

Only the standard library is used. The ID token comes straight from Google's token
endpoint over HTTPS with our client secret, so per Google's docs its signature does not
need to be re-checked; we still check issuer, audience, expiry and email_verified.
"""
import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleAuthError(Exception):
    pass


def authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"{AUTH_URL}?{query}"


def _post_token(data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, ValueError) as exc:
        raise GoogleAuthError("token exchange failed") from exc


def _decode_jwt_payload(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError) as exc:
        raise GoogleAuthError("bad id_token") from exc


def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """Swap the code for tokens and return the checked ID-token claims (sub, email, name)."""
    tokens = _post_token(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    )
    if "id_token" not in tokens:
        raise GoogleAuthError("no id_token")
    claims = _decode_jwt_payload(tokens["id_token"])
    if claims.get("iss") not in ISSUERS or claims.get("aud") != client_id:
        raise GoogleAuthError("wrong issuer or audience")
    if int(claims.get("exp", 0)) < time.time():
        raise GoogleAuthError("expired id_token")
    if not claims.get("sub") or not claims.get("email") or claims.get("email_verified") is not True:
        raise GoogleAuthError("email not verified")
    return {"sub": str(claims["sub"]), "email": str(claims["email"]).lower(), "name": str(claims.get("name", ""))}
