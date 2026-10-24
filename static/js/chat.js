/* Live chat between students and SBO support (Socket.IO with HTTP fallback). */
(function () {
  "use strict";
  const root = document.querySelector("[data-chat]");
  if (!root) return;

  const mode = root.dataset.chat; // "student" | "admin"
  const messagesEl = root.querySelector("[data-messages]");
  const form = root.querySelector("[data-compose]");
  const input = form.querySelector("textarea");
  const sendBtn = form.querySelector("button[type=submit]");
  const liveDot = root.querySelector("[data-live-dot]");
  const liveText = root.querySelector("[data-live-text]");
  const typingEl = root.querySelector("[data-typing]");
  const socket = Fox.socket();

  let activeStudent = mode === "student" ? Number(root.dataset.me) : null;
  let rendered = new Set();
  let lastDay = null;
  let typingTimer = null;
  let lastTypingSent = 0;

  const isMine = (m) => (mode === "student" ? m.sender_role === "student" : m.sender_role === "admin");
  const studentOf = (m) => (m.sender_role === "student" ? Number(m.sender_id) : Number(m.receiver_id));
  const dayLabel = (d) => {
    const today = new Date();
    const y = new Date(); y.setDate(today.getDate() - 1);
    if (d.toDateString() === today.toDateString()) return "Today";
    if (d.toDateString() === y.toDateString()) return "Yesterday";
    return d.toLocaleDateString([], { month: "short", day: "numeric", year: d.getFullYear() === today.getFullYear() ? undefined : "numeric" });
  };
  const parseTime = (t) => (t ? new Date(t) : new Date());

  function scrollToEnd() { messagesEl.scrollTop = messagesEl.scrollHeight; }

  function append(m, { scroll = true } = {}) {
    if (m.id && rendered.has(m.id)) return;
    if (m.id) rendered.add(m.id);
    const when = parseTime(m.timestamp);
    const day = when.toDateString();
    if (day !== lastDay) {
      const sep = document.createElement("div");
      sep.className = "msg-day";
      sep.textContent = dayLabel(when);
      messagesEl.appendChild(sep);
      lastDay = day;
    }
    const el = document.createElement("div");
    el.className = `msg ${isMine(m) ? "mine" : "theirs"}`;
    const text = document.createElement("div");
    text.textContent = m.message; // never innerHTML: messages are user content
    const time = document.createElement("time");
    time.dateTime = when.toISOString();
    time.textContent = when.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    el.append(text, time);
    messagesEl.appendChild(el);
    if (scroll) scrollToEnd();
  }

  function showEmpty(title, text) {
    messagesEl.innerHTML = `<div class="empty" style="margin:auto"><div class="list-icon" style="width:56px;height:56px;border-radius:16px;font-size:1.3rem"><i class="fas fa-comments"></i></div><h3>${Fox.escapeHtml(title)}</h3><p>${Fox.escapeHtml(text)}</p></div>`;
  }

  async function load(studentId) {
    rendered = new Set();
    lastDay = null;
    messagesEl.innerHTML = '<div class="skeleton" style="height:44px;width:55%"></div><div class="skeleton" style="height:44px;width:40%;align-self:flex-end"></div><div class="skeleton" style="height:44px;width:48%"></div>';
    try {
      const data = await Fox.api(`/chat/messages/${studentId}`);
      messagesEl.innerHTML = "";
      if (!data.length) {
        showEmpty(mode === "student" ? "Start a conversation" : "No messages yet",
          mode === "student" ? "Ask the SBO about requirements, deadlines or your application." : "Send the first message to this student.");
      }
      data.forEach((m) => append(m, { scroll: false }));
      scrollToEnd();
      Fox.setBadge("chatBadge", 0);
    } catch (err) {
      showEmpty("Couldn't load messages", err.message);
    }
  }

  function setLive(on) {
    if (liveDot) liveDot.classList.toggle("on", on);
    if (liveText) liveText.textContent = on ? "Connected · replies arrive instantly" : "Reconnecting…";
  }

  async function send() {
    const text = input.value.trim();
    if (!text || !activeStudent) return;
    if (text.length > 2000) { Fox.toast("Messages are limited to 2,000 characters.", "warning"); return; }
    sendBtn.disabled = true;
    const payload = { message: text, receiver_id: mode === "admin" ? activeStudent : 0 };
    const done = (ok) => {
      sendBtn.disabled = false;
      if (ok) { input.value = ""; autosize(); }
      input.focus();
    };
    if (messagesEl.querySelector(".empty")) messagesEl.innerHTML = "";
    if (socket && socket.connected) {
      socket.timeout(8000).emit("send_message", payload, (err, ack) => {
        if (err || !ack || ack.error) { Fox.toast((ack && ack.error) || "Message not sent — please try again.", "danger"); done(false); }
        else done(true);
      });
    } else {
      try {
        const m = await Fox.api("/chat/send", { method: "POST", json: payload });
        append(m);
        done(true);
      } catch (err) {
        Fox.toast(err.message, "danger");
        done(false);
      }
    }
  }

  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); send(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  input.addEventListener("input", () => {
    autosize();
    const now = Date.now();
    if (socket && socket.connected && activeStudent && now - lastTypingSent > 2500) {
      lastTypingSent = now;
      socket.emit("typing", { receiver_id: activeStudent });
    }
  });

  /* ------------------------------------------------------------ admin contact list */
  const listEl = root.querySelector("[data-contacts]");
  const searchEl = root.querySelector("[data-contact-search]");
  const headName = root.querySelector("[data-active-name]");
  const headAvatar = root.querySelector("[data-active-avatar]");
  let contacts = [];

  const initials = (name) => (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
  const shortTime = (t) => {
    if (!t) return "";
    const d = new Date(t);
    return d.toDateString() === new Date().toDateString()
      ? d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
      : d.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  function renderContacts() {
    if (!listEl) return;
    const q = (searchEl ? searchEl.value : "").trim().toLowerCase();
    const items = contacts.filter((c) => !q || `${c.name} ${c.email}`.toLowerCase().includes(q));
    listEl.innerHTML = "";
    if (!items.length) {
      listEl.innerHTML = `<div class="empty"><p>${q ? "No students match your search." : "No students yet."}</p></div>`;
      return;
    }
    let section = null;
    items.forEach((c) => {
      const group = c.last_message_time ? "Conversations" : "Start a new chat";
      if (group !== section) {
        section = group;
        const h = document.createElement("div");
        h.className = "sidebar-section";
        h.style.cssText = "color:var(--text-subtle);padding:12px 10px 6px";
        h.textContent = group;
        listEl.appendChild(h);
      }
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `chat-contact${c.id === activeStudent ? " is-active" : ""}`;
      btn.dataset.id = c.id;
      btn.innerHTML = `<span class="avatar">${Fox.escapeHtml(initials(c.name))}</span>
        <span class="info"><strong class="truncate"></strong><small></small></span>
        <span class="side"><time>${Fox.escapeHtml(shortTime(c.last_message_time))}</time>${c.unread_count ? `<span class="count-pill">${c.unread_count}</span>` : ""}</span>`;
      btn.querySelector("strong").textContent = c.name || "Unknown student";
      btn.querySelector("small").textContent = c.last_message || c.email || "";
      btn.addEventListener("click", () => openConversation(c.id));
      listEl.appendChild(btn);
    });
  }

  async function loadContacts() {
    try {
      contacts = await Fox.api("/chat/students?all=1");
      renderContacts();
      Fox.setBadge("chatBadge", contacts.reduce((n, c) => n + (c.unread_count || 0), 0));
    } catch (err) {
      if (listEl) listEl.innerHTML = `<div class="empty"><p>${Fox.escapeHtml(err.message)}</p></div>`;
    }
  }

  function openConversation(id) {
    const c = contacts.find((x) => x.id === Number(id));
    activeStudent = Number(id);
    if (c) {
      c.unread_count = 0;
      headName.textContent = c.name || "Unknown student";
      headAvatar.textContent = initials(c.name);
    }
    root.classList.add("show-pane");
    form.hidden = false;
    renderContacts();
    load(activeStudent);
    const url = new URL(window.location);
    url.searchParams.set("student", activeStudent);
    history.replaceState(null, "", url);
    Fox.setBadge("chatBadge", contacts.reduce((n, x) => n + (x.unread_count || 0), 0));
    input.focus();
  }

  const backBtn = root.querySelector("[data-chat-back]");
  if (backBtn) backBtn.addEventListener("click", () => root.classList.remove("show-pane"));
  if (searchEl) searchEl.addEventListener("input", renderContacts);

  /* ------------------------------------------------------------ socket events */
  if (socket) {
    let wasConnected = false;
    socket.on("connect", () => {
      setLive(true);
      if (wasConnected && activeStudent) load(activeStudent); // catch up on anything missed
      wasConnected = true;
    });
    socket.on("disconnect", () => setLive(false));
    socket.on("connect_error", () => setLive(false));
    if (socket.connected) { setLive(true); wasConnected = true; }

    socket.on("receive_message", (m) => {
      const sid = studentOf(m);
      if (sid === activeStudent) {
        if (messagesEl.querySelector(".empty")) messagesEl.innerHTML = "";
        append(m);
        if (typingEl) typingEl.hidden = true;
        if (mode === "admin" && m.sender_role === "student") {
          Fox.api(`/chat/mark_read/${sid}`, { method: "POST" }).catch(() => {});
        }
      }
      if (mode === "admin") {
        const c = contacts.find((x) => x.id === sid);
        if (c) {
          c.last_message = m.message;
          c.last_message_time = m.timestamp;
          if (m.sender_role === "student" && sid !== activeStudent) c.unread_count = (c.unread_count || 0) + 1;
          contacts.sort((a, b) => (b.last_message_time ? new Date(b.last_message_time) : 0) - (a.last_message_time ? new Date(a.last_message_time) : 0));
          renderContacts();
          Fox.setBadge("chatBadge", contacts.reduce((n, x) => n + (x.unread_count || 0), 0));
        } else {
          loadContacts();
        }
      }
    });

    socket.on("typing", (data) => {
      if (!typingEl) return;
      const relevant = mode === "admin" ? data.from === "student" && Number(data.student_id) === activeStudent : data.from === "admin";
      if (!relevant) return;
      typingEl.hidden = false;
      clearTimeout(typingTimer);
      typingTimer = setTimeout(() => (typingEl.hidden = true), 3000);
    });
  } else {
    setLive(false);
    if (liveText) liveText.textContent = "Live updates unavailable · messages still send";
  }

  /* ------------------------------------------------------------ boot */
  if (mode === "student") {
    load(activeStudent);
  } else {
    form.hidden = true;
    loadContacts().then(() => {
      const initial = Number(root.dataset.open || new URL(window.location).searchParams.get("student"));
      if (initial) openConversation(initial);
    });
  }
})();
