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

/* Espectro do hero (#63): cada mancha vai de um ponto aleatório a outro por uma curva (Bézier quadrática com
   um ponto de controlo também aleatório), cada perna em 25 a 40 s, até ~35% do hero para cada lado; e a camada
   cónica roda uma volta em 90 s. Só transform e opacity (Web Animations). A opacidade nunca passa a do CSS, por
   causa do contraste do texto. Pára quando o hero sai do ecrã ou o separador fica escondido, e não corre com
   reduced motion (fica tudo parado). */
function driftBlobs(hero) {
  var blobs = hero.querySelectorAll(".blob"), spectrum = hero.querySelector(".spectrum");
  if (reducedMotion || !blobs.length || !blobs[0].animate || !("IntersectionObserver" in window)) return;
  var onScreen = true, running = [];
  function rand(min, max) { return min + Math.random() * (max - min); }
  function point() {
    var r = hero.getBoundingClientRect();
    return { x: rand(-0.35, 0.35) * r.width, y: rand(-0.35, 0.35) * r.height, s: rand(0.85, 1.25), o: rand(0.75, 1) };
  }
  function curve(a, b, base) {
    var c = point(), frames = [];
    for (var k = 0; k <= 8; k++) {
      var t = k / 8, u = 1 - t;
      var x = u * u * a.x + 2 * u * t * c.x + t * t * b.x, y = u * u * a.y + 2 * u * t * c.y + t * t * b.y;
      frames.push({
        transform: "translate3d(" + x.toFixed(1) + "px, " + y.toFixed(1) + "px, 0) scale(" + (a.s + (b.s - a.s) * t).toFixed(3) + ")",
        opacity: (base * (a.o + (b.o - a.o) * t)).toFixed(3)
      });
    }
    return frames;
  }
  function live() { return onScreen && !document.hidden; }
  Array.prototype.forEach.call(blobs, function (blob, i) {
    var base = parseFloat(getComputedStyle(blob).opacity) || 0.5;
    var from = { x: 0, y: 0, s: 1, o: 1 };
    (function leg() {
      var to = point();
      var anim = blob.animate(curve(from, to, base), { duration: rand(25000, 40000), easing: "ease-in-out", fill: "forwards" });
      if (running[i]) running[i].cancel();
      running[i] = anim;
      if (!live()) anim.pause();
      anim.onfinish = function () { from = to; leg(); };
    })();
  });
  if (spectrum) {
    running.push(spectrum.animate([{ transform: "rotate(0deg)" }, { transform: "rotate(360deg)" }], { duration: 90000, iterations: Infinity }));
  }
  function sync() { running.forEach(function (a) { if (live()) a.play(); else a.pause(); }); }
  new IntersectionObserver(function (entries) { onScreen = entries[0].isIntersecting; sync(); }).observe(hero);
  document.addEventListener("visibilitychange", sync);
}

/* Cartões de projeto (#63): o cartão não mexe, só a ilustração. Com .is-playing no cartão, o site.css anima as
   peças do SVG uma vez (até 1,2 s). Corre no hover do rato e no foco do teclado; em ecrã tátil corre uma vez
   quando o cartão entra no ecrã (50% visível), e tocar na ilustração repete sem seguir o link. Nada disto com
   reduced motion: a ilustração fica parada e completa, como sem JS. */
var CARD_PLAY_MS = 1300;
function playCards() {
  var cards = document.querySelectorAll(".card-project");
  if (reducedMotion || !cards.length) return;
  function play(card) {
    clearTimeout(card._playTimer);
    card.classList.remove("is-playing");
    void card.offsetWidth; /* recomeça as animações do início */
    card.classList.add("is-playing");
    card._playTimer = setTimeout(function () { card.classList.remove("is-playing"); }, CARD_PLAY_MS);
  }
  var touch = window.matchMedia("(hover: none)").matches;
  Array.prototype.forEach.call(cards, function (card) {
    card.addEventListener("pointerenter", function (e) { if (e.pointerType === "mouse") play(card); });
    card.addEventListener("focusin", function () { play(card); });
    var media = card.querySelector("[data-art]");
    if (touch && media) {
      media.addEventListener("click", function (e) { e.preventDefault(); play(card); });
    }
  });
  if (!touch || !("IntersectionObserver" in window)) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      io.unobserve(e.target);
      play(e.target);
    });
  }, { threshold: 0.5 });
  Array.prototype.forEach.call(cards, function (card) { io.observe(card); });
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

