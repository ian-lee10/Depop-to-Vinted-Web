import json
import os
import time
from collections import defaultdict, deque

from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from listings import parse_shop_response

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


# Both bookmarklets below run in the user's own browser while they're
# already on their shop/closet page, not on this server. Neither Depop nor
# Vinted's per-seller listing grid can be read with a plain server-side
# request:
#   - Depop's Cloudflare bot management blocks server-to-server requests to
#     webapi.depop.com regardless of cookie validity (confirmed: the block
#     is a Cloudflare bot-management page, not an app-level error), and
#     that same API has no CORS allowance for browser-side calls either
#     (confirmed via a live console error).
#   - Vinted's closet/listing grid is rendered client-side only - a plain
#     fetch() of the profile URL returns 0 item links (confirmed).
# So both bookmarklets read the grid from the already-rendered live DOM
# (scrolling first, since both lazy-load more items as you scroll), then do
# same-origin fetch()es - no CORS involved, same origin as the page - to
# each item's own page and parse out the draft fields. Both build objects
# shaped for parse_shop_response()/format_listing() in listings.py, so that
# pipeline is shared and doesn't care which marketplace the data came from.
DEPOP_BOOKMARKLET_TEMPLATE = """(function(){
function extractFromDoc(doc, href){
var priceNode = Array.from(doc.querySelectorAll('*')).find(function(el){return el.children.length===0 && /^[$\\u00a3\\u20ac]\\d/.test((el.textContent||'').trim());});
var priceText = priceNode ? priceNode.textContent.trim() : '';
var sym = priceText[0] || '$';
var currency = sym==='\\u00a3' ? 'GBP' : sym==='\\u20ac' ? 'EUR' : 'USD';
var amount = parseFloat(priceText.replace(/[^0-9.]/g,'')) || 0;
var descNode = doc.querySelector('p[class*="textWrapper"]');
var h1 = doc.querySelector('h1');
var description = descNode ? descNode.textContent.trim() : (h1 ? h1.textContent.trim() : '');
var brandLink = doc.querySelector('a[class*="linkAttribute"]');
var brand = brandLink ? brandLink.textContent.trim() : '';
var sizeMatch = description.match(/\\bsize\\s*:?\\s*(extra\\s*small|extra\\s*large|xxs|xs|small|medium|large|xxl|xl|s|m|l)\\b/i);
var size = sizeMatch ? sizeMatch[1].trim() : '';
var imgs = Array.from(doc.querySelectorAll('img[src*="media-photos.depop.com"]'));
var photos = priceNode
  ? [].concat.apply([], [imgs.filter(function(img){return (img.compareDocumentPosition(priceNode) & Node.DOCUMENT_POSITION_FOLLOWING);})]).map(function(i){return i.src;})
  : imgs.slice(0,1).map(function(i){return i.src;});
photos = photos.filter(function(u){return /\\/P\\d+\\.(jpg|jpeg|png|webp)/i.test(u);});
photos = photos.filter(function(u, idx){return photos.indexOf(u)===idx;});
var slug = (href.match(/\\/products\\/([^/]+)\\//)||[])[1] || '';
if(!priceNode && !description){ return null; }
return {slug:slug, description:description, price:{priceAmount:amount, currencyIsoCode:currency}, brand:{name:brand}, size:size, condition:'', pictures:photos.map(function(u){return {originalUrl:u};})};
}
function collectHrefs(){
var links = Array.from(document.querySelectorAll('a[href*="/products/"]'));
var seen = {}; var hrefs = [];
links.forEach(function(a){var h=a.getAttribute('href'); if(h && !seen[h]){seen[h]=1; hrefs.push(h);}});
return hrefs;
}
var MAX_ITEMS = 300, MAX_SCROLL_ITERS = 60;
function autoScrollThenRun(){
var iters = 0, lastCount = -1, stableChecks = 0;
(function step(){
var count = collectHrefs().length;
if(count === lastCount) stableChecks++; else stableChecks = 0;
lastCount = count;
iters++;
if(stableChecks >= 2 || iters >= MAX_SCROLL_ITERS || count >= MAX_ITEMS){ runExtraction(); return; }
window.scrollTo(0, document.body.scrollHeight);
setTimeout(step, 700);
})();
}
function fetchOneAtATime(hrefs, extractor){
var results = [];
function next(idx){
if(idx >= hrefs.length){ return Promise.resolve(results); }
return fetch(hrefs[idx]).then(function(r){return r.text();}).then(function(html){
return extractor(new DOMParser().parseFromString(html,'text/html'), hrefs[idx]);
}).catch(function(){ return null; }).then(function(item){
results.push(item);
return new Promise(function(res){ setTimeout(res, 250); });
}).then(function(){ return next(idx+1); });
}
return next(0);
}
function runExtraction(){
var hrefs = collectHrefs().slice(0, MAX_ITEMS);
if(hrefs.length===0){alert('Depop to Vinted: go to your shop page (depop.com/yourusername) first, then click this bookmark.'); return;}
var m = location.pathname.match(/^\\/([A-Za-z0-9_.-]+)\\/?$/);
var username = m ? m[1] : (prompt('Your Depop username?') || 'your-shop');
fetchOneAtATime(hrefs, extractFromDoc).then(function(raw){
var items = raw.filter(Boolean);
if(items.length===0){
alert('Depop to Vinted: could not read any listings - either Depop rate-limited these requests (try again in a minute or two) or the page layout changed.');
return;
}
if(items.length < raw.length / 2){
alert('Depop to Vinted: only got '+items.length+' of '+raw.length+' listings - Depop likely rate-limited some requests. Showing what came through; try again shortly for the rest.');
}
var f=document.createElement('form');
f.method='POST';f.action='__BASE_URL__from-browser';
var i=document.createElement('input');i.type='hidden';i.name='data';i.value=JSON.stringify({products:items});f.appendChild(i);
var j=document.createElement('input');j.type='hidden';j.name='username';j.value=username;f.appendChild(j);
var k=document.createElement('input');k.type='hidden';k.name='target';k.value='vinted';f.appendChild(k);
document.body.appendChild(f);f.submit();
}).catch(function(e){alert('Depop to Vinted: '+e.message);});
}
autoScrollThenRun();
})();"""

