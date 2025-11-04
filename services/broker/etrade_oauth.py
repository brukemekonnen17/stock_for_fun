import os
import requests
from requests_oauthlib import OAuth1

ETRADE_SANDBOX = "https://apisb.etrade.com"
ETRADE_LIVE    = "https://api.etrade.com"

def _base() -> str:
    return ETRADE_SANDBOX if os.getenv("ETRADE_SANDBOX","true").lower()=="true" else ETRADE_LIVE

def request_token(consumer_key: str, consumer_secret: str, callback: str = "oob") -> dict:
    url = f"{_base()}/oauth/request_token"
    oauth = OAuth1(consumer_key, client_secret=consumer_secret, callback_uri=callback, signature_type="auth_header")
    r = requests.post(url, auth=oauth, timeout=15)
    r.raise_for_status()
    data = dict(x.split("=") for x in r.text.split("&"))
    # data has oauth_token, oauth_token_secret, oauth_callback_confirmed
    auth_url = f"{_base()}/oauth/authorize?key={consumer_key}&token={data['oauth_token']}"
    return {"oauth_token": data["oauth_token"], "oauth_token_secret": data["oauth_token_secret"], "authorize_url": auth_url}

def exchange_token(consumer_key: str, consumer_secret: str, oauth_token: str, oauth_token_secret: str, verifier: str) -> dict:
    url = f"{_base()}/oauth/access_token"
    oauth = OAuth1(
        client_key=consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        verifier=verifier,
        signature_type="auth_header",
    )
    r = requests.post(url, auth=oauth, timeout=15)
    r.raise_for_status()
    data = dict(x.split("=") for x in r.text.split("&"))
    # returns oauth_token, oauth_token_secret
    return {"access_token": data["oauth_token"], "access_token_secret": data["oauth_token_secret"]}

