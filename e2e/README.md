# Jangu storefront — Cypress E2E

UI-driven end-to-end harness. Drives the storefront in a real browser. It
targets a local Django server by default.

## Setup

    cd e2e
    npm install
    cp cypress.env.json.example cypress.env.json   # optional: override testPassword

## Run

    npm run e2e         # headless, against http://localhost:8000
    npm run e2e:open    # interactive runner

Target another environment with CYPRESS_BASE_URL:

    CYPRESS_BASE_URL=https://<deployed-host> npm run e2e

## account-smoke.cy.js

1. Registers the shopper `0701588030` / `JanguTest2026!` (or confirms it already
   exists — the spec is re-runnable).
2. Logs out, then logs back in with those credentials.
3. While logged in: opens the first in-stock product, adds it to the cart, and
   asserts the cart shows the line.

The first green run creates the account on the target database.

## featured-grid.cy.js

Checks that Featured Products on the home page shows only complete rows at six
screen widths. The target site needs at least 10 in-stock products with images.
It only reads pages, so it creates no data.

## page-width.cy.js

Checks that the main pages do not scroll sideways at phone and tablet widths. It only
reads pages, so it creates no data.

## CI

`.github/workflows/ci.yml` runs these specs on every push to `main` and every pull
request, against a throwaway database, along with the backend tests.
