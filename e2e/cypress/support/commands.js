// Visit the home page and, if a logout form is present, submit it.
// Safe to call when already anonymous.
Cypress.Commands.add("ensureLoggedOut", () => {
  cy.visit("/");
  cy.get("body").then(($body) => {
    if ($body.find('form[action*="logout"]').length) {
      cy.get('form[action*="logout"]').first().submit();
    }
  });
  // Contract: the command returns only once the session is anonymous.
  cy.get('form[action*="logout"]').should("not.exist");
});

// Fill and submit the storefront login form. No assertions — callers assert.
// Django normalises a "07..." phone to "+256..." on the username field.
Cypress.Commands.add("login", (phone, password) => {
  cy.visit("/login/");
  cy.get("#id_username").clear().type(phone);
  cy.get("#id_password").clear().type(password, { log: false });
  cy.get('form[method="post"] button[type="submit"]').click();
});
