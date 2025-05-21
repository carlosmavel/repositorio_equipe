// static/js/main.js

document.addEventListener("DOMContentLoaded", function() {
  // 1) Inicializa tooltips do Bootstrap
  Array.from(document.querySelectorAll('[title]')).forEach(el =>
    new bootstrap.Tooltip(el)
  );

  // 2) Fade-out das flash messages
  const flashContainer = document.getElementById("flash-container");
  if (flashContainer) {
    flashContainer.querySelectorAll(".alert").forEach(flash => {
      setTimeout(() => {
        flash.style.transition = "opacity 0.5s";
        flash.style.opacity = "0";
        setTimeout(() => flash.remove(), 500);
      }, 3000);
    });
  }
});