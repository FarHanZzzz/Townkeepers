// Progressive enhancement only; every action also works as a plain form post.
(function () {
  "use strict";

  function isTyping(target) {
    if (!target) { return false; }
    var tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
  }

  document.addEventListener("DOMContentLoaded", function () {

    // ---------------------------------------------------------------- H6
    // The top bar names the current page so orientation never depends on memory.
    var crumb = document.querySelector("[data-page-title]");
    if (crumb) {
      var pageTitle = document.title.split("·")[0].trim();
      if (pageTitle && pageTitle !== "Amader TOWNHALL") {
        crumb.textContent = pageTitle === "Dashboard" ? "Overview" : pageTitle;
      }
    }

    // ---------------------------------------------------------------- H9
    // Move keyboard focus to the error summary or first invalid field.
    var summary = document.querySelector("[data-error-summary]");
    var invalid = document.querySelector("[aria-invalid='true']");
    if (summary) { summary.focus(); } else if (invalid) { invalid.focus(); }

    // ---------------------------------------------------------------- H3/H7
    // Off-canvas navigation on narrow screens.
    var sidebar = document.getElementById("sidebar");
    var toggle = document.getElementById("menu-toggle");
    if (sidebar && toggle) {
      toggle.addEventListener("click", function () {
        var open = sidebar.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        if (open) {
          var first = sidebar.querySelector("nav a");
          if (first) { first.focus(); }
        }
      });
      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
          sidebar.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
          toggle.focus();
        }
      });
      document.addEventListener("click", function (event) {
        if (!sidebar.classList.contains("is-open")) { return; }
        if (!sidebar.contains(event.target) && !toggle.contains(event.target)) {
          sidebar.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
        }
      });
    }

    // ---------------------------------------------------------------- H3/H4
    // Dialogs: a button with data-dialog opens the named <dialog>.
    document.querySelectorAll("[data-dialog]").forEach(function (button) {
      var dialog = document.getElementById(button.getAttribute("data-dialog"));
      if (!dialog || typeof dialog.showModal !== "function") { return; }
      button.addEventListener("click", function (event) {
        event.preventDefault();
        dialog.showModal();
        var input = dialog.querySelector("[data-autofocus]");
        var first = input || dialog.querySelector("input, textarea, button");
        if (first) { first.focus(); }
      });
      dialog.querySelectorAll("[data-dialog-close]").forEach(function (close) {
        close.addEventListener("click", function () { dialog.close(); button.focus(); });
      });
    });

    // ---------------------------------------------------------------- H5
    // Plain confirm for irreversible single-button forms (NFR-USE-01).
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.getAttribute("data-confirm"))) { event.preventDefault(); }
      });
    });

    // ---------------------------------------------------------------- H1/H6
    // Prevent double submission and show that work is in flight.
    document.querySelectorAll("form[method=post]").forEach(function (form) {
      form.addEventListener("submit", function () {
        form.querySelectorAll("button[type=submit]").forEach(function (b) {
          window.setTimeout(function () {
            b.disabled = true;
            b.setAttribute("data-loading", "true");
            b.setAttribute("aria-busy", "true");
          }, 0);
        });
      });
    });

    // ---------------------------------------------------------------- H3/H5
    // Warn before discarding unsaved edits.
    var dirtyForms = [];
    document.querySelectorAll("form[method=post]:not([data-no-guard])").forEach(function (form) {
      var initial = new FormData(form);
      var snapshot = [];
      initial.forEach(function (value, key) { snapshot.push(key + "=" + value); });
      snapshot = snapshot.sort().join("&");
      var submitted = false;
      var record = { form: form, snapshot: snapshot, submitted: function () { submitted = true; } };

      form.addEventListener("submit", function () { submitted = true; });

      record.isDirty = function () {
        if (submitted) { return false; }
        var now = new FormData(form);
        var current = [];
        now.forEach(function (value, key) { current.push(key + "=" + value); });
        return current.sort().join("&") !== record.snapshot;
      };
      dirtyForms.push(record);
    });

    function anyDirty() {
      for (var i = 0; i < dirtyForms.length; i++) { if (dirtyForms[i].isDirty()) { return true; } }
      return false;
    }

    window.addEventListener("beforeunload", function (event) {
      if (anyDirty()) {
        event.preventDefault();
        event.returnValue = "";
        return "";
      }
    });

    document.addEventListener("click", function (event) {
      var link = event.target.closest ? event.target.closest("a[href]") : null;
      if (!link || !anyDirty()) { return; }
      if (link.target === "_blank" || link.hasAttribute("download")) { return; }
      if (!window.confirm("You have unsaved changes. Leave this page anyway?")) {
        event.preventDefault();
      }
    });

    // ---------------------------------------------------------------- H7
    // Quick jump: "/" opens, typing filters, arrows and Enter navigate.
    var jump = document.getElementById("quick-jump");
    var jumpInput = document.getElementById("quick-jump-input");
    var jumpList = document.getElementById("quick-jump-list");

    function visibleItems() {
      if (!jumpList) { return []; }
      return Array.prototype.filter.call(jumpList.children, function (li) { return !li.hidden; });
    }

    function setActive(li) {
      visibleItems().forEach(function (item) { item.querySelector("a").removeAttribute("data-active"); });
      if (li) {
        li.querySelector("a").setAttribute("data-active", "true");
        li.scrollIntoView({ block: "nearest" });
      }
    }

    if (jump && jumpInput && jumpList) {
      jump.addEventListener("close", function () { jumpInput.value = ""; visibleItems().forEach(function (li) { li.hidden = false; }); });
      jumpInput.addEventListener("input", function () {
        var q = jumpInput.value.trim().toLowerCase();
        Array.prototype.forEach.call(jumpList.children, function (li) {
          li.hidden = q !== "" && li.getAttribute("data-label").indexOf(q) === -1;
        });
        var first = visibleItems()[0];
        setActive(first || null);
      });
      jumpInput.addEventListener("keydown", function (event) {
        var items = visibleItems();
        var index = items.findIndex(function (li) { return li.querySelector("a").getAttribute("data-active") === "true"; });
        if (event.key === "ArrowDown") {
          event.preventDefault();
          setActive(items[Math.min(index + 1, items.length - 1)]);
        } else if (event.key === "ArrowUp") {
          event.preventDefault();
          setActive(items[Math.max(index - 1, 0)]);
        } else if (event.key === "Enter") {
          event.preventDefault();
          var target = items[index >= 0 ? index : 0];
          if (target) { window.location.assign(target.querySelector("a").href); }
        }
      });
      document.addEventListener("keydown", function (event) {
        if (event.key === "/" && !isTyping(event.target) && !jump.open) {
          event.preventDefault();
          jump.showModal();
          jumpInput.focus();
          setActive(visibleItems()[0] || null);
        }
      });
    }

    // ---------------------------------------------------------------- H10
    var shortcuts = document.getElementById("shortcuts");
    if (shortcuts) {
      document.addEventListener("keydown", function (event) {
        if (event.key === "?" && !isTyping(event.target) && !shortcuts.open) {
          event.preventDefault();
          shortcuts.showModal();
        }
      });
    }
  });
})();
