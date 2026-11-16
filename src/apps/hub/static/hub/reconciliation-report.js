"use strict";

document.querySelectorAll("[data-report-print]").forEach((button) => {
  button.hidden = false;
  button.addEventListener("click", () => window.print());
});
