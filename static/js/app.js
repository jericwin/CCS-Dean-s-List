/* CCS Dean's List — shared UI behaviour. No framework; progressive enhancement only. */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const csrf = () => (document.querySelector('meta[name="csrf-token"]') || {}).content || "";

  const ICONS = { success: "fa-circle-check", danger: "fa-circle-exclamation", error: "fa-circle-exclamation", warning: "fa-triangle-exclamation", info: "fa-circle-info" };

  /* ------------------------------------------------------------ toasts */
  function toast(message, type = "info", timeout = 4500) {
    let stack = $("#toasts");
    if (!stack) {
      stack = document.createElement("div");
      stack.id = "toasts";
      stack.className = "toast-stack";
      document.body.appendChild(stack);
    }
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.setAttribute("role", type === "danger" || type === "error" ? "alert" : "status");
    el.innerHTML = `<i class="fas ${ICONS[type] || ICONS.info} toast-icon" aria-hidden="true"></i><div class="toast-body"></div><button class="toast-close" type="button" aria-label="Dismiss"><i class="fas fa-xmark"></i></button>`;
    $(".toast-body", el).textContent = message;
    stack.appendChild(el);
    const remove = () => {
      if (el.classList.contains("is-leaving")) return;
      el.classList.add("is-leaving");
      setTimeout(() => el.remove(), 250);
    };
    $(".toast-close", el).addEventListener("click", remove);
    if (timeout) setTimeout(remove, timeout);
    return el;
  }

  function toastAfterReload(message, type = "success") {
    try { sessionStorage.setItem("fox:toast", JSON.stringify([type, message])); } catch (_) { /* storage unavailable */ }
  }

  /* ------------------------------------------------------------ fetch */
  async function api(url, { method = "GET", body, json } = {}) {
    const headers = { "X-Requested-With": "fetch", Accept: "application/json" };
    if (method !== "GET") headers["X-CSRFToken"] = csrf();
    let payload = body;
    if (json !== undefined) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(json);
    }
    let res;
    try {
      res = await fetch(url, { method, headers, body: payload, credentials: "same-origin" });
    } catch (err) {
      throw new Error("Network error — check your connection and try again.");
    }
    let data = null;
    const type = res.headers.get("content-type") || "";
    if (type.includes("application/json")) data = await res.json();
    if (!res.ok) {
      if (res.status === 401) {
        window.location.href = "/login";
      }
      throw new Error((data && data.error) || `Request failed (${res.status}).`);
    }
    return data;
  }

  /* ------------------------------------------------------------ modals */
  let lastFocus = null;
  function openModal(target) {
    const modal = typeof target === "string" ? document.getElementById(target) : target;
    if (!modal) return;
    lastFocus = document.activeElement;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    const focusable = modal.querySelector("[autofocus], input:not([type=hidden]), select, textarea, button:not([data-modal-close])");
    if (focusable) setTimeout(() => focusable.focus(), 60);
    modal.dispatchEvent(new CustomEvent("modal:open"));
  }
  function closeModal(target) {
    const modal = typeof target === "string" ? document.getElementById(target) : target;
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    if (!$(".modal.is-open")) document.body.classList.remove("modal-open");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
    modal.dispatchEvent(new CustomEvent("modal:close"));
  }

  function confirmDialog({ title = "Are you sure?", message = "", confirmText = "Confirm", tone = "danger" } = {}) {
    const modal = $("#confirmModal");
    if (!modal) return Promise.resolve(window.confirm(message || title));
    $("[data-confirm-title]", modal).textContent = title;
    $("[data-confirm-message]", modal).textContent = message;
    const ok = $("[data-confirm-ok]", modal);
    ok.textContent = confirmText;
    ok.className = `btn ${tone === "danger" ? "btn-danger" : "btn-primary"}`;
    openModal(modal);
    return new Promise((resolve) => {
      const done = (value) => {
        ok.removeEventListener("click", onOk);
        modal.removeEventListener("modal:close", onClose);
        resolve(value);
      };
      const onOk = () => { done(true); closeModal(modal); };
      const onClose = () => done(false);
      ok.addEventListener("click", onOk);
      modal.addEventListener("modal:close", onClose);
    });
  }

  /* ------------------------------------------------------------ helpers */
  function setLoading(button, on) {
    if (!button) return;
    button.classList.toggle("is-loading", on);
    button.disabled = on;
  }
  function formatBytes(n) {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
    return `${(n / 1024 / 1024).toFixed(1)} MB`;
  }
  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function setBadge(id, count) {
    $$(`[data-badge="${id}"]`).forEach((el) => {
      el.textContent = count > 99 ? "99+" : String(count);
      el.hidden = !count;
    });
  }
  function bumpBadge(id, by = 1) {
    const el = $(`[data-badge="${id}"]`);
    const current = el ? parseInt(el.textContent, 10) || 0 : 0;
    setBadge(id, Math.max(0, current + by));
  }

  /* ------------------------------------------------------------ init: shell */
  function initShell() {
    const body = document.body;
    $$("[data-nav-toggle]").forEach((btn) =>
      btn.addEventListener("click", () => {
        const open = !body.classList.contains("nav-open");
        body.classList.toggle("nav-open", open);
        btn.setAttribute("aria-expanded", String(open));
      })
    );
    $$("[data-nav-close]").forEach((el) => el.addEventListener("click", () => body.classList.remove("nav-open")));
    window.addEventListener("resize", () => { if (window.innerWidth > 1024) body.classList.remove("nav-open"); });

    const topbar = $(".topbar");
    if (topbar) {
      const onScroll = () => topbar.classList.toggle("is-scrolled", window.scrollY > 4);
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll();
    }

    // Dropdowns
    $$("[data-dropdown]").forEach((dd) => {
      const trigger = $("[data-dropdown-trigger]", dd);
      if (!trigger) return;
      trigger.addEventListener("click", (e) => {
        e.stopPropagation();
        const open = !dd.classList.contains("is-open");
        $$("[data-dropdown].is-open").forEach((o) => o.classList.remove("is-open"));
        dd.classList.toggle("is-open", open);
        trigger.setAttribute("aria-expanded", String(open));
      });
    });
    document.addEventListener("click", (e) => {
      $$("[data-dropdown].is-open").forEach((dd) => { if (!dd.contains(e.target)) dd.classList.remove("is-open"); });
    });

    // Modals
    document.addEventListener("click", (e) => {
      const opener = e.target.closest("[data-modal-open]");
      if (opener) { e.preventDefault(); openModal(opener.dataset.modalOpen); return; }
      const closer = e.target.closest("[data-modal-close]");
      if (closer) { e.preventDefault(); closeModal(closer.closest(".modal")); return; }
      if (e.target.classList && e.target.classList.contains("modal")) closeModal(e.target);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      const open = $$(".modal.is-open").pop();
      if (open) closeModal(open);
      else {
        document.body.classList.remove("nav-open");
        $$("[data-dropdown].is-open").forEach((o) => o.classList.remove("is-open"));
      }
    });

    // Flash messages rendered by the server
    const flashes = $("#flash-data");
    if (flashes) {
      try { JSON.parse(flashes.textContent).forEach(([type, msg]) => toast(msg, type)); } catch (_) { /* ignore */ }
    }
    try {
      const pending = sessionStorage.getItem("fox:toast");
      if (pending) { sessionStorage.removeItem("fox:toast"); const [type, msg] = JSON.parse(pending); toast(msg, type); }
    } catch (_) { /* storage unavailable */ }
  }

  /* ------------------------------------------------------------ init: forms */
  function initForms() {
    // Loading state + double-submit guard + optional confirmation.
    $$("form").forEach((form) => {
      form.addEventListener("submit", async (e) => {
        if (form.dataset.confirmed === "1") return;
        if (form.dataset.confirm) {
          e.preventDefault();
          if (!form.reportValidity()) return;
          const ok = await confirmDialog({
            title: form.dataset.confirmHeading || "Please confirm",
            message: form.dataset.confirm,
            confirmText: form.dataset.confirmLabel || "Continue",
            tone: form.dataset.confirmTone || "primary",
          });
          if (!ok) return;
          form.dataset.confirmed = "1";
          setLoading(e.submitter || $('[type="submit"]', form), true);
          form.submit();
          return;
        }
        if (form.hasAttribute("data-ajax")) return;
        if (form.dataset.submitting === "1") { e.preventDefault(); return; }
        form.dataset.submitting = "1";
        setLoading(e.submitter || $('[type="submit"]', form), true);
      });
    });
    window.addEventListener("pageshow", () => {
      $$("form[data-submitting]").forEach((f) => { delete f.dataset.submitting; delete f.dataset.confirmed; });
      $$(".btn.is-loading").forEach((b) => setLoading(b, false));
    });

    // Show/hide password
    $$(".password-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const input = btn.parentElement.querySelector("input");
        const show = input.type === "password";
        input.type = show ? "text" : "password";
        btn.innerHTML = `<i class="fas ${show ? "fa-eye-slash" : "fa-eye"}"></i>`;
        btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
      });
    });

    // Password strength meter
    $$("[data-strength-for]").forEach((meter) => {
      const input = document.getElementById(meter.dataset.strengthFor);
      if (!input) return;
      const hint = meter.nextElementSibling;
      input.addEventListener("input", () => {
        const v = input.value;
        let score = 0;
        if (v.length >= 8) score++;
        if (v.length >= 12) score++;
        if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
        if (/\d/.test(v) && /[^A-Za-z0-9]/.test(v)) score++;
        if (!v) score = 0;
        else if (v.length < 8) score = 1;
        meter.dataset.score = String(score);
        if (hint) hint.textContent = !v ? "Use at least 8 characters." : ["Too short", "Weak", "Fair", "Good", "Strong"][score];
      });
    });

    // Matching confirm password
    $$("[data-match]").forEach((input) => {
      const other = document.getElementById(input.dataset.match);
      const check = () => input.setCustomValidity(input.value && input.value !== other.value ? "Passwords do not match." : "");
      input.addEventListener("input", check);
      other.addEventListener("input", check);
    });

    // Character counters
    $$("[data-counter]").forEach((field) => {
      const out = document.getElementById(field.dataset.counter);
      const max = parseInt(field.getAttribute("maxlength"), 10);
      const update = () => { out.textContent = `${field.value.length}${max ? ` / ${max}` : ""}`; };
      field.addEventListener("input", update);
      update();
    });

    // File dropzones
    $$(".dropzone").forEach((zone) => {
      const input = $("input[type=file]", zone);
      const title = $(".dropzone-title", zone);
      const meta = $(".dropzone-meta", zone);
      const clear = $(".dropzone-clear", zone);
      const preview = zone.dataset.preview ? document.getElementById(zone.dataset.preview) : null;
      const defaults = { title: title.textContent, meta: meta.textContent };
      const maxBytes = (parseFloat(zone.dataset.maxMb) || 10) * 1024 * 1024;
      const allowed = (input.getAttribute("accept") || "").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);

      const reset = () => {
        input.value = "";
        zone.classList.remove("has-file");
        title.textContent = defaults.title;
        meta.textContent = defaults.meta;
        if (clear) clear.hidden = true;
        if (preview) { preview.hidden = true; preview.removeAttribute("src"); }
        zone.dispatchEvent(new CustomEvent("dropzone:change", { bubbles: true }));
      };
      const accepts = (file) => {
        if (!allowed.length) return true;
        const ext = "." + file.name.split(".").pop().toLowerCase();
        return allowed.some((a) => a === ext || (a.endsWith("/*") && file.type.startsWith(a.slice(0, -1))) || a === file.type);
      };
      input.addEventListener("change", () => {
        const file = input.files[0];
        if (!file) return reset();
        if (!accepts(file)) { toast(`${file.name} is not an accepted file type.`, "danger"); return reset(); }
        if (file.size > maxBytes) { toast(`${file.name} is larger than ${zone.dataset.maxMb || 10} MB.`, "danger"); return reset(); }
        zone.classList.add("has-file");
        title.textContent = file.name;
        meta.textContent = `${formatBytes(file.size)} · ready to upload`;
        if (clear) clear.hidden = false;
        if (preview && file.type.startsWith("image/")) {
          preview.src = URL.createObjectURL(file);
          preview.hidden = false;
        }
        zone.dispatchEvent(new CustomEvent("dropzone:change", { bubbles: true }));
      });
      ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, () => zone.classList.add("is-drag")));
      ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, () => zone.classList.remove("is-drag")));
      if (clear) clear.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); reset(); });
    });
  }

  /* ------------------------------------------------------------ init: tables */
  function cellValue(row, index) {
    const cell = row.cells[index];
    if (!cell) return "";
    const raw = cell.dataset.value !== undefined ? cell.dataset.value : cell.textContent.trim();
    return raw;
  }
  function initTables() {
    $$("table[data-sortable]").forEach((table) => {
      const headers = $$("th[data-sort]", table);
      headers.forEach((th) => {
        th.tabIndex = 0;
        const sort = () => {
          const index = Array.from(th.parentElement.children).indexOf(th);
          const asc = th.getAttribute("aria-sort") !== "ascending";
          headers.forEach((h) => h.removeAttribute("aria-sort"));
          th.setAttribute("aria-sort", asc ? "ascending" : "descending");
          const numeric = th.dataset.sort === "number";
          const tbody = table.tBodies[0];
          const rows = $$("tr[data-row]", tbody);
          rows.sort((a, b) => {
            let x = cellValue(a, index), y = cellValue(b, index);
            if (numeric) { x = parseFloat(x); y = parseFloat(y); x = isNaN(x) ? Infinity : x; y = isNaN(y) ? Infinity : y; }
            else { x = x.toLowerCase(); y = y.toLowerCase(); }
            return (x > y ? 1 : x < y ? -1 : 0) * (asc ? 1 : -1);
          });
          rows.forEach((r) => tbody.appendChild(r));
        };
        th.addEventListener("click", sort);
        th.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); } });
      });
    });

    // Client-side filters: controls with data-filter="<key>" inside [data-filters="<tableId>"]
    $$("[data-filters]").forEach((bar) => {
      const target = document.getElementById(bar.dataset.filters);
      if (!target) return;
      const controls = $$("[data-filter]", bar);
      const counter = $(`[data-result-count="${bar.dataset.filters}"]`);
      const empty = $(`[data-filter-empty="${bar.dataset.filters}"]`);
      const apply = () => {
        let shown = 0;
        const items = $$("[data-row]", target);
        items.forEach((row) => {
          const visible = controls.every((c) => {
            const v = c.value.trim().toLowerCase();
            if (!v || v === "all") return true;
            const key = c.dataset.filter;
            if (key === "q") return (row.dataset.search || row.textContent).toLowerCase().includes(v);
            return (row.dataset[key] || "").toLowerCase() === v;
          });
          row.hidden = !visible;
          if (visible) shown++;
        });
        if (counter) counter.textContent = `${shown} of ${items.length} shown`;
        if (empty) empty.hidden = shown !== 0 || items.length === 0;
      };
      controls.forEach((c) => c.addEventListener(c.tagName === "INPUT" ? "input" : "change", apply));
      const reset = $("[data-filter-reset]", bar);
      if (reset) reset.addEventListener("click", (e) => { e.preventDefault(); controls.forEach((c) => { c.value = c.tagName === "SELECT" ? (c.querySelector('option[value="all"]') ? "all" : "") : ""; }); apply(); });
      apply();
    });
  }

  /* ------------------------------------------------------------ reveal on scroll */
  function initReveal() {
    const items = $$(".reveal");
    if (!items.length) return;
    if (!("IntersectionObserver" in window)) return;
    document.documentElement.classList.add("js-reveal");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("is-visible"); io.unobserve(en.target); } });
    }, { threshold: 0.12 });
    items.forEach((i) => io.observe(i));
  }

  /* ------------------------------------------------------------ live updates */
  let socket = null;
  function getSocket() {
    if (socket || typeof window.io !== "function") return socket;
    socket = window.io({ transports: ["websocket", "polling"] });
    return socket;
  }
  function initLive() {
    const role = document.body.dataset.role;
    if (role !== "student" && role !== "admin") return;
    const s = getSocket();
    if (!s) return;
    const onChatPage = !!document.querySelector("[data-chat]");
    if (role === "student") {
      s.on("notification", (data) => {
        bumpBadge("notifBadge");
        toast(data.message.split("\n")[0], "info", 6000);
      });
      s.on("receive_message", (m) => {
        if (!onChatPage && m.sender_role === "admin") { bumpBadge("chatBadge"); toast("New message from SBO support.", "info"); }
      });
    } else {
      s.on("receive_message", (m) => {
        if (!onChatPage && m.sender_role === "student") { bumpBadge("chatBadge"); toast(`New message from ${m.sender_name || "a student"}.`, "info"); }
      });
    }
  }

  window.Fox = { $, $$, toast, api, openModal, closeModal, confirm: confirmDialog, toastAfterReload, setLoading, escapeHtml, formatBytes, setBadge, bumpBadge, socket: getSocket };

  document.addEventListener("DOMContentLoaded", () => {
    initShell();
    initForms();
    initTables();
    initReveal();
    initLive();
  });
})();
