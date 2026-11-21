const user = require("../fixtures/test-user.json");
const password = Cypress.env("testPassword") || "JanguTest2026!";

describe("Storefront account: seed + verify +256701588030", () => {
  before(() => {
    // Fail fast if the server is down; a non-200 here fails the whole spec.
    cy.request("/").its("status").should("eq", 200);
  });

  it("registers +256701588030, or confirms it already exists", () => {
    cy.visit("/register/");
    cy.get("#id_phone").clear().type(user.phone);
    cy.get("#id_first_name").clear().type(user.firstName);
    cy.get("#id_last_name").clear().type(user.lastName);
    cy.get("#id_password1").clear().type(password, { log: false });
    cy.get("#id_password2").clear().type(password, { log: false });
    cy.get('form[method="post"] button[type="submit"]').click();

    cy.location("pathname").then((pathname) => {
      if (pathname !== "/register/") {
        // Redirected away -> account created and auto-logged-in.
        cy.get('form[action*="logout"]').should("exist");
        return;
      }
      // Still on /register/ -- the only acceptable reason is a duplicate phone.
      cy.get("body").then(($body) => {
        const errText = $body.find(".errorlist").text();
        expect(
          errText || $body.text(),
          "register did not redirect; expected a duplicate-phone error"
        ).to.match(/already exists/i);
        cy.log("account +256701588030 already present -- skipping creation");
      });
    });
  });

  it("logs in with the seeded credentials", () => {
    cy.ensureLoggedOut();
    cy.login(user.phone, password);
    cy.location("pathname").should("not.eq", "/login/");
    cy.get('form[action*="logout"]').should("exist");
    cy.get(".site-header .header-actions").should("contain.text", user.firstName);
  });

  it("completes a shopper smoke journey while logged in", () => {
    // testIsolation:false keeps the login from the previous test. Re-login only
    // if this spec is run in isolation (e.g. with --spec on this file alone and
    // Cypress starting mid-describe on a retry).
    cy.visit("/");
    cy.get("body").then(($body) => {
      if (!$body.find('form[action*="logout"]').length) {
        cy.login(user.phone, password);
        cy.visit("/"); // cy.login lands on LOGIN_REDIRECT_URL; get back to home
      }
    });

    // Enforce the "while logged in" premise (mirrors it (b)).
    cy.get('form[action*="logout"]').should("exist");

    cy.get(".product-grid a.product-card")
      .filter(":not(:has(.oos))")
      .should(($cards) => {
        expect(
          $cards.length,
          "in-stock product cards on the home page"
        ).to.be.greaterThan(0);
      })
      .first()
      .click();
    cy.location("pathname").should("match", /^\/p\//);

    // cart.html renders the row name from product.title verbatim; capture it here.
    // Wrap the extracted string so @productTitle is a static alias, not a re-queried <h1>.
    cy.get("h1")
      .first()
      .invoke("text")
      .then((text) => {
        cy.wrap(text).as("productTitle");
      });

    cy.get("body").then(($body) => {
      if ($body.find("select[data-variant-select]").length) {
        cy.get("select[data-variant-select] option[data-in-stock='1']")
          .should(($opts) => {
            expect(
              $opts.length,
              "in-stock variant options on the product page"
            ).to.be.greaterThan(0);
          })
          .first()
          .then(($opt) => {
            cy.get("select[data-variant-select]").select(String($opt.val()));
          });
      }
    });

    cy.get("button[data-add-btn]").click();

    cy.location("pathname").should("eq", "/cart/");
    cy.get("ul.messages").invoke("text").should("match", /added/i);
    cy.get("@productTitle").then((title) => {
      // cart.html row: <a>{{ line.variant.product.title }}</a> -- title verbatim.
      cy.get("table.cart-table").should("contain.text", title.trim());
    });
    cy.get("table.cart-table tbody tr").should("have.length.gte", 1);
  });
});