/* Reveal em cascata nos grupos [data-reveal] abaixo da dobra: filhos sobem com 100 ms entre si
   e os ícones desenham o traço. Os que já estão visíveis ao carregar não mexem. */
function revealGroups() {
  if (reducedMotion || !("IntersectionObserver" in window)) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      io.unobserve(e.target);
      e.target.classList.add("is-in");
    });
  }, { rootMargin: "0px 0px -10% 0px" });
  Array.prototype.forEach.call(document.querySelectorAll("[data-reveal]"), function (group) {
    if (group.getBoundingClientRect().top < window.innerHeight) return;
    Array.prototype.forEach.call(group.children, function (child, i) { child.style.setProperty("--i", String(i)); });
    group.classList.add("reveal");
    io.observe(group);
    /* Com Tab, o elemento focado não pode ficar invisível à espera da animação: o grupo aparece já. */
    group.addEventListener("focusin", function () {
      io.unobserve(group);
      group.classList.remove("reveal");
    }, { once: true });
  });
}

/* Cenas de cor: quando uma secção passa o meio do ecrã, a página inteira veste a cor dela
   (data-scene no <html>). Sem esta função, cada secção já tem a sua cor fixa (.scene-*). */
function colourScenes() {
  if (reducedMotion || !("IntersectionObserver" in window)) return;
  var root = document.documentElement;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      var scene = e.target.getAttribute("data-scene");
      if (scene) root.setAttribute("data-scene", scene); else root.removeAttribute("data-scene");
    });
  }, { rootMargin: "-49% 0px -49% 0px" });
  Array.prototype.forEach.call(document.querySelectorAll("main > *, .site-footer"), function (el) { io.observe(el); });
  root.classList.add("scenes");
}

/* CTA final: o título cresce de 0.8 para 1 enquanto a secção sobe do fundo até ao meio do ecrã.
   Só transform (sem saltos de layout); sem JS ou com reduced motion fica a 1. */
function ctaScale(el) {
  if (reducedMotion) return;
  var frame = 0;
  function update() {
    frame = 0;
    var vh = window.innerHeight, top = el.getBoundingClientRect().top;
    var k = Math.min(Math.max((vh - top) / (vh * 0.5), 0), 1);
    el.style.setProperty("--cta-scale", (0.8 + 0.2 * k).toFixed(3));
  }
  window.addEventListener("scroll", function () { if (!frame) frame = requestAnimationFrame(update); }, { passive: true });
  window.addEventListener("resize", update);
  update();
}

/* Botão principal magnético: segue um pouco o rato, só em desktop com rato. */
function magneticButtons() {
  if (reducedMotion || !window.matchMedia("(pointer: fine) and (min-width: 48rem)").matches) return;
  Array.prototype.forEach.call(document.querySelectorAll(".btn-primary"), function (btn) {
    btn.addEventListener("pointermove", function (e) {
      var r = btn.getBoundingClientRect();
      btn.style.setProperty("--tx", ((e.clientX - r.left - r.width / 2) * 0.15).toFixed(1) + "px");
      btn.style.setProperty("--ty", ((e.clientY - r.top - r.height / 2) * 0.25).toFixed(1) + "px");
    });
    btn.addEventListener("pointerleave", function () {
      btn.style.setProperty("--tx", "0px");
      btn.style.setProperty("--ty", "0px");
    });
  });
}

document.addEventListener("DOMContentLoaded", function () {
  if (!reducedMotion) Array.prototype.forEach.call(document.querySelectorAll("[data-split]"), splitLines);
  revealGroups();
  colourScenes();
  playCards();
  magneticButtons();
  Array.prototype.forEach.call(document.querySelectorAll("[data-cta-scale]"), ctaScale);
  Array.prototype.forEach.call(document.querySelectorAll("[data-marquee]"), marqueeScroll);
  countLabels();
  var hero = document.querySelector(".hero");
  if (hero) { followPointer(hero); driftBlobs(hero); }

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
