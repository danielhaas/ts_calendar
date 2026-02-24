#!/usr/bin/env python3
"""One-time OAuth2 setup for TeamSnap API tokens.

Run this locally to get access and refresh tokens, then set them as
environment variables in Vercel.
"""

import webbrowser

import requests

AUTH_URL = "https://auth.teamsnap.com/oauth/authorize"
TOKEN_URL = "https://auth.teamsnap.com/oauth/token"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


def main():
    print("=== TeamSnap OAuth2 Setup ===\n")

    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()

    authorize_url = (
        f"{AUTH_URL}"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=read"
    )

    print(f"\nOpening browser to authorize...\n{authorize_url}\n")
    webbrowser.open(authorize_url)

    auth_code = input("Paste the authorization code here: ").strip()

    print("\nExchanging code for tokens...")
    resp = requests.post(TOKEN_URL, data={
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=15)
    resp.raise_for_status()
    tokens = resp.json()

    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token", "")

    print("\n=== Tokens ===")
    print(f"Access Token:  {access_token}")
    print(f"Refresh Token: {refresh_token}")

    print("\n=== Vercel Environment Setup ===")
    print("Run these commands to set your environment variables:\n")
    print(f'  vercel env add TEAMSNAP_CLIENT_ID     # paste: {client_id}')
    print(f'  vercel env add TEAMSNAP_CLIENT_SECRET  # paste: {client_secret}')
    print(f'  vercel env add TEAMSNAP_ACCESS_TOKEN   # paste: {access_token}')
    print(f'  vercel env add TEAMSNAP_REFRESH_TOKEN  # paste: {refresh_token}')
    print()


if __name__ == "__main__":
    main()
