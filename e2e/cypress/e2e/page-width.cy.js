// No page may scroll sideways on a phone or tablet. It only reads pages, so it creates
// no data, but the target site needs the catalogue's iphone-17-pro and smartphones rows.
const WIDTHS = [320, 375, 414, 768];
const PAGES = [
  "/",
  "/search/",
  "/c/smartphones/",
  "/p/iphone-17-pro/",
  "/login/",
  "/register/",
  "/cart/",
];

describe("Pages fit the screen width", () => {
  WIDTHS.forEach((width) => {
    PAGES.forEach((path) => {
      it(`${path} at ${width}px wide`, () => {
        cy.viewport(width, 900);
        cy.visit(path);
        cy.document().then(({ documentElement: page }) => {
          expect(page.scrollWidth).to.be.at.most(page.clientWidth);
        });
      });
    });
  });
});
