/* thr33.xyz: melhoria progressiva. Sem este ficheiro o site lê-se e navega-se na íntegra. */
document.documentElement.classList.add("js");

var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* Reveal por linhas: cada palavra fica numa máscara (.w > .wi) com --line = linha em que caiu.
   O <h1> guarda o texto original em aria-label. Com reduced motion não se parte nada. */
function splitLines(el) {
  var text = el.textContent.replace(/\s+/g, " ").trim();
  (function walk(node) {
    Array.prototype.slice.call(node.childNodes).forEach(function (child) {
      if (child.nodeType === 1) { walk(child); return; }
      if (child.nodeType !== 3) return;
      var frag = document.createDocumentFragment();
      child.textContent.split(/(\s+)/).forEach(function (part) {
        if (!part) return;
        if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(" ")); return; }
        var w = document.createElement("span"), wi = document.createElement("span");
        w.className = "w"; wi.className = "wi"; wi.textContent = part;
        w.appendChild(wi); frag.appendChild(w);
      });
      node.replaceChild(frag, child);
    });
  })(el);
  el.setAttribute("aria-label", text);
  var top = null, line = -1;
  Array.prototype.forEach.call(el.querySelectorAll(".w"), function (w) {
    var t = w.getBoundingClientRect().top;
    if (top === null || Math.abs(t - top) > 2) { line += 1; top = t; }
    w.firstChild.style.setProperty("--line", String(Math.min(line, 3)));
  });
  el.classList.add("split");
  requestAnimationFrame(function () { requestAnimationFrame(function () { el.classList.add("is-in"); }); });
}

/* Gradiente-assinatura: segue um pouco o rato (só com rato e sem reduced motion). */
function followPointer(hero) {
  var grad = hero.querySelector(".hero-gradient");
  if (!grad || reducedMotion || !window.matchMedia("(pointer: fine)").matches) return;
  var last = null, frame = 0;
  hero.addEventListener("pointermove", function (e) {
    last = e;
    if (frame) return;
    frame = requestAnimationFrame(function () {
      frame = 0;
      var r = hero.getBoundingClientRect();
      grad.style.setProperty("--mx", ((last.clientX - r.left) / r.width * 2 - 1).toFixed(3));
      grad.style.setProperty("--my", ((last.clientY - r.top) / r.height * 2 - 1).toFixed(3));
    });
  });
}

/* Marquee: a velocidade sobe com a velocidade do scroll e o sentido segue o do scroll;
   depois volta devagar à velocidade base. O loop em si é a animação CSS. */
function marqueeScroll(el) {
  var track = el.querySelector(".marquee-track");
  var anim = track && track.getAnimations ? track.getAnimations()[0] : null;
  if (!anim || reducedMotion) return;
  var lastY = window.scrollY, lastT = performance.now(), dir = 1, rate = 1, target = 1, frame = 0;
  function tick() {
    rate += (target - rate) * 0.1;
    target += (dir - target) * 0.05;
    anim.playbackRate = rate;
    frame = Math.abs(rate - dir) > 0.01 || Math.abs(target - dir) > 0.01 ? requestAnimationFrame(tick) : 0;
  }
  window.addEventListener("scroll", function () {
    var y = window.scrollY, t = performance.now(), dy = y - lastY, dt = Math.max(t - lastT, 16);
    lastY = y; lastT = t;
    if (!dy) return;
    dir = dy > 0 ? 1 : -1;
    target = dir * (1 + Math.min(Math.abs(dy) / dt * 2, 4));
    if (!frame) frame = requestAnimationFrame(tick);
  }, { passive: true });
}

/* Etiquetas (01): abaixo da dobra, o número conta de 00 até ao valor quando entra no ecrã. */
function countLabels() {
  if (reducedMotion || !("IntersectionObserver" in window)) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      io.unobserve(e.target);
      var el = e.target, to = Number(el.dataset.to), start = performance.now();
      (function step(now) {
        var k = Math.min((now - start) / 400, 1);
        el.textContent = "(" + String(Math.round(to * k)).padStart(2, "0") + ")";
        if (k < 1) requestAnimationFrame(step);
      })(start);
    });
  }, { threshold: 1 });
  Array.prototype.forEach.call(document.querySelectorAll(".label-num"), function (el) {
    var to = parseInt(el.textContent.replace(/\D/g, ""), 10);
    if (!to || el.getBoundingClientRect().top < window.innerHeight) return;
    el.dataset.to = String(to);
    el.textContent = "(00)";
    io.observe(el);
  });
}

document.addEventListener("DOMContentLoaded", function () {
  if (!reducedMotion) Array.prototype.forEach.call(document.querySelectorAll("[data-split]"), splitLines);
  Array.prototype.forEach.call(document.querySelectorAll("[data-marquee]"), marqueeScroll);
  countLabels();
  var hero = document.querySelector(".hero");
  if (hero) followPointer(hero);

  var header = document.querySelector("[data-header]");
  if (!header) return;
  var toggle = header.querySelector(".menu-toggle");
  var menu = toggle && document.getElementById(toggle.getAttribute("aria-controls"));
  var isOpen = function () { return toggle && toggle.getAttribute("aria-expanded") === "true"; };

  /* Menu de ecrã inteiro (mobile): foco entra ao abrir, Esc fecha, foco volta ao botão. */
  if (toggle && menu) {
    var links = function () { return Array.prototype.slice.call(menu.querySelectorAll("a")); };
    var setOpen = function (open, moveFocus) {
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? toggle.dataset.labelClose : toggle.dataset.labelOpen);
      menu.classList.toggle("is-open", open);
      document.documentElement.classList.toggle("menu-open", open);
      if (moveFocus === false) return;
      if (open && links()[0]) links()[0].focus();
      if (!open) toggle.focus();
    };
    toggle.addEventListener("click", function () { setOpen(!isOpen()); });
    document.addEventListener("keydown", function (e) {
      if (!isOpen()) return;
      if (e.key === "Escape") { e.preventDefault(); setOpen(false); return; }
      if (e.key !== "Tab") return;
      var items = [toggle].concat(links());
      var first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    var desktop = window.matchMedia("(min-width: 48rem)");
    var onChange = function (e) { if (e.matches && isOpen()) setOpen(false, false); };
    if (desktop.addEventListener) desktop.addEventListener("change", onChange);
  }

  /* Cabeçalho: esconde ao descer, volta ao subir ou quando recebe foco. */
  var last = window.scrollY;
  window.addEventListener("scroll", function () {
    var y = window.scrollY;
    var hide = y > last && y > header.offsetHeight && !isOpen() && !header.contains(document.activeElement);
    header.classList.toggle("is-hidden", hide);
    last = y;
  }, { passive: true });
  header.addEventListener("focusin", function () { header.classList.remove("is-hidden"); });
});
