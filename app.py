import os
import time
from collections import defaultdict, deque

from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix
import requests

from depop import fetch_listings

app = Flask(__name__)
# Render (and most PaaS) terminate TLS at a proxy and forward the real
# client IP via X-Forwarded-For - without this, remote_addr is the proxy's
# IP for every request and the rate limit below applies globally, not per-IP.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

# ponytail: in-memory per-IP rate limit, single-process only (resets on
# restart/redeploy, doesn't share across instances). Move to a Redis-backed
# limiter (e.g. Flask-Limiter with a redis storage_uri) if this needs to
# hold up under multiple dynos/instances or real abuse.
RATE_LIMIT = 20  # requests per window per IP
RATE_WINDOW = 3600  # seconds
_hits: dict[str, deque] = defaultdict(deque)


def _rate_limited(ip: str) -> bool:
    now = time.time()
    hits = _hits[ip]
    while hits and hits[0] < now - RATE_WINDOW:
        hits.popleft()
    if len(hits) >= RATE_LIMIT:
        return True
    hits.append(now)
    return False


def _client_ip() -> str:
    # Render fronts every app with Cloudflare, which adds its own hop on top
    # of Render's internal proxy - ProxyFix's single-hop X-Forwarded-For
    # parsing can't reliably peel both, so prefer Cloudflare's own header
    # (set by Cloudflare itself, not client-controlled) when present.
    return request.headers.get("CF-Connecting-IP") or request.remote_addr or "unknown"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/listings", methods=["POST"])
def listings():
    if _rate_limited(_client_ip()):
        return render_template("index.html", error="Too many requests from your IP - try again in a bit."), 429

    username = request.form.get("username", "").strip()
    cookie = request.form.get("cookie", "").strip()
    if not username or not cookie:
        return render_template("index.html", error="Username and cookie are both required.")

    try:
        items = fetch_listings(username, cookie)
    except ValueError as e:
        return render_template("index.html", error=str(e))
    except requests.HTTPError as e:
        return render_template("index.html", error=f"Depop request failed: {e}")
    except requests.RequestException as e:
        return render_template("index.html", error=f"Couldn't reach Depop: {e}")

    return render_template("listings.html", items=items, username=username)


if __name__ == "__main__":
    app.run(debug=bool(os.environ.get("FLASK_DEBUG")), host="0.0.0.0", port=int(os.environ.get("PORT", 5050)))
