/* Page behaviour: nav state, scroll reveals, verification numbers pulled from the
   committed batch, and the agent console.

   The console posts to /api/inspect on viz.server, which runs the real adaptive
   runner. With no server behind the page there is nothing to fly, so it plays a
   clearly labelled offline rehearsal instead of pretending it flew something. */

(function () {
  "use strict";

  var data = window.AEROLOOP || {};

  /* ---------------- nav + reveals ---------------- */

  var nav = document.getElementById("nav");
  function onScroll() {
    nav.classList.toggle("stuck", window.scrollY > 24);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  function applyTheme() {
    var probe = window.scrollY + window.innerHeight * 0.5;
    var dark = false;
    var sections = document.querySelectorAll("section");
    for (var i = 0; i < sections.length; i++) {
      var el = sections[i];
      if (probe >= el.offsetTop && probe < el.offsetTop + el.offsetHeight) {
        dark = el.getAttribute("data-theme") === "dark";
      }
    }
    document.body.setAttribute("data-theme", dark ? "dark" : "light");
  }
  window.addEventListener("scroll", applyTheme, { passive: true });
  window.addEventListener("resize", applyTheme);
  applyTheme();

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.18 }
  );
  document.querySelectorAll(".rise").forEach(function (el) {
    observer.observe(el);
  });

  /* ---------------- verification numbers ---------------- */

  function countUp(el, value, format) {
    var start = performance.now();
    var duration = 1100;
    function tick(now) {
      var p = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = format(value * eased);
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  var batch = data.batch;
  if (batch) {
    var statsBox = document.querySelector(".stats");
    var seen = false;
    var statObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting || seen) return;
          seen = true;
          countUp(document.getElementById("stat-pass"), batch.pass_rate * 100, function (v) {
            return v.toFixed(0) + "%";
          });
          countUp(document.getElementById("stat-cov"), batch.mean_coverage * 100, function (v) {
            return v.toFixed(1) + "%";
          });
          countUp(document.getElementById("stat-col"), batch.total_collisions, function (v) {
            return Math.round(v).toString();
          });
          countUp(document.getElementById("stat-scen"), batch.scenarios, function (v) {
            return Math.round(v).toString();
          });
        });
      },
      { threshold: 0.4 }
    );
    if (statsBox) statObserver.observe(statsBox);

    document.getElementById("stat-seed").textContent = batch.base_seed;

    var grid = document.getElementById("batch");
    (batch.runs || []).forEach(function (run, i) {
      var cell = document.createElement("i");
      if (!run.passed) cell.className = "fail";
      cell.title =
        "seed " +
        run.seed +
        " / coverage " +
        Math.round(run.coverage * 100) +
        "% / " +
        run.elapsed_s +
        "s / collisions " +
        run.collisions;
      cell.style.transitionDelay = i * 14 + "ms";
      grid.appendChild(cell);
    });
  }

  /* ---------------- console ---------------- */

  var EXAMPLES = [
    "full sweep of the nacelle",
    "inspect ring 2 in heavy wind, seed 4242",
    "inspect the bottom side of the engine",
    "inspect ring 1 and 3, light wind",
    "full sweep, calm, seed 1017"
  ];

  var promptBox = document.getElementById("prompt");
  var chips = document.getElementById("chips");
  var runBtn = document.getElementById("run");
  var logBox = document.getElementById("log");
  var resultBox = document.getElementById("result");
  var lamp = document.getElementById("lamp");
  var lampText = document.getElementById("lamp-text");
  var conn = document.getElementById("conn");

  EXAMPLES.forEach(function (text) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = text;
    b.addEventListener("click", function () {
      promptBox.value = text;
      promptBox.focus();
    });
    chips.appendChild(b);
  });

  var online = false;

  fetch("/api/scene", { method: "GET" })
    .then(function (r) {
      if (!r.ok) throw new Error("bad status");
      return r.json();
    })
    .then(function () {
      online = true;
      lamp.className = "lamp live";
      lampText.textContent = "Mission server connected";
      conn.textContent = "adaptive runner ready";
    })
    .catch(function () {
      online = false;
      lamp.className = "lamp";
      lampText.textContent = "Offline rehearsal";
      conn.textContent = "run python -m viz.server for live flights";
    });

  function line(text, cls) {
    var el = document.createElement("div");
    el.className = "line " + (cls || "");
    el.innerHTML = '<span class="tick">&#9654;</span><span>' + text + "</span>";
    logBox.appendChild(el);
    logBox.scrollTop = logBox.scrollHeight;
    return el;
  }

  function stage(steps) {
    return new Promise(function (resolve) {
      var i = 0;
      function next() {
        if (i >= steps.length) {
          resolve();
          return;
        }
        line(steps[i], "done");
        i += 1;
        setTimeout(next, 420);
      }
      next();
    });
  }

  function pct(v) {
    return (v * 100).toFixed(1) + "%";
  }

  function renderResult(payload) {
    var trace = payload.trace || {};
    var artifact = payload.artifact || {};
    var quality = payload.quality || artifact.quality || [];
    var good = quality.filter(function (q) {
      return q.status === "good";
    }).length;
    var marginal = quality.filter(function (q) {
      return q.status === "marginal";
    }).length;
    var bad = quality.length - good - marginal;
    var disposition = artifact.final_disposition || payload.disposition || "unknown";
    var clean = disposition.toLowerCase().indexOf("complete") >= 0 || disposition.toLowerCase().indexOf("pass") >= 0;
    var recaptures = (artifact.requested_captures || payload.requested_captures || []).length;

    var cells = quality
      .map(function (q) {
        var cls = q.status === "good" ? "" : q.status === "marginal" ? "retry" : "bad";
        var label = (q.waypoint_index !== undefined ? "waypoint " + q.waypoint_index : "capture") +
          " / " + q.status + (q.reason ? " / " + q.reason : "");
        return '<i class="' + cls + '" title="' + label + '"></i>';
      })
      .join("");

    resultBox.innerHTML =
      '<div class="verdict ' + (clean ? "" : "hold") + '">' + disposition.replace(/_/g, " ") + "</div>" +
      '<div class="metrics">' +
      '<div class="metric"><b>' + (trace.coverage !== undefined ? pct(trace.coverage) : "--") + "</b><span>coverage</span></div>" +
      '<div class="metric"><b>' + (trace.collisions !== undefined ? trace.collisions : "--") + "</b><span>collisions</span></div>" +
      '<div class="metric"><b>' + (trace.elapsed_s !== undefined ? trace.elapsed_s.toFixed(1) + "s" : "--") + "</b><span>flight time</span></div>" +
      '<div class="metric"><b>' + good + "/" + quality.length + "</b><span>captures good</span></div>" +
      "</div>" +
      '<div class="captures">' + cells + "</div>" +
      '<p class="result-note">' +
      (recaptures
        ? recaptures + " capture(s) were re-flown after the quality oracle rejected the first attempt."
        : "Every capture passed the quality oracle on the first pass.") +
      (bad ? " " + bad + " still unusable." : "") +
      "</p>" +
      (payload.offline
        ? '<p class="mode-note">Offline rehearsal: numbers replayed from the committed verification batch, not a live flight.</p>'
        : '<p class="result-note">Signed artifact digest ' +
          String(artifact.integrity_digest || "").slice(0, 16) +
          '. <a href="../flight_view.html">Open the flight replay &rarr;</a></p>');
  }

  function offlineRun(text) {
    var runs = (batch && batch.runs) || [];
    var seedMatch = text.match(/seed\s*(\d+)/i);
    var pick = runs.length
      ? runs[seedMatch ? Number(seedMatch[1]) % runs.length : Math.floor(Math.random() * runs.length)]
      : { coverage: 1, collisions: 0, elapsed_s: 33.4 };
    var count = 24;
    var quality = [];
    for (var i = 0; i < count; i++) {
      var roll = Math.random();
      quality.push({
        waypoint_index: i,
        status: roll > 0.86 ? "marginal" : "good",
        reason: roll > 0.86 ? "motion blur over threshold" : ""
      });
    }
    return {
      offline: true,
      trace: {
        coverage: pick.coverage,
        collisions: pick.collisions,
        elapsed_s: pick.elapsed_s
      },
      artifact: {
        final_disposition: "complete (rehearsal)",
        requested_captures: quality.filter(function (q) {
          return q.status !== "good";
        })
      },
      quality: quality
    };
  }

  var busy = false;

  function run() {
    if (busy) return;
    var text = (promptBox.value || "").trim() || EXAMPLES[0];
    promptBox.value = text;
    busy = true;
    runBtn.disabled = true;
    lamp.className = "lamp busy";
    logBox.innerHTML = "";
    if (window.AeroSky) window.AeroSky.kick();

    line("work order: " + text);
    var staged = stage([
      "binding geometry, seed and wind scale",
      "planning the waypoint sweep",
      "flying the controller at 50 Hz"
    ]);

    var pending = online
      ? fetch("/api/inspect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: text })
        }).then(function (r) {
          return r.json();
        })
      : new Promise(function (resolve) {
          setTimeout(function () {
            resolve(offlineRun(text));
          }, 1800);
        });

    Promise.all([pending, staged])
      .then(function (settled) {
        var payload = settled[0];
        if (payload.ok === false) {
          line(payload.reply || "the agent could not parse that work order", "warn");
          return;
        }
        line("grading captures against the quality oracle", "done");
        if ((payload.artifact && (payload.artifact.requested_captures || []).length) > 0) {
          line("re-flying rejected captures", "warn");
        }
        line(payload.reply || "run complete", "done");
        renderResult(payload);
      })
      .catch(function (error) {
        line("mission server unreachable: " + error.message, "warn");
        renderResult(offlineRun(text));
      })
      .finally(function () {
        busy = false;
        runBtn.disabled = false;
        lamp.className = online ? "lamp live" : "lamp";
      });
  }

  runBtn.addEventListener("click", run);
  promptBox.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      run();
    }
  });
})();
