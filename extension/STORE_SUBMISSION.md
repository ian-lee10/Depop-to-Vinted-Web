# Publishing to the Chrome Web Store — everything's prepped

Everything the store asks for is ready in this folder. You do the account +
upload; the copy below is paste-ready.

**Already prepared for you (all in this folder):**
- `../extension.zip` — the exact package to upload.
- `icon128.png` — the store icon (128×128).
- `store-assets/1-results.png`, `store-assets/2-landing.png` — 1280×800
  screenshots (the store requires at least one; these two are enough).
- `store-assets/promo-small-440x280.png` — small promo tile (440×280).
- `store-assets/promo-marquee-1400x560.png` — marquee promo tile (1400×560).
- Privacy policy URL (required for these permissions):
  **https://crosslister.onrender.com/privacy**

## Listing page — every field, paste-ready

| Field | Value |
|---|---|
| **Store icon** | `icon128.png` (128×128) |
| **Category** | Shopping |
| **Language** | English (United States) |
| **Screenshots** | `store-assets/1-results.png`, `store-assets/2-landing.png` (1280×800) |
| **Small promo tile** | `store-assets/promo-small-440x280.png` |
| **Marquee promo tile** | `store-assets/promo-marquee-1400x560.png` |
| **Homepage URL** | https://crosslister.onrender.com |
| **Support URL** | https://github.com/ian-lee10/Depop-to-Vinted-Web/issues |
| **Official URL** | Leave blank — it requires verifying ownership of the domain in Google Search Console, and `onrender.com` isn't a domain you can verify. Optional field; skip it. |

"Global assets" in the dashboard is just the umbrella section that holds the
store icon + screenshots + promo tiles above — nothing separate to add.

## Steps

1. Go to the **[Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)**
   and sign in with the Google account you want to own the extension.
2. Pay the **one-time $5 registration fee** (Google requires it — I can't do
   this for you). You may also need to verify your identity/contact email.
3. Click **Add new item** and upload **`extension.zip`**.
4. Fill in the listing using the paste-ready text below.
5. Upload the two screenshots from `store-assets/`.
6. Complete the **Privacy** tab (answers below) and add the privacy policy URL.
7. **Submit for review.** Review typically takes a few days. Once approved you
   get a public page with an **Add to Chrome** button — put that link on the
   site and share it.

---

## Paste-ready listing text

**Name**
```
Depop ⇄ Vinted cross-lister
```

**Summary** (short description, max 132 chars)
```
One click turns your Depop shop or Vinted closet into copy/paste-ready drafts for the other site. No login, no automation.
```

**Detailed description**
```
Cross-listing the same items on Depop and Vinted means re-typing everything twice. This does the boring part.

Click the toolbar button while you're on your own Depop shop page or Vinted closet page. It reads every one of your listings and opens a tab that fills in live — each listing's photos, description, price, brand, size, and condition — formatted for the other marketplace, with a copy button next to every field so you can drop each straight into the new listing form.

• Works both directions: Depop → Vinted and Vinted → Depop
• No login, no password, no cookies — it only reads pages you're already viewing
• Nothing is posted or changed on either site; you review and publish yourself
• Nothing is sent to any server — it all runs in your own browser

It only runs on depop.com and vinted.com, and only when you click it.
```

**Category:** Shopping
**Language:** English

---

## Privacy tab answers

**Single purpose**
```
Reads the user's own Depop shop or Vinted closet listings that are already displayed on the page and formats them into copy/paste-ready drafts for the other marketplace.
```

**Permission justifications**
- `host_permissions` (depop.com, vinted.com):
  ```
  The extension only functions on the user's own Depop shop and Vinted closet pages. It needs to read the listing data rendered on those pages to format it for the other marketplace. It does nothing on any other site.
  ```
- `scripting`:
  ```
  Used to run the read-and-format script on the current shop/closet tab when the user clicks the toolbar button.
  ```

**Remote code:** No — all code is included in the package.

**Data usage:** Check that the extension does **not** collect or use any user
data. It processes listing data locally in the browser and sends nothing to any
server. (Do not check any of the "collects" boxes.)

**Privacy policy URL:**
```
https://crosslister.onrender.com/privacy
```
