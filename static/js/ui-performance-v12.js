(function () {
  "use strict";

  var BATCH_SIZE = 40;
  var TABLE_ROW_LIMIT = 120;

  function scheduleIdle(fn) {
    if ("requestIdleCallback" in window) {
      window.requestIdleCallback(fn, { timeout: 500 });
      return;
    }
    setTimeout(fn, 16);
  }

  function renderInBatches(items, renderer, done) {
    var idx = 0;
    function step() {
      var end = Math.min(idx + BATCH_SIZE, items.length);
      while (idx < end) {
        renderer(items[idx], idx);
        idx += 1;
      }
      if (idx < items.length) {
        scheduleIdle(step);
      } else if (typeof done === "function") {
        done();
      }
    }
    step();
  }

  function optimizeLargeTables() {
    var tables = document.querySelectorAll("table tbody");
    tables.forEach(function (tbody) {
      var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
      if (rows.length <= TABLE_ROW_LIMIT) {
        return;
      }

      var hidden = rows.slice(TABLE_ROW_LIMIT);
      hidden.forEach(function (row) {
        row.style.display = "none";
      });

      var table = tbody.closest("table");
      if (!table || table.dataset.showMoreAttached === "1") {
        return;
      }
      table.dataset.showMoreAttached = "1";

      var wrap = document.createElement("div");
      wrap.className = "ui-perf-show-more-wrap";

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn-outline-primary btn-sm";
      btn.textContent = "Mostrar mais linhas";

      btn.addEventListener("click", function () {
        var chunk = hidden.splice(0, BATCH_SIZE);
        chunk.forEach(function (row) {
          row.style.display = "";
        });
        if (hidden.length === 0) {
          btn.remove();
        }
      });

      wrap.appendChild(btn);
      table.insertAdjacentElement("afterend", wrap);
    });
  }

  function lazyRevealSections() {
    var targets = document.querySelectorAll("[data-lazy-section], .ai-card");
    if (!targets.length) {
      return;
    }

    if (!("IntersectionObserver" in window)) {
      targets.forEach(function (el) {
        el.classList.add("lazy-visible");
      });
      return;
    }

    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("lazy-visible");
          obs.unobserve(entry.target);
        }
      });
    }, { rootMargin: "120px 0px" });

    targets.forEach(function (el) {
      obs.observe(el);
    });
  }

  function primeImagesLazy() {
    var imgs = document.querySelectorAll("img:not([loading])");
    imgs.forEach(function (img) {
      img.setAttribute("loading", "lazy");
      img.setAttribute("decoding", "async");
    });
  }

  function boot() {
    primeImagesLazy();
    lazyRevealSections();
    scheduleIdle(optimizeLargeTables);
  }

  document.addEventListener("DOMContentLoaded", boot);

  window.uiPerf = {
    renderInBatches: renderInBatches,
    scheduleIdle: scheduleIdle
  };
})();
