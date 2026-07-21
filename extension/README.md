# Depop ⇄ Vinted cross-lister — browser extension

Same thing the bookmarklets do, but as a one-click toolbar button — no
bookmarks bar needed. Click it while you're on your Depop shop page or your
Vinted closet page and it reads your listings into copy/paste-ready drafts
on the tool's site, exactly like the bookmarklet.

## Try it right now (unpacked — free, instant)

1. Open **chrome://extensions** in Chrome (or Edge: edge://extensions).
2. Turn on **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select this `extension/` folder.
4. A ⇄ button appears in your toolbar. Go to your Depop shop or Vinted
   closet page and click it.

This is enough to use it yourself and to share with friends (send them the
folder + these steps). It just isn't discoverable — that needs the store.

## Publish it to the Chrome Web Store (so anyone can install it)

This part needs a step only you can do:

1. Go to the [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
   and pay the **one-time $5 developer registration fee** (Google requires
   it; I can't do this for you).
2. Zip the contents of this `extension/` folder (the files, not the folder
   itself): `cd extension && zip -r ../extension.zip .`
3. In the dashboard: **Add new item** → upload the zip.
4. Fill in the listing (name, description, screenshots, a privacy note —
   "reads only your own public shop/closet pages, no login, no data sent to
   our server"), then submit for review. Review usually takes a few days.

Once approved it gets a public "Add to Chrome" link you can put on the site
and share.

## Keeping it in sync with the bookmarklets

`depop.js` and `vinted.js` are generated from the bookmarklet templates in
`../app.py` (`DEPOP_BOOKMARKLET_TEMPLATE` / `VINTED_BOOKMARKLET_TEMPLATE`),
with `__BASE_URL__` hardcoded to the production URL. If you change the
scraping logic in `app.py`, regenerate these two files so the extension
doesn't drift from the bookmarklets. `manifest.json` and `background.js`
are extension-only and don't change with the scraping logic.
