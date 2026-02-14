document.addEventListener("DOMContentLoaded", function () {
  // Mobile nav toggle
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });
  }

  // Work form: add/remove video URL inputs
  var addVideoBtn = document.getElementById("add-video-btn");
  var videoContainer = document.getElementById("video-urls-container");
  if (addVideoBtn && videoContainer) {
    addVideoBtn.addEventListener("click", function () {
      var row = document.createElement("div");
      row.className = "video-url-row";
      row.innerHTML =
        '<input type="text" name="video_titles[]" placeholder="Video title (optional)">' +
        '<input type="url" name="video_urls[]" placeholder="YouTube or embed URL">' +
        '<button type="button" class="btn btn-secondary btn-remove-video">Remove</button>';
      videoContainer.appendChild(row);
    });
    videoContainer.addEventListener("click", function (e) {
      if (e.target.classList.contains("btn-remove-video")) {
        e.target.parentElement.remove();
      }
    });
  }

  // Gallery arrow scroll
  var wrapper = document.querySelector(".gallery-track-wrapper");
  if (!wrapper) return;

  var prev = document.querySelector(".gallery-prev");
  var next = document.querySelector(".gallery-next");
  var track = document.querySelector(".gallery-track");
  var scrollAmt = 300;

  // Pause CSS animation and switch to manual scroll on arrow click
  function toManual() {
    if (track.style.animation !== "none") {
      var style = window.getComputedStyle(track);
      var matrix = new DOMMatrix(style.transform);
      var currentX = matrix.m41;
      track.style.animation = "none";
      track.style.transform = "translateX(" + currentX + "px)";
      wrapper.style.overflow = "hidden";
    }
  }

  if (prev) {
    prev.addEventListener("click", function () {
      toManual();
      var current = parseFloat(track.style.transform.replace(/[^-\d.]/g, "")) || 0;
      var newX = Math.min(current + scrollAmt, 0);
      track.style.transition = "transform .4s ease";
      track.style.transform = "translateX(" + newX + "px)";
    });
  }

  if (next) {
    next.addEventListener("click", function () {
      toManual();
      var current = parseFloat(track.style.transform.replace(/[^-\d.]/g, "")) || 0;
      var maxScroll = -(track.scrollWidth - wrapper.clientWidth);
      var newX = Math.max(current - scrollAmt, maxScroll);
      track.style.transition = "transform .4s ease";
      track.style.transform = "translateX(" + newX + "px)";
    });
  }
});
