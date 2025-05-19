// static/js/main.js

document.addEventListener("DOMContentLoaded", function() {
  // 1) Inicializa tooltips do Bootstrap (via title)
  const tooltipTriggerList = Array.from(document.querySelectorAll('[title]'));
  tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));

  // 2) Faz o fade-out automático das flash messages
  const flashContainer = document.getElementById("flash-container");
  if (flashContainer) {
    const flashes = flashContainer.querySelectorAll(".alert");
    flashes.forEach(flash => {
      setTimeout(() => {
        flash.style.transition = "opacity 0.5s";
        flash.style.opacity = "0";
        setTimeout(() => flash.remove(), 500);
      }, 3000);
    });
  }
});