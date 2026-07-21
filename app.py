import os

from flask import Flask, render_template, request

app = Flask(__name__)

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
# each item's own page and parse out the draft fields.
#
# As each item is read, it's posted via postMessage to a window opened
# synchronously at the very start (a direct response to the click, so popup
# blockers allow it) - that window (see /progress) renders each draft live
# as it arrives, with a working copy button, and never needs a server round
# trip: everything after the initial page load is pure client-side
# rendering of data the bookmarklet already extracted.
#
# NOTE: the browser extension in extension/ ships copies of these two script
# bodies (extension/depop.js, extension/vinted.js) with __BASE_URL__ hard-
# coded to the production URL. If you change the scraping logic here,
# regenerate those two files (see extension/README.md) so they don't drift.
DEPOP_BOOKMARKLET_TEMPLATE = """(function(){
var __m = location.pathname.match(/^\\/([A-Za-z0-9_.-]+)\\/?$/);
var username = __m ? __m[1] : (prompt('Your Depop username?') || 'your-shop');
var progressWin = window.open('__BASE_URL__progress?target=vinted&username='+encodeURIComponent(username), 'depopVintedResults');
var targetOrigin = '__BASE_URL__'.slice(0, -1);
function notify(msg){ if(progressWin){ try{ progressWin.postMessage(msg, targetOrigin); }catch(e){} } }
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
return {url:(location.origin+href), description:description, price:amount, currency:currency, brand:brand, size:size, condition:'', photos:photos};
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
if(stableChecks >= 3 || iters >= MAX_SCROLL_ITERS || count >= MAX_ITEMS){ runExtraction(); return; }
window.scrollTo(0, document.body.scrollHeight);
setTimeout(step, 1000);
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
notify({type:'progress', done:idx+1, total:hrefs.length, username:username});
if(item){ notify({type:'item', item:item}); }
return new Promise(function(res){ setTimeout(res, 250); });
}).then(function(){ return next(idx+1); });
}
return next(0);
}
function runExtraction(){
var hrefs = collectHrefs().slice(0, MAX_ITEMS);
if(hrefs.length===0){alert('Depop to Vinted: go to your shop page (depop.com/yourusername) first, then click this bookmark.'); return;}
notify({type:'progress', done:0, total:hrefs.length, username:username});
fetchOneAtATime(hrefs, extractFromDoc).then(function(raw){
var items = raw.filter(Boolean);
if(items.length < raw.length && items.length < raw.length / 2){
alert('Depop to Vinted: only got '+items.length+' of '+raw.length+' listings - Depop likely rate-limited some requests. Showing what came through; try again shortly for the rest.');
}
notify({type:'done', username:username});
}).catch(function(e){alert('Depop to Vinted: '+e.message);});
}
autoScrollThenRun();
})();"""