VINTED_BOOKMARKLET_TEMPLATE = """(function(){
function extractFromDoc(doc, href){
var ldEl = doc.querySelector('script[type="application/ld+json"]');
if(!ldEl){ return null; }
var ld = {};
try { ld = JSON.parse(ldEl.textContent); } catch(e) { return null; }
var name = ld.name || '';
var descText = ld.description || '';
var description = name + (descText ? ('\\n' + descText) : '');
var offers = ld.offers || {};
var brand = (ld.brand && ld.brand.name) || '';
var sizeEl = doc.querySelector('[data-testid="item-attributes-size"] [itemprop="size"]');
var size = sizeEl ? sizeEl.textContent.trim() : '';
var statusEl = doc.querySelector('[data-testid="item-attributes-status"] [itemprop="status"]');
var condition = statusEl ? statusEl.textContent.trim() : '';
var imgs = Array.from(doc.querySelectorAll('img[src*="vinted.net"]')).filter(function(img){
var a = img.closest('a');
return !(a && /\\/member\\//.test(a.getAttribute('href')||''));
});
var photos = imgs.map(function(i){return i.src;});
photos = photos.filter(function(u, idx){return photos.indexOf(u)===idx;});
var url = href.indexOf('http')===0 ? href : (location.origin + href);
return {url:url, description:description, price:{priceAmount:(offers.price||0), currencyIsoCode:(offers.priceCurrency||'USD')}, brand:{name:brand}, size:size, condition:condition, pictures:photos.map(function(u){return {originalUrl:u};})};
}
function collectHrefs(){
var links = Array.from(document.querySelectorAll('a[href*="/items/"]'));
var seen = {}; var hrefs = [];
links.forEach(function(a){var h=a.getAttribute('href'); if(h && !seen[h]){seen[h]=1; hrefs.push(h);}});
return hrefs;
}
var MAX_ITEMS = 300, MAX_SCROLL_ITERS = 60;
function autoScrollThenRun(){
var iters = 0, lastCount = -1, stableChecks = 0;
(function step(){
var count = collectHrefs().length;
if(count === lastCount) stableChecks++; else stableChecks = 0;
lastCount = count;
iters++;
if(stableChecks >= 2 || iters >= MAX_SCROLL_ITERS || count >= MAX_ITEMS){ runExtraction(); return; }
window.scrollTo(0, document.body.scrollHeight);
setTimeout(step, 700);
})();
}
function fetchOneAtATime(hrefs, extractor){
var results = [];
function next(idx){
if(idx >= hrefs.length){ return Promise.resolve(results); }
return fetch(hrefs[idx]).then(function(r){return r.text();}).then(function(html){
return extractor(new DOMParser().parseFromString(html,'text/html'), hrefs[idx]);
}).catch(function(){ return null; }).then(function(item){
results.push(item);
return new Promise(function(res){ setTimeout(res, 250); });
}).then(function(){ return next(idx+1); });
}
return next(0);
}
function runExtraction(){
var hrefs = collectHrefs().slice(0, MAX_ITEMS);
if(hrefs.length===0){alert('Vinted to Depop: go to your closet page (your Vinted profile) first, then click this bookmark.'); return;}
var h1 = document.querySelector('h1');
var username = h1 ? h1.textContent.trim() : 'your-closet';
fetchOneAtATime(hrefs, extractFromDoc).then(function(raw){
var items = raw.filter(Boolean);
if(items.length===0){
alert('Vinted to Depop: could not read any listings - either Vinted rate-limited these requests (try again in a minute or two) or the page layout changed.');
return;
}
if(items.length < raw.length / 2){
alert('Vinted to Depop: only got '+items.length+' of '+raw.length+' listings - Vinted likely rate-limited some requests. Showing what came through; try again shortly for the rest.');
}
var f=document.createElement('form');
f.method='POST';f.action='__BASE_URL__from-browser';
var i=document.createElement('input');i.type='hidden';i.name='data';i.value=JSON.stringify({products:items});f.appendChild(i);
var j=document.createElement('input');j.type='hidden';j.name='username';j.value=username;f.appendChild(j);
var k=document.createElement('input');k.type='hidden';k.name='target';k.value='depop';f.appendChild(k);
document.body.appendChild(f);f.submit();
}).catch(function(e){alert('Vinted to Depop: '+e.message);});
}
autoScrollThenRun();
})();"""


