// Drawn e-signature capture (FR-MEM-04). Writes a PNG data URL into the hidden input.
// Keyboard and assistive-technology users can instead type their name (rendered server-side).
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-signature]").forEach(function (wrapper) {
      var canvas = wrapper.querySelector("canvas");
      var output = wrapper.querySelector("input[type=hidden]");
      var clear = wrapper.querySelector("[data-signature-clear]");
      if (!canvas || !output) { return; }
      var ctx = canvas.getContext("2d");
      var drawing = false;
      var hasInk = false;

      function resize() {
        var ratio = window.devicePixelRatio || 1;
        var rect = canvas.getBoundingClientRect();
        canvas.width = Math.max(300, rect.width) * ratio;
        canvas.height = Math.max(120, rect.height) * ratio;
        ctx.scale(ratio, ratio);
        ctx.lineWidth = 2.2;
        ctx.lineCap = "round";
        ctx.strokeStyle = "#14204f";
      }
      function point(event) {
        var rect = canvas.getBoundingClientRect();
        return { x: event.clientX - rect.left, y: event.clientY - rect.top };
      }
      canvas.addEventListener("pointerdown", function (event) {
        drawing = true;
        canvas.setPointerCapture(event.pointerId);
        var p = point(event);
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
      });
      canvas.addEventListener("pointermove", function (event) {
        if (!drawing) { return; }
        var p = point(event);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        hasInk = true;
      });
      function finish() {
        if (!drawing) { return; }
        drawing = false;
        if (hasInk) { output.value = canvas.toDataURL("image/png"); }
      }
      canvas.addEventListener("pointerup", finish);
      canvas.addEventListener("pointerleave", finish);
      if (clear) {
        clear.addEventListener("click", function () {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          output.value = "";
          hasInk = false;
        });
      }
      resize();
    });
  });
})();
