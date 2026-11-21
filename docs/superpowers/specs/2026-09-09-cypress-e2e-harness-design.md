# Cypress E2E harness + test-account seed — design

- **Date:** 2026-09-09
- **Status:** Approved (design), pending implementation plan
- **Author:** Mugisha Ivan Jalagatha

## 1. Context

`jango_mobileapp` is a Django 5.2 project (`backend/`) whose **storefront** app is a
server-rendered customer site: catalogue browsing, session cart, session auth
(register / login / logout), checkout, and a `/account/` area. It is deployed with
an ephemeral SQLite database (data resets on every deploy). The backend test suite is 236 Django tests, all green.

There is **no browser / end-to-end test layer** and **no Node toolchain** in the repo
(`node -v` → v24, `npm -v` → 11 are available on the dev machine; no `package.json`
anywhere). GitHub Actions is currently unusable on this private repo — every run,
including a minimal canonical workflow, fails with `startup_failure` (account-level
Actions billing block), so CI is out of scope for this work.

We want to:

1. Add a small, **isolated** Cypress harness that drives the live storefront in a real
   browser.
2. Use it to create a known test shopper account — phone **`0701588030`** (Django
   normalises to `+256701588030`) — on the live deployment, and then verify that
   account can log in and shop.

## 2. Goals

- One spec, runnable locally with `npm --prefix e2e run e2e` (headless) or
  `e2e:open` (interactive).
- The Node/Cypress footprint is confined to a top-level `e2e/` directory. **No change
  to any file under `backend/`.**
- `baseUrl` defaults to the local server, overridable via `CYPRESS_BASE_URL`.
- The spec is **idempotent**: first green run creates `+256701588030`; every later run
  confirms the account still logs in and the shopper journey still works, without
  failing on "account already exists".
- Tolerates a cold start (~1 min) on the first request.

## 3. Non-goals

- **CI integration.** Deferred until the GitHub Actions billing block is resolved. No
  workflow file is added.
- **`data-cy` / `data-testid` selector hooks in templates.** v1 uses the markup as it
  stands. Hardening selectors is a separate follow-up.
- **API-level tests** (`cy.request` against `/api/...`). This harness is UI-driven only.
- **Broader storefront coverage** (checkout, account-area CRUD, cart edits). Only the
  register → login → add-to-cart smoke path is in scope.
- Seeding the account through a Django management command or fixture. The point is to
  exercise the real register UI with Cypress.

## 4. Approach

**Chosen: pure UI-driven, no application changes** (approach A of three considered).

Cypress drives the real pages with resilient selectors — Django's default `#id_<field>`
ids on the auth forms, plus existing storefront markup hooks (`.product-card`,
`select[data-variant-select]`, `button[data-add-btn]`, `table.cart-table`,
`ul.messages`). This runs against the *current* live deployment with nothing to
redeploy first, and genuinely exercises the register/login/shop UI.

Rejected:

- **B — add `data-cy` hooks then test.** Cleaner selectors, but needs a template change
  + redeploy before the spec can pass against live. Slower to first green for a
  throwaway account.
- **C — hybrid `cy.request` for auth + UI for smoke.** Django's `{% csrf_token %}`
  forces a GET-then-scrape-`csrfmiddlewaretoken` dance per form; more code, more
  fragile, and skips the auth UI that is half the point.

## 5. Structure

```
e2e/
  package.json            # devDependency: cypress ^13. scripts: e2e, e2e:open
  cypress.config.js       # baseUrl, timeouts, retries, testIsolation
  cypress.env.json.example # committed; { "testPassword": "JanguTest2026!" }
  cypress.env.json        # local only, gitignored; overrides testPassword
  cypress/
    e2e/
      account-smoke.cy.js
    support/
      e2e.js              # imports ./commands
      commands.js         # cy.ensureLoggedOut(), cy.login(phone, password)
    fixtures/
      test-user.json      # { "phone": "0701588030", "firstName": "Jangu", "lastName": "Tester" }
```

Root `.gitignore` additions:

```
e2e/node_modules/
e2e/cypress/screenshots/
e2e/cypress/videos/
e2e/cypress.env.json
```

`cypress.env.json.example` is committed; the real `cypress.env.json` is local and
gitignored. If `testPassword` resolves to nothing, the spec falls back to the literal
`JanguTest2026!`.

## 6. Configuration — `cypress.config.js`

| Setting | Value | Reason |
|---|---|---|
| `e2e.baseUrl` | `process.env.CYPRESS_BASE_URL \|\| 'http://localhost:8000'` | Local server by default; overridable |
| `e2e.pageLoadTimeout` | `120000` | Absorb a cold start |
| `e2e.defaultCommandTimeout` | `15000` | Slack for a waking instance |
| `retries.runMode` | `2` | One flaky cold-start retry margin |
| `video` | `false` | Keep the harness light |
| `screenshotOnRunFailure` | `true` | Debugging a live-site failure |
| `e2e.testIsolation` | `false` | The three `it`s form one continuous session: register → same tab logs out/in → shops. Cypress 13 clears cookies between tests by default, which would drop the login before it (c). |

## 7. The spec — `account-smoke.cy.js`

