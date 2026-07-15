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


# Runs in the user's own browser (from a bookmarklet) while they're already
# on their Depop shop page, not on this server. Two things forced this
# design rather than a single API call:
#   1. Depop's Cloudflare bot management blocks server-to-server requests
#      to webapi.depop.com regardless of cookie validity (confirmed: the
#      block is a Cloudflare bot-management page, not an app-level error).
#   2. webapi.depop.com also has no CORS allowance for cross-origin fetches
#      from www.depop.com (confirmed via a live console error), so even a
#      real browser can't call that API directly from a depop.com page.
# Instead, this scrapes the shop grid (product links + prices) already
# rendered on the page, then does same-origin fetch()es (no CORS involved
# at all - same depop.com origin) to each product's own page HTML and
# parses out title/description/brand/price/photos with DOMParser. It
# builds objects shaped like Depop's old API response so the existing
# parse_shop_response()/format_listing() pipeline needs no changes.
BOOKMARKLET_TEMPLATE = """(function(){
function extractFromDoc(doc, href){
var priceNode = Array.from(doc.querySelectorAll('*')).find(function(el){return el.children.length===0 && /^[$\\u00a3\\u20ac]\\d/.test((el.textContent||'').trim());});
var priceText = priceNode ? priceNode.textContent.trim() : '';
var sym = priceText[0] || '$';
var currency = sym==='\\u00a3' ? 'GBP' : sym==='\\u20ac' ? 'EUR' : 'USD';
var amount = parseFloat(priceText.replace(/[^0-9.]/g,'')) || 0;
var descNode = doc.querySelector('p[class*="textWrapper"]');
var h1 = doc.querySelector('h1');
var description = descNode ? descNode.textContent.trim() : (h1 ? h1.textContent.trim() : '');
var brandLink = doc.querySelector('a[class*="linkAttribute"]') || doc.querySelectorAll('a[class*="breadcrumbLink"]')[1];
var brand = brandLink ? brandLink.textContent.trim() : '';
var imgs = Array.from(doc.querySelectorAll('img[src*="media-photos.depop.com"]'));
var photos = priceNode
  ? [].concat.apply([], [imgs.filter(function(img){return (img.compareDocumentPosition(priceNode) & Node.DOCUMENT_POSITION_FOLLOWING);})]).map(function(i){return i.src;})
  : imgs.slice(0,1).map(function(i){return i.src;});
photos = photos.filter(function(u){return /\\/P\\d+\\.(jpg|jpeg|png|webp)/i.test(u);});
photos = photos.filter(function(u, idx){return photos.indexOf(u)===idx;});
var slug = (href.match(/\\/products\\/([^/]+)\\//)||[])[1] || '';
return {slug:slug, description:description, price:{priceAmount:amount, currencyIsoCode:currency}, brand:{name:brand}, size:'', condition:'', pictures:photos.map(function(u){return {originalUrl:u};})};
}
var links = Array.from(document.querySelectorAll('a[href*="/products/"]'));
var seen = {}; var hrefs = [];
links.forEach(function(a){var h=a.getAttribute('href'); if(h && !seen[h]){seen[h]=1; hrefs.push(h);}});
hrefs = hrefs.slice(0, 40);
if(hrefs.length===0){alert('Depop to Vinted: go to your shop page (depop.com/yourusername) first, then click this bookmark.'); return;}
var m = location.pathname.match(/^\\/([A-Za-z0-9_.-]+)\\/?$/);
var username = m ? m[1] : (prompt('Your Depop username?') || 'your-shop');
Promise.all(hrefs.map(function(href){
return fetch(href).then(function(r){return r.text();}).then(function(html){return extractFromDoc(new DOMParser().parseFromString(html,'text/html'), href);}).catch(function(){return null;});
})).then(function(items){
items = items.filter(Boolean);
if(items.length===0){alert('Depop to Vinted: could not read any listings - Depop may have changed their page layout.'); return;}
var f=document.createElement('form');
f.method='POST';f.action='__BASE_URL__from-browser';
var i=document.createElement('input');i.type='hidden';i.name='data';i.value=JSON.stringify({products:items});f.appendChild(i);
var j=document.createElement('input');j.type='hidden';j.name='username';j.value=username;f.appendChild(j);
document.body.appendChild(f);f.submit();
}).catch(function(e){alert('Depop to Vinted: '+e.message);});
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
