/* Alunites — interactions du site (sans dépendance). */
(() => {
  "use strict";
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => [...c.querySelectorAll(s)];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- En-tête : fond plein au défilement ---------- */
  const header = $("[data-header]");
  if (header) {
    const onScroll = () => header.classList.toggle("is-solid", window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- Menu mobile ---------- */
  const toggle = $("[data-menu-toggle]");
  const menu = $("[data-menu]");
  if (toggle && menu) {
    const setOpen = (open) => {
      toggle.setAttribute("aria-expanded", String(open));
      toggle.querySelector(".menu-toggle__label").textContent = open ? "Fermer" : "Menu";
      menu.hidden = !open;
      document.body.classList.toggle("menu-open", open);
      if (open) menu.querySelector("a")?.focus();
    };
    toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") { setOpen(false); toggle.focus(); }
    });
  }

  /* ---------- Accueil : vidéo de fond pilotée par la liste « À la une » ---------- */
  const hero = $("[data-hero]");
  if (hero) {
    const video = $("[data-hero-video]", hero);
    const items = $$(".hero__item", hero);
    const pauseBtn = $("[data-hero-toggle]", hero);
    let paused = reduceMotion;
    const play = () => { if (video && !paused) video.play().catch(() => {}); };
    const show = (src) => {
      if (!video || !src || video.dataset.current === src) return;
      video.classList.remove("is-ready");
      video.dataset.current = src;
      video.src = src;
      play();
    };
    if (video) {
      video.addEventListener("playing", () => video.classList.add("is-ready"));
      if (!reduceMotion) show(video.dataset.src);
    }
    items.forEach((item) => {
      const activate = () => {
        items.forEach((i) => i.classList.toggle("is-active", i === item));
        show(item.dataset.video);
      };
      item.addEventListener("mouseenter", activate);
      item.addEventListener("focus", activate);
    });
    if (pauseBtn) {
      if (!video) pauseBtn.hidden = true;
      const label = () => {
        pauseBtn.textContent = paused ? "Lire la vidéo" : "Mettre la vidéo en pause";
        pauseBtn.setAttribute("aria-pressed", String(paused));
      };
      label();
      pauseBtn.addEventListener("click", () => {
        paused = !paused;
        if (paused) video?.pause();
        else { if (!video.dataset.current) show(video.dataset.src); play(); }
        label();
      });
    }
  }

  /* ---------- Lecteurs vidéo (clic sur la vignette) ---------- */
  $$("[data-video]").forEach((fig) => {
    const btn = $("[data-video-play]", fig);
    btn?.addEventListener("click", () => {
      const el = $("video", fig);
      if (el) {
        el.hidden = false;
        fig.classList.add("is-playing");
        el.play().catch(() => {});
        el.focus();
        return;
      }
      const tpl = $("template[data-video-embed]", fig);
      if (tpl) {
        fig.appendChild(tpl.content.cloneNode(true));
        fig.classList.add("is-playing");
      }
    });
  });

  /* ---------- Galeries (défilement horizontal) ---------- */
  $$("[data-slider]").forEach((slider) => {
    const track = $("[data-slider-track]", slider);
    const slides = $$(".slider__item", slider);
    const count = $("[data-slider-count]", slider);
    if (!track || slides.length < 2) return;
    const current = () => {
      const left = track.scrollLeft;
      let idx = 0;
      slides.forEach((s, i) => { if (Math.abs(s.offsetLeft - track.offsetLeft - left - parseFloat(getComputedStyle(track).paddingLeft)) < s.offsetWidth / 2) idx = i; });
      return idx;
    };
    const go = (i) => {
      const n = (i + slides.length) % slides.length;
      track.scrollTo({ left: slides[n].offsetLeft - slides[0].offsetLeft, behavior: reduceMotion ? "auto" : "smooth" });
    };
    $("[data-slider-prev]", slider)?.addEventListener("click", () => go(current() - 1));
    $("[data-slider-next]", slider)?.addEventListener("click", () => go(current() + 1));
    track.addEventListener("scroll", () => { if (count) count.textContent = `${current() + 1} / ${slides.length}`; }, { passive: true });
    track.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") { e.preventDefault(); go(current() + 1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); go(current() - 1); }
    });
  });

  /* ---------- Bandeau de logos : bouton pause / lecture ---------- */
  $$("[data-marquee-toggle]").forEach((btn) => {
    const marquee = document.getElementById(btn.getAttribute("aria-controls"));
    if (!marquee) return;
    btn.addEventListener("click", () => {
      const paused = marquee.classList.toggle("is-paused");
      btn.setAttribute("aria-pressed", String(paused));
      btn.textContent = paused ? "Relancer le défilement" : "Mettre en pause";
    });
  });

  /* ---------- Filtres des listes (projets / actualités) ---------- */
  $$("[data-filters]").forEach((group) => {
    const attr = group.dataset.filterAttr;
    const param = group.dataset.filterParam;
    const list = $("[data-filter-list]");
    const empty = $("[data-filter-empty]");
    const buttons = $$("[data-filter]", group);
    const apply = (value, push) => {
      let visible = 0;
      $$(".card", list).forEach((card) => {
        const ok = !value || (card.dataset[attr] || "").split(" ").includes(value);
        card.hidden = !ok;
        if (ok) visible++;
      });
      buttons.forEach((b) => {
        const on = b.dataset.filter === value;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-pressed", String(on));
      });
      if (empty) empty.hidden = visible > 0;
      if (push) {
        const url = new URL(location.href);
        value ? url.searchParams.set(param, value) : url.searchParams.delete(param);
        history.replaceState(null, "", url);
      }
    };
    buttons.forEach((b) => b.addEventListener("click", () => apply(b.dataset.filter, true)));
    const initial = new URL(location.href).searchParams.get(param);
    if (initial && buttons.some((b) => b.dataset.filter === initial)) apply(initial, false);
  });

  /* ---------- Contact : boussole à mantras ---------- */
  const compass = $("[data-compass]");
  if (compass) {
    const mantras = $$(".compass__mantra", compass);
    const dial = $(".rosace__g", compass);
    let turn = 0, idx = 0;
    $("[data-compass-spin]", compass)?.addEventListener("click", () => {
      let next = idx;
      while (mantras.length > 1 && next === idx) next = Math.floor(Math.random() * mantras.length);
      idx = next;
      turn += 540 + Math.floor(Math.random() * 4) * 90;
      if (dial) dial.style.setProperty("--turn", `${turn}deg`);
      const reveal = () => mantras.forEach((m, i) => { m.hidden = i !== idx; m.classList.toggle("is-active", i === idx); });
      reduceMotion ? reveal() : setTimeout(reveal, 900);
    });
  }

  /* ---------- Contact : envoi du formulaire ---------- */
  const form = $("[data-contact-form]");
  if (form) {
    const status = $("[data-form-status]", form);
    const ts = $("[data-ts]", form);
    if (ts) ts.value = String(Date.now());
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      let valid = true;
      $$("[required]", form).forEach((f) => {
        const ok = f.value.trim() !== "" && (f.type !== "email" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.value.trim()));
        f.setAttribute("aria-invalid", String(!ok));
        if (!ok) valid = false;
      });
      if (!valid) {
        status.className = "form__status is-error";
        status.textContent = "Merci de renseigner votre nom, une adresse e-mail valide et votre message.";
        $("[aria-invalid='true']", form)?.focus();
        return;
      }
      const btn = $("button[type=submit]", form);
      btn.disabled = true;
      status.className = "form__status";
      status.textContent = "Envoi en cours…";
      try {
        const res = await fetch(form.action, { method: "POST", body: new FormData(form), headers: { Accept: "application/json" } });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) throw new Error(data.message || "");
        form.reset();
        status.className = "form__status is-success";
        status.textContent = status.dataset.success;
      } catch (err) {
        status.className = "form__status is-error";
        status.textContent = err.message || status.dataset.error;
      } finally {
        btn.disabled = false;
        if (ts) ts.value = String(Date.now());
      }
    });
  }

  /* ---------- Consentement + Google Analytics 4 ---------- */
  const consent = $("[data-consent]");
  const KEY = "alunites-consent";
  const read = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
  const write = (v) => { try { localStorage.setItem(KEY, v); } catch { /* navigation privée */ } };
  const loadGA = (id) => {
    if (!id || window.__gaLoaded) return;
    window.__gaLoaded = true;
    const s = document.createElement("script");
    s.async = true;
    s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", id, { anonymize_ip: true });
  };
  if (consent) {
    const id = consent.dataset.ga;
    const choice = read();
    if (choice === "accept") loadGA(id);
    if (!choice) consent.hidden = false;
    $$("[data-consent-choice]", consent).forEach((b) => b.addEventListener("click", () => {
      const v = b.dataset.consentChoice;
      write(v);
      consent.hidden = true;
      if (v === "accept") loadGA(id);
      else {
        // Retire les cookies Google Analytics éventuellement déposés lors d'un accord précédent
        document.cookie.split(";").map((c) => c.trim().split("=")[0]).filter((n) => /^_ga/.test(n)).forEach((n) => {
          const host = location.hostname.replace(/^www\./, "");
          document.cookie = `${n}=; Max-Age=0; path=/; domain=.${host}`;
          document.cookie = `${n}=; Max-Age=0; path=/`;
        });
        if (window.__gaLoaded) location.reload();
      }
    }));
    $$("[data-consent-open]").forEach((b) => b.addEventListener("click", () => { consent.hidden = false; $("button", consent)?.focus(); }));
  }
})();
