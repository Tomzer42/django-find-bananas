// Loads Google Analytics only after the visitor agrees. The choice is kept
// in localStorage; nothing is loaded before it.
(function () {
  "use strict";
  var KEY = "fb-analytics-consent";
  var idEl = document.getElementById("ga-id");
  var banner = document.getElementById("consent");
  if (!idEl || !banner) return;
  var gaId = JSON.parse(idEl.textContent);

  function read() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function write(value) {
    try { localStorage.setItem(KEY, value); } catch (e) { /* private mode */ }
  }
  function loadAnalytics() {
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(gaId);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", gaId, { anonymize_ip: true });
  }

  var choice = read();
  if (choice === "yes") { loadAnalytics(); return; }
  if (choice === "no") return;

  banner.hidden = false;
  banner.addEventListener("click", function (event) {
    var button = event.target.closest("[data-consent]");
    if (!button) return;
    write(button.dataset.consent);
    banner.hidden = true;
    if (button.dataset.consent === "yes") loadAnalytics();
  });
})();