@app.route("/")
def index():
    depop_bookmarklet = "javascript:" + DEPOP_BOOKMARKLET_TEMPLATE.replace("__BASE_URL__", request.url_root).replace("\n", " ")
    vinted_bookmarklet = "javascript:" + VINTED_BOOKMARKLET_TEMPLATE.replace("__BASE_URL__", request.url_root).replace("\n", " ")
    return render_template("index.html", depop_bookmarklet=depop_bookmarklet, vinted_bookmarklet=vinted_bookmarklet)


@app.route("/from-browser", methods=["POST"])
def from_browser():
    if _rate_limited(_client_ip()):
        return render_template("index.html", error="Too many requests from your IP - try again in a bit."), 429

    username = request.form.get("username", "").strip()
    target = request.form.get("target", "vinted").strip().lower()
    if target not in ("vinted", "depop"):
        target = "vinted"
    raw = request.form.get("data", "")
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return render_template("index.html", error="Couldn't read the data the bookmarklet sent - try clicking it again."), 400

    items = parse_shop_response(payload)
    return render_template("listings.html", items=items, username=username, target=target)


if __name__ == "__main__":
    app.run(debug=bool(os.environ.get("FLASK_DEBUG")), host="0.0.0.0", port=int(os.environ.get("PORT", 5050)))
