// Progressive enhancement only; every action also works as a plain form post.
(function () {
  "use strict";

  // Move keyboard focus to the error summary or first invalid field (SDS screen design).
  document.addEventListener("DOMContentLoaded", function () {
    var summary = document.querySelector("[data-error-summary]");
    var invalid = document.querySelector("[aria-invalid='true']");
    if (summary) { summary.focus(); } else if (invalid) { invalid.focus(); }

    // On small screens start with the navigation menu collapsed.
    var menu = document.querySelector(".nav-menu");
    if (menu && window.matchMedia("(max-width: 760px)").matches) { menu.removeAttribute("open"); }

    // Confirmation dialogs: a button with data-dialog opens the named <dialog>.
    document.querySelectorAll("[data-dialog]").forEach(function (button) {
      var dialog = document.getElementById(button.getAttribute("data-dialog"));
      if (!dialog || typeof dialog.showModal !== "function") { return; }
      button.addEventListener("click", function (event) {
        event.preventDefault();
        dialog.showModal();
        var first = dialog.querySelector("textarea, input:not([type=hidden]), button");
        if (first) { first.focus(); }
      });
      dialog.querySelectorAll("[data-dialog-close]").forEach(function (close) {
        close.addEventListener("click", function () { dialog.close(); button.focus(); });
      });
    });

    // Plain confirm for irreversible single-button forms (NFR-USE-01).
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.getAttribute("data-confirm"))) { event.preventDefault(); }
      });
    });

    // Prevent double submission while a request is in flight; server keys still dedupe retries.
    document.querySelectorAll("form[method=post]").forEach(function (form) {
      form.addEventListener("submit", function () {
        form.querySelectorAll("button[type=submit]").forEach(function (b) {
          window.setTimeout(function () { b.disabled = true; }, 0);
        });
      });
    });
  });
})();
