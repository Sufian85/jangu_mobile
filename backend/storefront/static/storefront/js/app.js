(function () {
  // mobile nav is CSS-only; nothing needed here yet for it.

  // product detail: thumbnail swap
  document.querySelectorAll(".pd .gallery .thumbs img").forEach(function (t) {
    t.addEventListener("click", function () {
      var main = document.querySelector(".pd .gallery .main img");
      if (main) main.src = t.dataset.full || t.src;
    });
  });

  // product detail: variant <select> updates price + stock button state
  var sel = document.querySelector("[data-variant-select]");
  if (sel) {
    var priceEl = document.querySelector("[data-variant-price]");
    var addBtn = document.querySelector("[data-add-btn]");
    var sync = function () {
      var opt = sel.options[sel.selectedIndex];
      if (priceEl && opt.dataset.price) priceEl.textContent = opt.dataset.price;
      if (addBtn) addBtn.disabled = opt.dataset.inStock !== "1";
    };
    sel.addEventListener("change", sync);
    sync();
  }

  // qty steppers
  document.querySelectorAll("[data-qty]").forEach(function (wrap) {
    var input = wrap.querySelector('input[type="number"]');
    if (!input) return;
    var min = parseInt(input.getAttribute("min"), 10);
    if (isNaN(min)) min = 1;
    wrap.querySelectorAll("button[data-step]").forEach(function (b) {
      b.addEventListener("click", function () {
        var step = b.dataset.step === "down" ? -1 : 1;
        var v = Math.max(min, (parseInt(input.value, 10) || min) + step);
        input.value = v;
      });
    });
  });
})();