A `before()` hook issues `cy.request({ url: '/api/schema/', timeout: 120000,
retryOnStatusCodeFailure: true })` once, so the cold start is paid before step (a).

Constants come from `cypress/fixtures/test-user.json` and
`Cypress.env('testPassword')`.

### it (a) — "registers +256701588030, or confirms it already exists"

1. `cy.visit('/register/')`.
2. Fill `#id_phone` = `0701588030`, `#id_first_name` = `Jangu`,
   `#id_last_name` = `Tester`, `#id_password1` = password, `#id_password2` = password.
3. Submit (`button[type=submit]`, label "Create account").
4. Branch on the resulting page:
   - **URL no longer `/register/`** and header contains a logout control
     (`form[action*="logout"]`) → account created. Pass.
   - **URL still `/register/`** and `.errorlist` text matches `/already exists/i` →
     seeded on a previous run. Log `cy.log('account already present')`. Pass.
   - Otherwise → `throw` with `cy.get('.errorlist').text()` (or the page body) in the
     message. Fail.

### it (b) — "logs in with the seeded credentials"

1. `cy.ensureLoggedOut()`.
2. `cy.login('0701588030', password)` — visits `/login/`, fills `#id_username` and
   `#id_password`, submits ("Log in").
3. Assert `cy.location('pathname').should('not.eq', '/login/')`.
4. Assert header shows a logout control and the account link text contains `Jangu`.

### it (c) — "completes a shopper smoke journey while logged in"

With `testIsolation: false` the login from it (b) is still active. it (c) opens with a
cheap re-assertion that a logout control is present (and calls `cy.login(...)` only if
it is not, e.g. when the spec is run with `--spec` filtering to this test alone).

1. Confirm logged in, or `cy.login(...)` if not.
2. `cy.visit('/')`. Within `.product-grid`, pick the first `a.product-card` whose
   subtree has no `.oos` element; `click()`.
3. On the product page: `cy.get('body').then($b => …)` — if
   `select[data-variant-select]` exists, `select` the first `option[data-in-stock="1"]`
   by value. Leave `input[name="quantity"]` at `1`.
4. `cy.get('button[data-add-btn]').click()`.
5. Assert `cy.location('pathname').should('eq', '/cart/')`,
   `ul.messages` contains `/added/i`, and `table.cart-table tbody tr` has length ≥ 1.

## 8. Custom commands — `cypress/support/commands.js`

- **`cy.ensureLoggedOut()`** — `cy.visit('/')`, then
  `cy.get('body').then($b => { if ($b.find('form[action*="logout"]').length)
  cy.get('form[action*="logout"]').first().submit(); })`. Safe when already anonymous.
- **`cy.login(phone, password)`** — `cy.visit('/login/')`, fill `#id_username` /
  `#id_password`, submit; no assertion inside (callers assert).

Django's hidden `{% csrf_token %}` input is submitted automatically because the commands
drive the real form elements — no token handling needed.

## 9. Data flow

```
npm run e2e
  └─ cypress run  (baseUrl = target site)
       before(): GET /api/schema/  ── wakes the instance
       it (a):  POST /register/    ── creates +256701588030 in the live SQLite DB
                                        (or detects the duplicate-phone error)
       it (b):  POST /logout/, POST /login/  ── session cookie proves credentials
       it (c):  GET /, GET /p/<slug>/, POST /cart/add/, GET /cart/
                                        ── session cart, message assertion
```

The only persistent side effect is the `User` row for `+256701588030`. It survives
until the next deploy wipes the ephemeral database, after which the next run
re-creates it (step (a)'s create branch).

## 10. Error handling

| Situation | Behaviour |
|---|---|
| Cold start | `before()` warm-up + 120 s `pageLoadTimeout`; `runMode` retry ×2 |
| Account already exists | it (a) detects `/already exists/i` in `.errorlist` and passes |
| Password fails Django validators | it (a) falls to the `throw` branch with the validator text — surfaces immediately |
| First product is out of stock | Selection skips any card containing `.oos` |
| Product has variants | it (c) selects the first `option[data-in-stock="1"]` before add |
| Storefront markup changed | Spec fails on a missing selector; documented fragility (§3), fix is a `data-cy` follow-up |

## 11. Testing the harness itself

Manual acceptance, run from `e2e/`:

1. `npm install` — Cypress downloads, `npx cypress verify` passes.
2. `npm run e2e` against the default (live) base URL — all three `it`s pass; the
   account is created on first run.
3. Re-run `npm run e2e` — still green; it (a) now takes the "already exists" branch.
4. `CYPRESS_BASE_URL=http://localhost:8000 npm run e2e` against a local
   `python manage.py runserver` — passes, proving the base URL override.

No Django-side tests change; `python manage.py test` stays at 236 green.

## 12. Follow-ups (out of scope)

- Add `data-cy` attributes to storefront templates and switch the spec to them.
- Wire `npm run e2e` into CI once the GitHub Actions billing block is lifted.
- Expand coverage: checkout + payment sim, `/account/` order history and address book.
- Point the harness at a persistent database (Neon) so the seeded account survives
  deploys.
