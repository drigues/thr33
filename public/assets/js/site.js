/* thr33.xyz: melhoria progressiva. Sem este ficheiro o site lê-se e navega-se na íntegra. */
document.documentElement.classList.add("js");

document.addEventListener("DOMContentLoaded", function () {
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
