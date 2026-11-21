// Featured Products shows only complete rows, however wide the screen is. CSS decides
// which cards to hide, so this can only be checked in a real browser. The target site
// needs at least 10 in-stock products with images.
const LAYOUTS = [
  { width: 1280, columns: 5, cards: 10 },
  { width: 1024, columns: 4, cards: 8 },
  { width: 768, columns: 3, cards: 6 },
  { width: 500, columns: 2, cards: 6 },
  { width: 375, columns: 2, cards: 6 },
  { width: 320, columns: 2, cards: 6 },
];

describe("Featured Products fills complete rows", () => {
  LAYOUTS.forEach(({ width, columns, cards }) => {
    it(`shows ${cards} products in ${columns} columns at ${width}px wide`, () => {
      cy.viewport(width, 900);
      cy.visit("/");
      cy.get("#featured .product-grid").then(($grid) => {
        expect($grid.css("grid-template-columns").split(" ")).to.have.length(columns);
        expect($grid.find(".product-card:visible")).to.have.length(cards);
      });
    });
  });
});
