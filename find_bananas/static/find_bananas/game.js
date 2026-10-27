// Find Bananas — game screen.
// The server owns the game: this script only displays what it is told,
// sends guesses, and never knows a banana count before answering.
(function () {
  "use strict";

  var root = document.getElementById("game");
  if (!root) return;

  var T = JSON.parse(document.getElementById("i18n").textContent);
  var state = JSON.parse(document.getElementById("initial-state").textContent);
  var edition = root.dataset.edition;
  var csrfToken = document.querySelector('meta[name="csrf-token"]').content;
  var DISPLAY_MS = 5000;
  var busy = false;
  var countdownTimer = null;

  // --- helpers -------------------------------------------------------------

  function fmt(template, values) {
    return template.replace(/\{(\w+)\}/g, function (_, key) {
      return values[key] !== undefined ? values[key] : "";
    });
  }

  function field(name) {
    return root.querySelector('[data-field="' + name + '"]');
  }

  function show(screen) {
    root.querySelectorAll(".screen").forEach(function (el) {
      el.hidden = el.dataset.screen !== screen;
    });
    root.dataset.screen = screen;
    // Only the guess field takes focus, so the phone keyboard opens at once.
    if (screen === "guess") document.getElementById("guess-input").focus({ preventScroll: true });
  }

  function renderProgress(current) {
    var list = document.getElementById("progress");
    var total = state.edition.rounds;
    list.innerHTML = "";
    for (var i = 1; i <= total; i++) {
      var li = document.createElement("li");
      li.textContent = i;
      var answered = state.rounds[i - 1] && state.rounds[i - 1].answered;
      if (answered) li.className = "done";
      else if (i === current) li.className = "current";
      list.appendChild(li);
    }
    list.hidden = false;
  }

  function api(path, body, responseType) {
    var url = "/api/editions/" + edition + path;
    return fetch(url, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrfToken, "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(
      function (response) {
        if (response.ok) return responseType === "blob" ? response.blob() : response.json();
        return response.json().then(
          function (data) { throw { code: data.error || "default", status: response.status }; },
          function () { throw { code: "default", status: response.status }; }
        );
      },
      function () { throw { code: "network" }; }
    );
  }

  function fail(error) {
    busy = false;
    var code = (error && error.code) || "default";
    if (code === "network") {
      // Keep the player where they are; they can simply retry.
      flashError(T.errors.network);
      return;
    }
    field("error-message").textContent = T.errors[code] || T.errors["default"];
    show("error");
  }

  function flashError(message) {
    var current = root.querySelector('[data-screen="' + root.dataset.screen + '"]');
    var box = current && current.querySelector(".form-error");
    if (!box) {
      box = document.createElement("p");
      box.className = "form-error";
      box.setAttribute("role", "alert");
      current.appendChild(box);
    }
    box.textContent = message;
    box.hidden = false;
  }

  function clearErrors() {
    root.querySelectorAll(".form-error").forEach(function (el) { el.hidden = true; });
  }

  // --- screens -------------------------------------------------------------

  function goReady(n) {
    var range = state.edition.ranges[n - 1] || ["?", "?"];
    field("ready-title").textContent = fmt(T.roundTitle, { n: n, total: state.edition.rounds });
    field("ready-range").textContent = fmt(T.roundRange, { min: range[0], max: range[1] });
    renderProgress(n);
    show("ready");
  }

  function goGuess(n, afterReload) {
    var input = document.getElementById("guess-input");
    var range = state.edition.ranges[n - 1];
    input.value = "";
    input.placeholder = range ? range[0] + "–" + range[1] : "";
    var label = field("guess-label");
    if (!label.dataset.default) label.dataset.default = label.textContent;
    label.textContent = afterReload ? T.guessLabelAfterReload : label.dataset.default;
    renderProgress(n);
    show("guess");
  }

  // Make the image as large as the window allows. A landscape image on a
  // screen held upright is turned a quarter turn: same image, more room.
  function fitImage(img, frame) {
    var w = frame.clientWidth;
    var h = frame.clientHeight;
    var iw = img.naturalWidth;
    var ih = img.naturalHeight;
    var turn = h > w && iw > ih;
    var scale = turn ? Math.min(w / ih, h / iw) : Math.min(w / iw, h / ih);
    img.style.width = Math.floor(iw * scale) + "px";
    img.style.height = Math.floor(ih * scale) + "px";
    img.classList.toggle("is-turned", turn);
  }

  function showBananas() {
    if (busy) return;
    busy = true;
    clearErrors();
    var n = state.next_round;
    var frame = document.getElementById("frame");
    var loading = document.getElementById("frame-loading");
    var bar = document.getElementById("timer-bar");
    frame.querySelectorAll("img").forEach(function (img) { img.remove(); });
    loading.hidden = false;
    bar.style.transition = "none";
    bar.style.transform = "scaleX(1)";
    show("view");

    api("/rounds/" + n + "/image", {}, "blob")
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var img = new Image();
        img.alt = "";
        img.src = url;
        return img.decode().then(function () { return { img: img, url: url }; });
      })
      .then(function (loaded) {
        loading.hidden = true;
        frame.appendChild(loaded.img);
        fitImage(loaded.img, frame);
        var refit = function () { fitImage(loaded.img, frame); };
        window.addEventListener("resize", refit);
        // The 5 seconds start once the image is actually on screen.
        requestAnimationFrame(function () {
          bar.style.transition = "transform " + DISPLAY_MS + "ms linear";
          bar.style.transform = "scaleX(0)";
        });
        setTimeout(function () {
          window.removeEventListener("resize", refit);
          loaded.img.remove();
          URL.revokeObjectURL(loaded.url);
          busy = false;
          goGuess(n, false);
        }, DISPLAY_MS);
      })
      .catch(function (error) {
        busy = false;
        if (error && error.code === "image_expired") {
          goGuess(n, true);
          flashError(T.errors.image_expired);
          return;
        }
        if (error && error.code === "network") {
          goReady(n);
          flashError(T.errors.network);
          return;
        }
        fail(error);
      });
  }

  function submitGuess(event) {
    event.preventDefault();
    if (busy) return;
    var input = document.getElementById("guess-input");
    var raw = input.value.trim();
    var guess = Number(raw);
    var error = document.getElementById("guess-error");
    if (raw === "" || !Number.isInteger(guess) || guess < 0 || guess > 9999) {
      error.textContent = T.guessRequired;
      error.hidden = false;
      input.focus();
      return;
    }
    error.hidden = true;
    busy = true;
    var n = state.next_round;
    api("/rounds/" + n + "/answer", { guess: guess })
      .then(function (data) {
        busy = false;
        state = data.state;
        goReveal(data.round);
      })
      .catch(fail);
  }

  function gapText(gap) {
    if (gap === 0) return T.exact;
    return fmt(gap > 0 ? T.tooMany : T.tooFew, { n: Math.abs(gap) });
  }

  function goReveal(round) {
    field("reveal-gap").textContent = gapText(round.gap);
    field("reveal-gap").classList.toggle("is-exact", round.gap === 0);
    field("reveal-guess").textContent = round.guess;
    field("reveal-count").textContent = round.count;
    root.querySelector('[data-action="next"]').textContent =
      state.status === "completed" ? T.seeResult : T.nextRound;
    renderProgress(round.index);
    show("reveal");
  }

  function goResult() {
    document.getElementById("progress").hidden = true;
    var score = state.score;
    field("score").textContent = score;
    field("score-label").textContent =
      score === 0 ? T.scorePerfect : score === 1 ? T.scoreLabelOne : T.scoreLabel;

    var rows = field("rounds");
    rows.innerHTML = "";
    state.rounds.forEach(function (r) {
      var tr = document.createElement("tr");
      [r.index, r.guess, r.count, Math.abs(r.gap)].forEach(function (value) {
        var td = document.createElement("td");
        td.textContent = value;
        tr.appendChild(td);
      });
      rows.appendChild(tr);
    });

    var ranking = state.ranking || {};
    var rankingText = "";
    var hasPercent = ranking.ranked && ranking.top_percent !== null && ranking.top_percent !== undefined;
    if (!ranking.ranked) rankingText = T.notRanked;
    else if (hasPercent) rankingText = fmt(T.topPercent, { p: ranking.top_percent, players: ranking.players });
    else if (ranking.players <= 1) rankingText = fmt(T.firstPlayer, { min: ranking.min_players });
    else rankingText = fmt(T.firstPlayers, { players: ranking.players, min: ranking.min_players });
    field("ranking").textContent = rankingText;
    field("ranking").classList.toggle("is-pending", !hasPercent);

    var cta = field("account-cta");
    cta.innerHTML = "";
    var link = document.createElement("a");
    if (root.dataset.authenticated === "true") {
      link.href = root.dataset.historyUrl;
      link.textContent = T.historyLink;
      cta.appendChild(link);
    } else {
      link.href = root.dataset.signupUrl;
      link.textContent = T.signupLink;
      cta.appendChild(document.createTextNode(T.signupCta + " "));
      cta.appendChild(link);
    }

    updateCountdown();
    clearInterval(countdownTimer);
    countdownTimer = setInterval(updateCountdown, 30000);
    show("result");
  }

  function updateCountdown() {
    var ms = new Date(state.edition.ends_at).getTime() - Date.now();
    var el = field("countdown");
    if (ms <= 0) {
      clearInterval(countdownTimer);
      window.location.reload();
      return;
    }
    var minutes = Math.floor(ms / 60000);
    el.textContent = minutes < 1
      ? T.countdownSoon
      : fmt(T.countdown, { h: Math.floor(minutes / 60), m: minutes % 60 });
  }

  // --- sharing -------------------------------------------------------------

  function shareText() {
    var lines = [fmt(T.shareTitle, { number: state.edition.number }) + " 🍌"];
    state.rounds.forEach(function (r) {
      lines.push(fmt(T.shareRound, { n: r.index, gap: Math.abs(r.gap) }) + (r.gap === 0 ? " 🎯" : ""));
    });
    var total = fmt(T.shareTotal, { score: state.score });
    if (state.ranking && state.ranking.top_percent !== null && state.ranking.top_percent !== undefined) {
      total += " · " + fmt(T.shareTop, { p: state.ranking.top_percent });
    }
    lines.push(total);
    lines.push(T.shareChallenge + " " + window.SITE_URL + "/");
    return lines.join("\n");
  }

  function toast(message, fallbackText) {
    var el = document.getElementById("toast");
    el.textContent = message;
    if (fallbackText) {
      var area = document.createElement("textarea");
      area.readOnly = true;
      area.value = fallbackText;
      area.rows = 6;
      el.appendChild(area);
      area.select();
    }
    el.hidden = false;
  }

  function share() {
    var text = shareText();
    var touch = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
    if (navigator.share && touch) {
      navigator.share({ text: text }).catch(function () { /* cancelled by the player */ });
      return;
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(
        function () { toast(T.copied); },
        function () { toast(T.copyFailed, text); }
      );
      return;
    }
    toast(T.copyFailed, text);
  }

  // --- wiring --------------------------------------------------------------

  root.addEventListener("click", function (event) {
    var button = event.target.closest("[data-action]");
    if (!button) return;
    var action = button.dataset.action;
    if (action === "start") {
      if (busy) return;
      busy = true;
      api("/start", {})
        .then(function (data) { busy = false; state = data; resume(); })
        .catch(fail);
    } else if (action === "show") {
      showBananas();
    } else if (action === "next") {
      if (state.status === "completed") goResult();
      else goReady(state.next_round);
    } else if (action === "share") {
      share();
    } else if (action === "reload") {
      window.location.reload();
    }
  });

  document.getElementById("guess-form").addEventListener("submit", submitGuess);

  function resume() {
    if (state.status === "completed") return goResult();
    if (state.status === "in_progress") {
      if (state.awaiting_answer) return goGuess(state.next_round, true);
      return goReady(state.next_round);
    }
    show("intro");
  }

  resume();
})();