VINTED_BOOKMARKLET_TEMPLATE = """(function(){
var __h1 = document.querySelector('h1');
var username = __h1 ? __h1.textContent.trim() : 'your-closet';
var __userMatch = location.pathname.match(/^\\/member\\/(\\d+)/);
var userId = __userMatch ? __userMatch[1] : null;
var progressWin = window.open('__BASE_URL__progress?target=depop&username='+encodeURIComponent(username), 'depopVintedResults');
var targetOrigin = '__BASE_URL__'.slice(0, -1);
function notify(msg){ if(progressWin){ try{ progressWin.postMessage(msg, targetOrigin); }catch(e){} } }
if(!userId){ alert('Vinted to Depop: go to your closet page (your Vinted profile) first, then click this bookmark.'); return; }

function fetchAllWardrobePages(){
var perPage = 50, all = [];
function loadPage(page){
return fetch('/api/v2/wardrobe/'+userId+'/items?page='+page+'&per_page='+perPage+'&order=relevance')
.then(function(r){
if(!r.ok){ throw new Error('wardrobe API HTTP '+r.status); }
return r.json();
})
.then(function(data){
var items = (data && data.items) || [];
all = all.concat(items);
if(items.length >= perPage){ return loadPage(page+1); }
return all;
});
}
return loadPage(1);
}
function fetchDescription(url){
return fetch(url).then(function(r){return r.text();}).then(function(html){
var doc = new DOMParser().parseFromString(html, 'text/html');
var ldEl = doc.querySelector('script[type="application/ld+json"]');
if(!ldEl){ return null; }
try { return JSON.parse(ldEl.textContent).description || null; } catch(e) { return null; }
}).catch(function(){ return null; });
}
function toDraftItem(wardrobeItem, fullDescription){
var price = wardrobeItem.price || {};
var photos = (wardrobeItem.photos || []).map(function(p){ return p.url; });
var title = wardrobeItem.title || '';
return {
url: wardrobeItem.url,
description: title + (fullDescription ? ('\\n' + fullDescription) : ''),
price: parseFloat(price.amount) || 0,
currency: price.currency_code || 'USD',
brand: wardrobeItem.brand || '',
size: wardrobeItem.size || '',
condition: wardrobeItem.status || '',
photos: photos
};
}
function enrichOneAtATime(wardrobeItems){
var results = [];
function next(idx){
if(idx >= wardrobeItems.length){ return Promise.resolve(results); }
var w = wardrobeItems[idx];
return fetchDescription(w.url).then(function(desc){
var item = toDraftItem(w, desc);
results.push(item);
notify({type:'progress', done:idx+1, total:wardrobeItems.length, username:username});
notify({type:'item', item:item});
return new Promise(function(res){ setTimeout(res, 250); });
}).then(function(){ return next(idx+1); });
}
return next(0);
}
function runViaWardrobeApi(){
return fetchAllWardrobePages().then(function(wardrobeItems){
if(wardrobeItems.length===0){ throw new Error('wardrobe API returned no items'); }
return enrichOneAtATime(wardrobeItems);
});
}

function extractFromItemPage(doc, href){
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
var isMemberLink = a && /\\/member\\//.test(a.getAttribute('href')||'');
var w = parseInt(img.getAttribute('width')||'0', 10);
var h = parseInt(img.getAttribute('height')||'0', 10);
var isAvatarSized = (w && w <= 120) || (h && h <= 120);
return !isMemberLink && !isAvatarSized;
});
var photos = imgs.map(function(i){return i.src;});
photos = photos.filter(function(u, idx){return photos.indexOf(u)===idx;});
var url = href.indexOf('http')===0 ? href : (location.origin + href);
return {url:url, description:description, price:(offers.price||0), currency:(offers.priceCurrency||'USD'), brand:brand, size:size, condition:condition, photos:photos};
}
function collectHrefsFromDOM(){
var links = Array.from(document.querySelectorAll('a[href*="/items/"]'));
var seen = {}; var hrefs = [];
links.forEach(function(a){var h=a.getAttribute('href'); if(h && !seen[h]){seen[h]=1; hrefs.push(h);}});
return hrefs;
}
var MAX_ITEMS = 300, MAX_SCROLL_ITERS = 60;
function autoScrollThenCollect(){
return new Promise(function(resolve){
var iters = 0, lastCount = -1, stableChecks = 0;
(function step(){
var count = collectHrefsFromDOM().length;
if(count === lastCount) stableChecks++; else stableChecks = 0;
lastCount = count;
iters++;
if(stableChecks >= 3 || iters >= MAX_SCROLL_ITERS || count >= MAX_ITEMS){ resolve(collectHrefsFromDOM().slice(0, MAX_ITEMS)); return; }
window.scrollTo(0, document.body.scrollHeight);
setTimeout(step, 1000);
})();
});
}
function fetchItemsOneAtATime(hrefs){
var results = [];
function next(idx){
if(idx >= hrefs.length){ return Promise.resolve(results); }
return fetch(hrefs[idx]).then(function(r){return r.text();}).then(function(html){
return extractFromItemPage(new DOMParser().parseFromString(html,'text/html'), hrefs[idx]);
}).catch(function(){ return null; }).then(function(item){
results.push(item);
notify({type:'progress', done:idx+1, total:hrefs.length, username:username});
if(item){ notify({type:'item', item:item}); }
return new Promise(function(res){ setTimeout(res, 250); });
}).then(function(){ return next(idx+1); });
}
return next(0);
}
function runViaDomScraping(){
notify({type:'progress', done:0, total:0, username:username});
return autoScrollThenCollect().then(function(hrefs){
if(hrefs.length===0){ throw new Error('no listings found - is this your closet page?'); }
notify({type:'progress', done:0, total:hrefs.length, username:username});
return fetchItemsOneAtATime(hrefs).then(function(raw){
var items = raw.filter(Boolean);
if(items.length===0){ throw new Error('could not read any listings - Vinted may have changed its page layout'); }
});
});
}

notify({type:'progress', done:0, total:0, username:username});
runViaWardrobeApi().catch(function(apiErr){
return runViaDomScraping();
}).then(function(){
notify({type:'done', username:username});
}).catch(function(e){alert('Vinted to Depop: '+e.message);});
})();"""


@app.route("/")
def index():
    depop_bookmarklet = "javascript:" + DEPOP_BOOKMARKLET_TEMPLATE.replace("__BASE_URL__", request.url_root).replace("\n", " ")
    vinted_bookmarklet = "javascript:" + VINTED_BOOKMARKLET_TEMPLATE.replace("__BASE_URL__", request.url_root).replace("\n", " ")
    # Set CHROME_STORE_URL in the environment once the extension is approved -
    # the "Add to Chrome" button flips from "coming soon" to a live link, no
    # code change needed (just a Render env var + restart).
    chrome_store_url = os.environ.get("CHROME_STORE_URL", "").strip()
    return render_template(
        "index.html",
        depop_bookmarklet=depop_bookmarklet,
        vinted_bookmarklet=vinted_bookmarklet,
        chrome_store_url=chrome_store_url,
    )


@app.route("/progress")
def progress():
    target = request.args.get("target", "vinted").strip().lower()
    if target not in ("vinted", "depop"):
        target = "vinted"
    username = request.args.get("username", "").strip()
    return render_template("progress.html", target=target, username=username)


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


if __name__ == "__main__":
    app.run(debug=bool(os.environ.get("FLASK_DEBUG")), host="0.0.0.0", port=int(os.environ.get("PORT", 5050)))
