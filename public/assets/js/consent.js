/* thr33.xyz: consentimento de cookies e Google Analytics 4.

   - Consent Mode v2 com tudo denied por defeito; o gtag.js só se pede depois de aceitar.
   - A escolha fica no cookie thr33_consent (6 meses), não no armazenamento do browser.
   - Recusar tem o mesmo peso que aceitar; ao recusar depois de aceitar, apagam-se os cookies _ga.
   - Publicidade sempre desligada: ad_storage, ad_user_data e ad_personalization ficam denied.
   Sem este ficheiro (ou sem JS) não há banner nem GA, e o site funciona na íntegra. */
(function () {
  var GA_ID = "G-JCJZ754SWW";
  var COOKIE = "thr33_consent";
  var MAX_AGE = 60 * 60 * 24 * 180;

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag("consent", "default", {
    ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied", analytics_storage: "denied"
  });

  function readChoice() {
    var m = document.cookie.match(new RegExp("(?:^|; )" + COOKIE + "=(granted|denied)"));
    return m ? m[1] : null;
  }

  function saveChoice(value) {
    var secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie = COOKIE + "=" + value + "; max-age=" + MAX_AGE + "; path=/; SameSite=Lax" + secure;
  }

  var loaded = false;
  function loadAnalytics() {
    if (loaded) return;
    loaded = true;
    gtag("consent", "update", { analytics_storage: "granted" });
    gtag("js", new Date());
    gtag("config", GA_ID, { allow_google_signals: false, allow_ad_personalization_signals: false });
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    document.head.appendChild(s);
  }

  /* Apaga _ga e _ga_<ID> no domínio actual e no domínio de topo (.thr33.xyz), onde o GA os põe. */
  function clearAnalyticsCookies() {
    var host = location.hostname;
    var domains = ["", "; domain=" + host, "; domain=." + host.split(".").slice(-2).join(".")];
    document.cookie.split("; ").forEach(function (pair) {
      var name = pair.split("=")[0];
      if (name !== "_ga" && name.indexOf("_ga_") !== 0) return;
      domains.forEach(function (d) {
        document.cookie = name + "=; max-age=0; path=/" + d;
      });
    });
  }

  if (readChoice() === "granted") loadAnalytics();

  document.addEventListener("DOMContentLoaded", function () {
    var banner = document.getElementById("cookie-banner");
    if (!banner) return;
    var opener = null;

    function show(from) {
      opener = from || null;
      banner.hidden = false;
      if (opener) banner.querySelector("button").focus();
    }

    function hide() {
      banner.hidden = true;
      if (opener) opener.focus();
      opener = null;
    }

    Array.prototype.forEach.call(banner.querySelectorAll("[data-consent]"), function (btn) {
      btn.addEventListener("click", function () {
        var value = btn.getAttribute("data-consent");
        saveChoice(value);
        if (value === "granted") {
          loadAnalytics();
        } else {
          gtag("consent", "update", { analytics_storage: "denied" });
          clearAnalyticsCookies();
        }
        hide();
      });
    });

    banner.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && opener) hide();
    });

    Array.prototype.forEach.call(document.querySelectorAll("[data-consent-open]"), function (btn) {
      btn.parentNode.hidden = false;
      btn.addEventListener("click", function () { show(btn); });
    });

    if (!readChoice()) show();
  });
})();
