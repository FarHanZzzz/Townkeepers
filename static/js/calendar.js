/* ==========================================================================
   Townhall calendar
   One popup used everywhere a date, time or venue is chosen:
     - mode "view"     browse the heatmap and read the day's events
     - mode "book"     pick a day, a time range and a free room
     - mode "schedule" pick dates and times for an event draft

   Heat rule (same as the server): 1-2 events green, 3 orange, 4+ red.
   ========================================================================== */

var TownhallCalendar = (function () {
  "use strict";

  var CFG = window.TOWNHALL_CALENDAR || {};
  var DATA_URL = CFG.data || "/events/calendar-data/";
  var VENUE_URL = CFG.venues || "/events/venue-availability/";

  var MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  var DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  var state = {
    mode: "view",
    year: 0,
    month: 0,
    data: null,
    loading: false,
    selectedDay: null,
    selectedVenue: null,
    venues: null,
    venuesLoading: false,
    venuesFailed: false,
    firstDate: "",
    lastDate: "",
    startTime: "18:00",
    endTime: "21:00",
    onSelect: null,
    request: 0,
    venueRequest: 0,
  };

  var dialog = null;

  /* ---------------------------------------------------------------- helpers */

  function $(selector) {
    return dialog ? dialog.querySelector(selector) : null;
  }

  function el(id) {
    return document.getElementById(id);
  }

  function pad(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function keyOf(year, month, day) {
    return year + "-" + pad(month + 1) + "-" + pad(day);
  }

  function dateOf(key) {
    var parts = key.split("-").map(Number);
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  function todayKey() {
    var now = new Date();
    return keyOf(now.getFullYear(), now.getMonth(), now.getDate());
  }

  function fmtDay(key) {
    return dateOf(key).toLocaleDateString([], {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }

  function fmtShort(key) {
    return dateOf(key).toLocaleDateString([], {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }

  function fmtRange(first, last) {
    if (!first) {
      return "Not chosen";
    }
    if (!last || last === first) {
      return fmtShort(first);
    }
    return fmtShort(first) + " – " + fmtShort(last);
  }

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function statusLabel(status) {
    return {
      free: "Available",
      pending: "Requested",
      confirmed: "Booked",
      unavailable: "Closed",
    }[status] || status;
  }

  /* ------------------------------------------------------------ modal shell */

  function ensureModal() {
    if (el("townhall-calendar")) {
      dialog = el("townhall-calendar");
      return;
    }

    dialog = document.createElement("dialog");
    dialog.id = "townhall-calendar";
    dialog.className = "cal-modal";
    dialog.setAttribute("aria-labelledby", "cal-title");
    dialog.innerHTML =
      '<div class="cal-modal-head">' +
        '<div>' +
          '<h2 id="cal-title">Calendar</h2>' +
          '<p class="cal-sub" id="cal-sub"></p>' +
        '</div>' +
        '<button type="button" class="icon-button" data-cal-close aria-label="Close calendar">' +
          '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>' +
        '</button>' +
      '</div>' +
      '<div class="cal-layout">' +
        '<section class="cal-main">' +
          '<div class="cal-toolbar">' +
            '<button type="button" class="cal-nav-btn" data-cal-prev aria-label="Previous month">' +
              '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
            '</button>' +
            '<span class="cal-modal-month" id="cal-month"></span>' +
            '<button type="button" class="cal-nav-btn" data-cal-next aria-label="Next month">' +
              '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
            '</button>' +
            '<button type="button" class="cal-today-btn" data-cal-today>Today</button>' +
          '</div>' +
          '<div class="cal-legend" aria-hidden="true">' +
            '<span class="cal-legend-item"><i class="cal-dot cal-dot-green"></i>Free · 0–2</span>' +
            '<span class="cal-legend-item"><i class="cal-dot cal-dot-orange"></i>Busy · 3</span>' +
            '<span class="cal-legend-item"><i class="cal-dot cal-dot-red"></i>Packed · 4+</span>' +
          '</div>' +
          '<div class="cal-dow" id="cal-dow" aria-hidden="true"></div>' +
          '<div class="cal-grid" id="cal-grid"></div>' +
        '</section>' +
        '<aside class="cal-side">' +
          '<div id="cal-detail" class="cal-detail"></div>' +
          '<div id="cal-action"></div>' +
        '</aside>' +
      '</div>' +
      '<div class="cal-foot" id="cal-foot"></div>';

    document.body.appendChild(dialog);

    var dow = dialog.querySelector("#cal-dow");
    dow.innerHTML = DOW.map(function (name) {
      return '<span class="cal-dow-name">' + name + "</span>";
    }).join("");

    dialog.addEventListener("click", function (event) {
      var target = event.target;
      if (!target.closest) {
        return;
      }
      if (target.closest("[data-cal-close]")) {
        event.preventDefault();
        close();
        return;
      }
      if (target.closest("[data-cal-prev]")) {
        event.preventDefault();
        shiftMonth(-1);
        return;
      }
      if (target.closest("[data-cal-next]")) {
        event.preventDefault();
        shiftMonth(1);
        return;
      }
      if (target.closest("[data-cal-today]")) {
        event.preventDefault();
        var now = new Date();
        state.year = now.getFullYear();
        state.month = now.getMonth();
        selectDay(todayKey());
        loadMonth();
        return;
      }
      if (target.closest("[data-cal-retry]")) {
        event.preventDefault();
        loadMonth();
        return;
      }
      var day = target.closest("[data-cal-day]");
      if (day) {
        event.preventDefault();
        selectDay(day.getAttribute("data-cal-day"));
        return;
      }
      var venue = target.closest("[data-cal-venue]");
      if (venue && !venue.disabled) {
        event.preventDefault();
        selectVenue(venue);
        return;
      }
      if (target.closest("[data-cal-confirm]")) {
        event.preventDefault();
        confirmSelection();
      }
    });

    dialog.addEventListener("change", function (event) {
      var field = event.target.closest("[data-cal-field]");
      if (!field) {
        return;
      }
      applyField(field.getAttribute("data-cal-field"), field.value);
    });

    dialog.addEventListener("close", function () {
      state.selectedDay = null;
      state.selectedVenue = null;
      state.onSelect = null;
    });
  }

  /* ------------------------------------------------------------------- open */

  function open(options) {
    options = options || {};
    ensureModal();

    var now = new Date();
    state.mode = options.mode || "view";
    state.onSelect = options.onSelect || null;
    state.year = options.year || now.getFullYear();
    state.month = options.month != null ? options.month : now.getMonth();
    state.data = null;
    state.loading = false;
    state.venues = null;
    state.venuesFailed = false;
    state.firstDate = options.firstDate || "";
    state.lastDate = options.lastDate || state.firstDate;
    state.startTime = options.startTime || "18:00";
    state.endTime = options.endTime || "21:00";
    state.selectedVenue = options.selectedVenue || null;
    state.selectedDay = options.date || state.firstDate || null;

    if (state.selectedDay) {
      var selected = dateOf(state.selectedDay);
      state.year = selected.getFullYear();
      state.month = selected.getMonth();
    }

    $("#cal-title").textContent =
      options.title ||
      (state.mode === "book"
        ? "Book a day, time and venue"
        : state.mode === "schedule"
          ? "Choose dates and times"
          : "Calendar");
    $("#cal-sub").textContent =
      state.mode === "view"
        ? "Select a day to see what is already on campus."
        : state.mode === "book"
          ? "The room is only held after the last confirmation."
          : "These dates flow into the event draft.";

    if (!dialog.open) {
      dialog.showModal();
    }

    loadMonth();
    if (state.mode !== "view" && state.selectedDay) {
      loadVenues();
    }
  }

  function close() {
    if (dialog && dialog.open) {
      dialog.close();
    }
  }

  function shiftMonth(delta) {
    state.month += delta;
    if (state.month > 11) {
      state.month = 0;
      state.year += 1;
    } else if (state.month < 0) {
      state.month = 11;
      state.year -= 1;
    }
    state.selectedDay = null;
    state.selectedVenue = null;
    state.venues = null;
    loadMonth();
  }

  /* ------------------------------------------------------------------ month */

  function loadMonth() {
    var request = ++state.request;
    state.loading = true;
    renderGrid();

    fetch(DATA_URL + "?year=" + state.year + "&month=" + (state.month + 1), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        if (request !== state.request) {
          return;
        }
        state.data = data;
        state.loading = false;
        render();
      })
      .catch(function () {
        if (request !== state.request) {
          return;
        }
        state.loading = false;
        state.data = null;
        render();
      });
  }

  function render() {
    var label = $("#cal-month");
    if (label) {
      label.textContent = MONTHS[state.month] + " " + state.year;
    }
    renderGrid();
    renderDetail();
    renderAction();
    renderFoot();
  }

  function renderGrid() {
    var grid = $("#cal-grid");
    if (!grid) {
      return;
    }
    if (state.loading) {
      grid.innerHTML = '<p class="cal-loading">Loading the month…</p>';
      return;
    }
    if (!state.data) {
      grid.innerHTML =
        '<p class="cal-loading">The calendar did not load. ' +
        '<button type="button" class="link-button" data-cal-retry>Try again</button></p>';
      return;
    }

    var offset = new Date(state.year, state.month, 1).getDay();
    var total = new Date(state.year, state.month + 1, 0).getDate();
    var today = todayKey();
    var html = "";

    for (var blank = 0; blank < offset; blank += 1) {
      html += '<span class="cal-cell cal-cell-blank" aria-hidden="true"></span>';
    }

    for (var day = 1; day <= total; day += 1) {
      var key = keyOf(state.year, state.month, day);
      var entry = (state.data.days && state.data.days[key]) || {
        count: 0,
        level: "green",
        events: [],
      };
      var classes = "cal-cell cal-day-" + entry.level;
      if (entry.count > 0) {
        classes += " cal-cell-has-events";
      }
      if (key === state.selectedDay) {
        classes += " cal-cell-selected";
      }
      if (key === today) {
        classes += " cal-cell-today";
      }
      html +=
        '<button type="button" class="' + classes + '" data-cal-day="' + key + '"' +
          ' aria-pressed="' + (key === state.selectedDay ? "true" : "false") + '"' +
          ' aria-label="' + day + " " + MONTHS[state.month] + ", " +
          entry.count + " event" + (entry.count === 1 ? "" : "s") + '">' +
          '<span class="cal-date">' + day + "</span>" +
          (entry.count > 0 ? '<span class="cal-count">' + entry.count + "</span>" : "") +
        "</button>";
    }

    grid.innerHTML = html;
  }

  /* ----------------------------------------------------------------- detail */

  function renderDetail() {
    var box = $("#cal-detail");
    if (!box) {
      return;
    }
    if (!state.selectedDay) {
      box.innerHTML =
        '<div class="cal-detail-card cal-detail-hint">' +
          "<h3>Choose a day</h3>" +
          "<p>Days with events show the club, the room and the time. Green is quiet, orange holds three events, red is packed.</p>" +
        "</div>";
      return;
    }

    var entry = state.data && state.data.days ? state.data.days[state.selectedDay] : null;
    var events = entry ? entry.events : [];
    var html =
      '<div class="cal-detail-card">' +
        '<header class="cal-detail-head">' +
          "<h3>" + fmtDay(state.selectedDay) + "</h3>" +
          '<span class="badge badge-neutral">' + events.length + " event" + (events.length === 1 ? "" : "s") + "</span>" +
        "</header>";

    if (!events.length) {
      html += '<p class="cal-detail-empty">Nothing is booked on this day.</p>';
    } else {
      events.forEach(function (event) {
        var title =
          state.mode === "view"
            ? '<a class="cal-event-title" href="' + esc(event.url) + '">' + esc(event.title) + "</a>"
            : '<span class="cal-event-title">' + esc(event.title) + "</span>";
        html +=
          '<div class="cal-event-row">' +
            '<div class="cal-event-time">' +
              esc(event.start_time || "—") +
              (event.end_time ? "<br>" + esc(event.end_time) : "") +
            "</div>" +
            '<div class="cal-event-info">' +
              title +
              '<div class="cal-event-meta">' +
                "<span>" + esc(event.club) + "</span>" +
                "<span>" + esc(event.venue) + "</span>" +
                "<span>" + esc(event.status) + "</span>" +
              "</div>" +
            "</div>" +
          "</div>";
      });
    }

    html += "</div>";
    box.innerHTML = html;
  }

  /* ------------------------------------------------------------------ slots */

  function renderAction() {
    var box = $("#cal-action");
    if (!box) {
      return;
    }
    if (state.mode === "view") {
      box.innerHTML = "";
      return;
    }
    if (!state.selectedDay) {
      box.innerHTML = "";
      return;
    }
    if (state.mode === "schedule") {
      box.innerHTML = renderSchedulePanel();
      return;
    }
    box.innerHTML = renderBookPanel();
  }

  function renderSchedulePanel() {
    return (
      '<div class="cal-action-panel">' +
        '<h3>Use this date</h3>' +
        '<div class="cal-form-row">' +
          '<label class="cal-mini"><span>First date</span>' +
            '<input type="date" data-cal-field="first" value="' + esc(state.firstDate) + '"></label>' +
          '<label class="cal-mini"><span>Last date</span>' +
            '<input type="date" data-cal-field="last" value="' + esc(state.lastDate) + '"></label>' +
        "</div>" +
        '<div class="cal-form-row">' +
          '<label class="cal-mini"><span>Start</span>' +
            '<input type="time" data-cal-field="start" value="' + esc(state.startTime) + '"></label>' +
          '<label class="cal-mini"><span>End</span>' +
            '<input type="time" data-cal-field="end" value="' + esc(state.endTime) + '"></label>' +
        "</div>" +
        renderVenueSection("Propose a room (optional)") +
      "</div>"
    );
  }

  function renderVenueSection(title) {
    var html =
      '<div class="cal-venue-head"><h4>' + esc(title) + "</h4>" +
        '<span class="help">' + esc(state.startTime) + "–" + esc(state.endTime) + "</span></div>";

    if (state.venuesLoading) {
      return html + '<p class="cal-loading">Checking rooms…</p>';
    }
    if (state.venuesFailed) {
      return html + '<p class="cal-detail-empty">Could not check the rooms. Try another time.</p>';
    }
    if (!state.venues) {
      return html + '<p class="cal-detail-empty">Choose a day to see which rooms are free.</p>';
    }
    if (!state.venues.length) {
      return html + '<p class="cal-detail-empty">No room fits this time. Try a shorter slot.</p>';
    }

    html += '<div class="cal-venue-list">';
    state.venues.forEach(function (venue) {
      var selectable = venue.status === "free" || venue.status === "pending";
      var selected = state.selectedVenue === venue.id;
      html +=
        '<button type="button" class="cal-venue' + (selected ? " cal-venue-selected" : "") + '"' +
          ' data-cal-venue="' + venue.id + '" data-cal-venue-name="' + esc(venue.name) + '"' +
          (selectable ? "" : " disabled") + ">" +
          '<span class="cal-venue-main">' +
            '<span class="cal-venue-name">' + esc(venue.name) + "</span>" +
            '<span class="cal-venue-meta">' + esc(venue.kind) + " · " + venue.capacity +
              " seats · " + esc(venue.opens_at) + "–" + esc(venue.closes_at) + "</span>" +
          "</span>" +
          '<span class="cal-venue-status is-' + esc(venue.status) + '">' +
            statusLabel(venue.status) + "</span>" +
        "</button>";
    });
    html += "</div>";
    return html;
  }

  function renderBookPanel() {
    return (
      '<div class="cal-action-panel">' +
        "<h3>Book this day</h3>" +
        '<div class="cal-form-row">' +
          '<label class="cal-mini"><span>First date</span>' +
            '<input type="date" data-cal-field="first" value="' + esc(state.firstDate) + '"></label>' +
          '<label class="cal-mini"><span>Last date</span>' +
            '<input type="date" data-cal-field="last" value="' + esc(state.lastDate) + '"></label>' +
        "</div>" +
        '<div class="cal-form-row">' +
          '<label class="cal-mini"><span>Start</span>' +
            '<input type="time" data-cal-field="start" value="' + esc(state.startTime) + '"></label>' +
          '<label class="cal-mini"><span>End</span>' +
            '<input type="time" data-cal-field="end" value="' + esc(state.endTime) + '"></label>' +
        "</div>" +
        renderVenueSection("Rooms for this slot") +
      "</div>"
    );
  }

  function renderFoot() {
    var foot = $("#cal-foot");
    if (!foot) {
      return;
    }
    if (state.mode === "view") {
      foot.innerHTML =
        '<a class="button secondary" href="' + esc(CFG.page || "/events/calendar/") + '">Open full calendar</a>' +
        '<button type="button" class="button secondary" data-cal-close>Close</button>';
      return;
    }

    var confirmLabel;
    var disabled = "";
    if (state.mode === "book") {
      var venueName = selectedVenueName();
      if (state.selectedVenue && venueName) {
        confirmLabel = "Book " + fmtRange(state.firstDate, state.lastDate) + " · " + venueName;
      } else {
        confirmLabel = "Choose a room to continue";
        disabled = " disabled";
      }
    } else {
      confirmLabel = state.firstDate
        ? "Use " + fmtRange(state.firstDate, state.lastDate)
        : "Choose a date to continue";
      disabled = state.firstDate ? "" : " disabled";
    }

    foot.innerHTML =
      '<button type="button" class="button secondary" data-cal-close>Cancel</button>' +
      '<button type="button" class="button" data-cal-confirm' + disabled + ">" +
        esc(confirmLabel) + "</button>";
  }

  /* ---------------------------------------------------------------- actions */

  function selectDay(key) {
    state.selectedDay = key;
    state.selectedVenue = null;

    if (!state.firstDate || state.firstDate === state.lastDate) {
      state.firstDate = key;
      state.lastDate = key;
    } else {
      state.firstDate = key;
      if (!state.lastDate || state.lastDate < key) {
        state.lastDate = key;
      }
    }

    render();
    if (state.mode !== "view") {
      loadVenues();
    }
    revealSide();
  }

  function revealSide() {
    if (!window.matchMedia || !window.matchMedia("(max-width: 860px)").matches) {
      return;
    }
    var layout = $(".cal-layout");
    var side = $(".cal-side");
    if (!layout || !side) {
      return;
    }
    var delta = side.getBoundingClientRect().top - layout.getBoundingClientRect().top;
    layout.scrollTop += delta - 4;
  }

  function selectVenue(button) {
    var id = parseInt(button.getAttribute("data-cal-venue"), 10);
    if (state.selectedVenue === id) {
      state.selectedVenue = null;
    } else {
      state.selectedVenue = id;
    }
    renderAction();
    renderFoot();
  }

  function applyField(name, value) {
    if (name === "first") {
      state.firstDate = value;
      if (!state.lastDate || state.lastDate < value) {
        state.lastDate = value;
      }
      if (value) {
        state.selectedDay = value;
      }
    } else if (name === "last") {
      state.lastDate = value;
      if (value && (!state.firstDate || value < state.firstDate)) {
        state.firstDate = value;
        state.selectedDay = value;
      }
    } else if (name === "start") {
      state.startTime = value;
    } else if (name === "end") {
      state.endTime = value;
    }

    render();
    if (state.mode !== "view") {
      loadVenues();
    }
  }

  function loadVenues() {
    if (!state.selectedDay) {
      state.venues = null;
      renderAction();
      renderFoot();
      return;
    }
    var request = ++state.venueRequest;
    var date = state.firstDate || state.selectedDay;
    state.venuesLoading = true;
    state.venuesFailed = false;
    renderAction();

    var url =
      VENUE_URL +
      "?date=" + encodeURIComponent(date) +
      "&start=" + encodeURIComponent(state.startTime) +
      "&end=" + encodeURIComponent(state.endTime);

    fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        if (request !== state.venueRequest) {
          return;
        }
        state.venues = data.venues || [];
        state.venuesLoading = false;
        renderAction();
        renderFoot();
      })
      .catch(function () {
        if (request !== state.venueRequest) {
          return;
        }
        state.venues = null;
        state.venuesLoading = false;
        state.venuesFailed = true;
        renderAction();
        renderFoot();
      });
  }

  function confirmSelection() {
    if (!state.onSelect) {
      close();
      return;
    }
    if (state.mode === "book" && !state.selectedVenue) {
      return;
    }
    if (!state.firstDate) {
      return;
    }
    state.onSelect({
      date: state.firstDate,
      lastDate: state.lastDate || state.firstDate,
      startTime: state.startTime,
      endTime: state.endTime,
      venueId: state.selectedVenue,
      venueName: selectedVenueName(),
    });
    close();
  }

  function selectedVenueName() {
    var name = "";
    (state.venues || []).forEach(function (venue) {
      if (venue.id === state.selectedVenue) {
        name = venue.name;
      }
    });
    return name;
  }

  /* ------------------------------------------------- page-level integrations */

  function initSlotPickers() {
    document.querySelectorAll("[data-slot-picker]").forEach(function (picker) {
      var openButton = picker.querySelector("[data-slot-open]");
      if (!openButton) {
        return;
      }

      function field(name) {
        return picker.querySelector('[name="' + name + '"]');
      }

      function refreshSummary() {
        var dateBox = picker.querySelector("[data-slot-date]");
        var timeBox = picker.querySelector("[data-slot-time]");
        var venueBox = picker.querySelector("[data-slot-venue]");
        var first = field("first_date");
        var last = field("last_date");
        var start = field("start_time");
        var end = field("end_time");
        var venue = field("venue");

        if (dateBox) {
          dateBox.textContent = first && first.value ? fmtRange(first.value, last ? last.value : "") : "Not chosen";
        }
        if (timeBox) {
          timeBox.textContent =
            (start && start.value ? start.value : "—") + "–" + (end && end.value ? end.value : "—");
        }
        if (venueBox) {
          var option = venue && venue.selectedIndex >= 0 ? venue.options[venue.selectedIndex] : null;
          venueBox.textContent = option ? option.textContent.trim() : "Not chosen";
        }
      }

      openButton.addEventListener("click", function (event) {
        event.preventDefault();
        var venue = field("venue");
        open({
          mode: "book",
          title: openButton.getAttribute("data-calendar-title") || "Choose date, time and venue",
          firstDate: field("first_date") ? field("first_date").value : "",
          lastDate: field("last_date") ? field("last_date").value : "",
          startTime: field("start_time") && field("start_time").value ? field("start_time").value : "18:00",
          endTime: field("end_time") && field("end_time").value ? field("end_time").value : "21:00",
          selectedVenue: venue && venue.value ? parseInt(venue.value, 10) : null,
          onSelect: function (selection) {
            if (field("first_date")) {
              field("first_date").value = selection.date;
            }
            if (field("last_date")) {
              field("last_date").value = selection.lastDate;
            }
            if (field("start_time")) {
              field("start_time").value = selection.startTime;
            }
            if (field("end_time")) {
              field("end_time").value = selection.endTime;
            }
            if (venue && selection.venueId) {
              venue.value = String(selection.venueId);
            }
            refreshSummary();
          },
        });
      });

      var form = picker.closest("form");
      if (form) {
        form.addEventListener("submit", function (event) {
          var venue = field("venue");
          if (venue && !venue.value) {
            event.preventDefault();
            picker.classList.add("slot-picker-missing");
            openButton.click();
          }
        });
      }

      refreshSummary();
    });
  }

  function initTriggers() {
    document.querySelectorAll("[data-calendar-open]").forEach(function (button) {
      if (button.closest("[data-slot-picker]")) {
        return;
      }
      button.addEventListener("click", function (event) {
        event.preventDefault();
        var mode = button.getAttribute("data-calendar-open") || "view";

        if (mode === "view") {
          open({ mode: "view", title: button.getAttribute("data-calendar-title") || "Calendar" });
          return;
        }

        var fields = {};
        (button.getAttribute("data-calendar-targets") || "")
          .split(/\s+/)
          .filter(Boolean)
          .forEach(function (id) {
            var input = document.getElementById(id);
            if (input && input.name) {
              fields[input.name] = input;
            }
          });

        // Forms name the same concept differently (`first_date` on an event,
        // `date` on the availability search); accept either.
        var dateField = fields.first_date || fields.date || null;
        var startField = fields.start_time || fields.start || null;
        var endField = fields.end_time || fields.end || null;
        var hostForm = button.closest("form");
        var proposal = hostForm ? hostForm.querySelector('[name="proposed_venue"]') : null;

        open({
          mode: "schedule",
          title: button.getAttribute("data-calendar-title") || "Choose dates and times",
          firstDate: dateField ? dateField.value : "",
          lastDate: fields.last_date ? fields.last_date.value : "",
          startTime: startField && startField.value ? startField.value : "18:00",
          endTime: endField && endField.value ? endField.value : "21:00",
          onSelect: function (selection) {
            if (dateField) {
              dateField.value = selection.date;
            }
            if (fields.last_date) {
              fields.last_date.value = selection.lastDate;
            }
            if (startField) {
              startField.value = selection.startTime;
            }
            if (endField) {
              endField.value = selection.endTime;
            }
            if (proposal && selection.venueName) {
              proposal.value = selection.venueName;
            }
          },
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initSlotPickers();
    initTriggers();
  });

  return { open: open, close: close };
})();
