import json
import os
import time
from collections import defaultdict, deque

from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from depop import parse_shop_response

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB - a shop's product JSON is small; reject anything huge
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


# Runs in the user's own browser (from a bookmarklet), not on this server -
# Depop's Cloudflare bot management blocks server-to-server requests to
# webapi.depop.com regardless of cookie validity, so the fetch has to
# happen from a real logged-in browser tab. It POSTs the raw API response
# to /from-browser below, which never talks to Depop itself.
BOOKMARKLET_TEMPLATE = """(function(){
var u=prompt('Your Depop username?');
if(!u)return;
fetch('https://webapi.depop.com/api/v2/shop/'+encodeURIComponent(u)+'/products/',{credentials:'include'})
.then(function(r){if(!r.ok)throw new Error('Depop returned HTTP '+r.status+' - are you logged in?');return r.json();})
.then(function(data){
var f=document.createElement('form');
f.method='POST';f.action='__BASE_URL__from-browser';f.target='_blank';
var i=document.createElement('input');i.type='hidden';i.name='data';i.value=JSON.stringify(data);f.appendChild(i);
var j=document.createElement('input');j.type='hidden';j.name='username';j.value=u;f.appendChild(j);
document.body.appendChild(f);f.submit();
})
.catch(function(e){alert('Depop to Vinted: '+e.message);});
})();"""


@app.route("/")
def index():
    bookmarklet = "javascript:" + BOOKMARKLET_TEMPLATE.replace("__BASE_URL__", request.url_root).replace("\n", " ")
    return render_template("index.html", bookmarklet=bookmarklet)


@app.route("/from-browser", methods=["POST"])
def from_browser():
    if _rate_limited(_client_ip()):
        return render_template("index.html", error="Too many requests from your IP - try again in a bit."), 429

    username = request.form.get("username", "").strip()
    raw = request.form.get("data", "")
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return render_template("index.html", error="Couldn't read the data the bookmarklet sent - try clicking it again."), 400

    items = parse_shop_response(payload)
    return render_template("listings.html", items=items, username=username)


if __name__ == "__main__":
    app.run(debug=bool(os.environ.get("FLASK_DEBUG")), host="0.0.0.0", port=int(os.environ.get("PORT", 5050)))
