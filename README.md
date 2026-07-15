# Depop → Vinted draft assistant

A small Flask site that reads your active Depop listings and formats each one
as copy/paste-ready text (title, description, price, brand, size, condition)
plus photo links — so you can paste it into a new Vinted listing yourself.

**It does not touch Vinted at all, and it does not post anything to Depop.**
It's a formatter, not a bot.

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5050.

## Using it

1. Log into depop.com in your own browser.
2. Open DevTools → Network, click any request to depop.com, and copy the
   `Cookie` request header value.
3. Paste your Depop username and that cookie into the form.

The cookie is used for a single server-side request to Depop's own web API
and is never written to disk or logged.

## Why this design

- **No Vinted automation** — sidesteps Vinted's anti-bot/ToS concerns
  entirely by never logging into or writing to Vinted programmatically.
- **No stored credentials** — nothing here creates accounts or persists
  a login; each request brings its own cookie and it's discarded after.
- **Not hardened for public multi-tenant hosting** — this accepts an
  arbitrary cookie from whoever loads the page, so don't deploy it on the
  open internet without adding auth/rate-limiting in front of it. Running
  it locally, or sharing the repo for others to run locally themselves
  (like the original CLI tool), is the intended use.

## If Depop changes its API

`depop.py` hits an undocumented endpoint (`webapi.depop.com`). If listings
come back empty, open a Depop shop page, check DevTools → Network for the
`/shop/<user>/products/` request, and update the field names in
`depop.py::format_listing` to match. `test_depop.py` has a self-check you
can run after changing it: `python test_depop.py`.
