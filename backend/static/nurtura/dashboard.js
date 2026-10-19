// Admin dashboard (#120): crosshair and tooltip on the trend chart. Without
// script, each day still has a native <title> tooltip.
(function () {
  "use strict";
  const LABELS = {
    ideas: "Ideas generated",
    milestones: "Milestones recorded",
    feedback: "Feedback received",
  };

  document.querySelectorAll("[data-od-trend]").forEach(function (figure) {
    const svg = figure.querySelector("svg");
    const cross = figure.querySelector("[data-od-cross]");
    const tip = figure.querySelector("[data-od-tip]");
    if (!svg || !cross || !tip) return;

    function show(hit) {
      const cx = hit.getAttribute("data-cx");
      cross.setAttribute("x1", cx);
      cross.setAttribute("x2", cx);
      cross.setAttribute("visibility", "visible");

      tip.textContent = "";
      const title = document.createElement("strong");
      title.textContent = hit.getAttribute("data-label");
      tip.appendChild(title);
      Object.keys(LABELS).forEach(function (key) {
        const row = document.createElement("span");
        const swatch = document.createElement("i");
        swatch.className = "od-key od-s-" + key;
        row.appendChild(swatch);
        row.appendChild(
          document.createTextNode(
            LABELS[key] + ": " + hit.getAttribute("data-" + key)
          )
        );
        tip.appendChild(row);
      });
      tip.hidden = false;

      // Place the tip beside the crosshair, inside the figure.
      const box = svg.getBoundingClientRect();
      const fig = figure.getBoundingClientRect();
      const viewWidth = svg.viewBox.baseVal.width || box.width;
      const x = box.left - fig.left + (Number(cx) / viewWidth) * box.width;
      const tipWidth = tip.offsetWidth;
      const left = x + 12 + tipWidth > fig.width ? x - 12 - tipWidth : x + 12;
      tip.style.left = Math.max(0, left) + "px";
      tip.style.top = box.top - fig.top + 8 + "px";
    }

    function hide() {
      cross.setAttribute("visibility", "hidden");
      tip.hidden = true;
    }

    figure.querySelectorAll(".od-hit").forEach(function (hit) {
      hit.addEventListener("mouseenter", function () { show(hit); });
      hit.addEventListener("focus", function () { show(hit); });
    });
    svg.addEventListener("mouseleave", hide);
  });
})();
