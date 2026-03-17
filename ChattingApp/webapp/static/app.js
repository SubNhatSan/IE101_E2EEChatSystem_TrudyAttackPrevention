// ===== API Helpers =====
const api = {
  post: async (path, body) => {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return res.json();
  },
  get: async (path) => {
    const res = await fetch(path);
    return res.json();
  },
};

// ===== Storage (localStorage) =====
const storage = {
  getSession: () => {
    const session = localStorage.getItem("chatSession");
    return session ? JSON.parse(session) : null;
  },
  setSession: (session) => {
    localStorage.setItem("chatSession", JSON.stringify(session));
  },
  clearSession: () => {
    localStorage.removeItem("chatSession");
  },
};

// ===== Variables =====
let socket;
let currentUser = null;
let currentFriends = [];
let currentGroups = [];
let currentChat = { type: "group", to: "all", label: "Phòng chung" };
let pendingMessages = {}; // clientId -> dom element
let allMessages = {}; // conversation_id -> [messages]

// ===== DOM Elements =====
const elements = {
  // Auth
  inputUsername: document.getElementById("inputUsername"),
  inputPassword: document.getElementById("inputPassword"),
  btnLogin: document.getElementById("btnLogin"),
  btnRegister: document.getElementById("btnRegister"),
  authMessage: document.getElementById("authMessage"),
  authSection: document.getElementById("authSection"),

  // User Info
  userInfo: document.getElementById("userInfo"),
  usernameLabel: document.getElementById("usernameLabel"),
  btnLogout: document.getElementById("btnLogout"),

  // Chat Main
  chatMainSection: document.getElementById("chatMainSection"),

  // Sidebar
  searchChat: document.getElementById("searchChat"),
  chatListFriends: document.getElementById("chatListFriends"),
  chatListGroups: document.getElementById("chatListGroups"),
  btnToggleManage: document.getElementById("btnToggleManage"),
  managePanel: document.getElementById("managePanel"),

  // Manage Panel
  searchUser: document.getElementById("searchUser"),
  searchResults: document.getElementById("searchResults"),
  requestSection: document.getElementById("requestsSection"),
  requestsBadge: document.getElementById("requestsBadge"),
  friendRequests: document.getElementById("friendRequests"),
  groupName: document.getElementById("groupName"),
  memberCheckboxes: document.getElementById("memberCheckboxes"),
  btnCreateGroup: document.getElementById("btnCreateGroup"),
  groupMessage: document.getElementById("groupMessage"),

  // Chat Area
  currentChatName: document.getElementById("currentChatName"),
  messages: document.getElementById("messages"),
  messageInput: document.getElementById("messageInput"),
  btnSend: document.getElementById("btnSend"),
  sendStatus: document.getElementById("sendStatus"),

  // Other
  notificationArea: document.getElementById("notificationArea"),
};

// ===== Helper Functions =====
function setStatus(text) {
  elements.sendStatus.textContent = text;
}

function showAuthMessage(text, isError = true) {
  elements.authMessage.textContent = text;
  elements.authMessage.style.color = isError ? "#b91c1c" : "#0b6e4f";
}

function playSound(type) {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    if (type === "accept") {
      oscillator.frequency.value = 600;
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.2);
    } else if (type === "decline") {
      oscillator.frequency.value = 400;
      gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.15);
    } else { // friend_request
      oscillator.frequency.value = 800;
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.1);
      
      const osc2 = audioContext.createOscillator();
      const gain2 = audioContext.createGain();
      osc2.connect(gain2);
      gain2.connect(audioContext.destination);
      osc2.frequency.value = 1000;
      gain2.gain.setValueAtTime(0.3, audioContext.currentTime + 0.12);
      gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.22);
      osc2.start(audioContext.currentTime + 0.12);
      osc2.stop(audioContext.currentTime + 0.22);
    }
  } catch (e) {
    console.log("Audio not available:", e);
  }
}

// ===== Message Display =====
function clearMessages() {
  elements.messages.innerHTML = "";
}

function addMessageToDom({ from, text, type, groupName, self, clientId }) {
  const row = document.createElement("div");
  row.className = "message-row" + (self ? " sent" : "");

  const meta = document.createElement("div");
  meta.className = "meta";
  if (type === "group") {
    meta.textContent = self ? "Bạn (Phòng chung)" : `${from} (Phòng chung)`;
  } else if (type === "private") {
    meta.textContent = self ? `Bạn → ${currentChat.label}` : `${from} → Bạn`;
  } else if (type === "groupchat") {
    meta.textContent = self ? `Bạn (${groupName})` : `${from} (${groupName})`;
  }
  row.appendChild(meta);

  const textEl = document.createElement("div");
  textEl.className = "text";
  textEl.textContent = text;
  row.appendChild(textEl);

  // Add delete button for private conversations (only show once)
  if (type === "private" && self && !document.querySelector(".btn-clear-chat")) {
    const btnDelete = document.createElement("button");
    btnDelete.className = "btn-clear-chat";
    btnDelete.textContent = "🗑";
    btnDelete.title = "Xoá toàn bộ đoạn chat";
    btnDelete.addEventListener("click", async () => {
      if (confirm(`Bạn có chắc chắn muốn xoá toàn bộ đoạn chat với ${currentChat.label}? Hành động này không thể hoàn tác.`)) {
        const res = await api.post("/api/messages/delete", {
          me: currentUser,
          to: currentChat.to,
        });
        if (res.success) {
          clearMessages();
          showAuthMessage("Đã xoá toàn bộ đoạn chat.", false);
          
          // Notify the other user in real-time
          if (socket) {
            socket.emit("delete_conversation", {
              user: currentUser,
              other_user: currentChat.to,
            });
          }
        } else {
          alert(res.message || "Không thể xoá đoạn chat.");
        }
      }
    });
    row.appendChild(btnDelete);
  }

  if (self && clientId) {
    const pending = document.createElement("div");
    pending.className = "pending";
    pending.textContent = "Đang gửi...";
    row.appendChild(pending);
    pendingMessages[clientId] = pending;
  }

  elements.messages.appendChild(row);
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

async function loadMessageHistory() {
  if (!currentUser) return;

  const params = new URLSearchParams({
    me: currentUser,
    type: currentChat.type,
  });

  if (currentChat.type === "private") {
    params.append("to", currentChat.to);
  } else if (currentChat.type === "groupchat") {
    params.append("groupId", currentChat.to);
  }

  const res = await api.get(`/api/messages/history?${params}`);
  if (!res.success) {
    console.error("Failed to load message history:", res.message);
    return;
  }

  clearMessages();
  const messages = res.messages || [];
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    addMessageToDom({
      from: msg.from,
      text: msg.text,
      type: msg.type,
      groupName: msg.groupName,
      self: msg.from === currentUser,
    });
  }
}

// ===== Chat List (Messenger-style) =====
async function renderChatList() {
  if (!currentUser) return;

  // Render friends
  elements.chatListFriends.innerHTML = "";
  for (const friend of currentFriends) {
    const item = document.createElement("div");
    item.className = "chat-list-item";
    if (currentChat.type === "private" && currentChat.to === friend) {
      item.classList.add("active");
    }

    const chatArea = document.createElement("div");
    chatArea.style.flex = "1";
    chatArea.style.cursor = "pointer";
    chatArea.innerHTML = `
      <div class="chat-item-avatar">
        <span class="avatar-text">👤</span>
      </div>
      <div class="chat-item-info">
        <div class="chat-item-name">${friend}</div>
        <div class="chat-item-preview">Tin nhắn riêng</div>
      </div>
    `;

    chatArea.addEventListener("click", async () => {
      setCurrentChat({ type: "private", to: friend, label: friend });
      await loadMessageHistory();
    });

    item.appendChild(chatArea);

    // Add delete friend button
    const btnDeleteFriend = document.createElement("button");
    btnDeleteFriend.className = "btn-icon-small";
    btnDeleteFriend.textContent = "✕";
    btnDeleteFriend.title = "Xoá bạn bè";
    btnDeleteFriend.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (confirm(`Bạn có chắc chắn muốn xoá ${friend} khỏi danh sách bạn bè?`)) {
        const res = await api.post("/api/friends/remove", { me: currentUser, friend });
        if (res.success) {
          await refreshFriends();
        } else {
          alert(res.message || "Không thể xoá bạn bè.");
        }
      }
    });

    item.appendChild(btnDeleteFriend);
    elements.chatListFriends.appendChild(item);
  }

  // Render groups
  elements.chatListGroups.innerHTML = "";
  for (const group of currentGroups) {
    const item = document.createElement("div");
    item.className = "chat-list-item";
    if (currentChat.type === "groupchat" && currentChat.to === group.id) {
      item.classList.add("active");
    }

    const chatArea = document.createElement("div");
    chatArea.style.flex = "1";
    chatArea.style.cursor = "pointer";
    chatArea.innerHTML = `
      <div class="chat-item-avatar">
        <span class="avatar-text">👥</span>
      </div>
      <div class="chat-item-info">
        <div class="chat-item-name">${group.name}</div>
        <div class="chat-item-preview">${group.members.length} thành viên</div>
      </div>
    `;

    chatArea.addEventListener("click", async () => {
      setCurrentChat({
        type: "groupchat",
        to: group.id,
        label: group.name,
        groupName: group.name,
      });
      await loadMessageHistory();
    });

    item.appendChild(chatArea);

    // Add delete group button (only if user is owner)
    if (group.owner === currentUser) {
      const btnDeleteGroup = document.createElement("button");
      btnDeleteGroup.className = "btn-icon-small";
      btnDeleteGroup.textContent = "✕";
      btnDeleteGroup.title = "Xoá nhóm";
      btnDeleteGroup.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (confirm(`Bạn có chắc chắn muốn xoá nhóm "${group.name}"? Hành động này không thể hoàn tác.`)) {
          const res = await api.post("/api/groups/delete", { me: currentUser, groupId: group.id });
          if (res.success) {
            await refreshGroups();
            // If the deleted group was active, switch to main room
            if (currentChat.type === "groupchat" && currentChat.to === group.id) {
              setCurrentChat({ type: "group", to: "all", label: "Phòng chung" });
              await loadMessageHistory();
            }
          } else {
            alert(res.message || "Không thể xoá nhóm.");
          }
        }
      });
      item.appendChild(btnDeleteGroup);
    }

    elements.chatListGroups.appendChild(item);
  }
}

function setCurrentChat({ type, to, label, groupName }) {
  currentChat = { type, to, label, groupName };
  elements.currentChatName.textContent = label;
  renderChatList(); // Update active state
}

// ===== Data Refresh =====
async function refreshFriendRequests() {
  if (!currentUser) return;
  const res = await api.get(`/api/friends/requests?me=${encodeURIComponent(currentUser)}`);
  const requests = res.requests || [];

  if (elements.requestsBadge) {
    elements.requestsBadge.textContent = requests.length;
    elements.requestsBadge.style.display = requests.length > 0 ? "block" : "none";
  }

  elements.friendRequests.innerHTML = "";
  if (requests.length === 0) {
    const emptyMsg = document.createElement("div");
    emptyMsg.className = "no-requests";
    emptyMsg.textContent = "Không có lời mời nào.";
    elements.friendRequests.appendChild(emptyMsg);
    return;
  }

  for (const requester of requests) {
    const item = document.createElement("div");
    item.className = "friend-request-item";

    const nameSpan = document.createElement("span");
    nameSpan.className = "requester-name";
    nameSpan.textContent = requester;
    item.appendChild(nameSpan);

    const btnAccept = document.createElement("button");
    btnAccept.className = "btn small accept-btn";
    btnAccept.textContent = "✓ Chấp nhận";
    btnAccept.addEventListener("click", async () => {
      await api.post("/api/friends/respond", { me: currentUser, from: requester, accept: true });
      playSound("accept");
      refreshFriends();
      refreshFriendRequests();
    });

    const btnDecline = document.createElement("button");
    btnDecline.className = "btn small decline-btn";
    btnDecline.textContent = "✗ Từ chối";
    btnDecline.addEventListener("click", async () => {
      await api.post("/api/friends/respond", { me: currentUser, from: requester, accept: false });
      playSound("decline");
      refreshFriendRequests();
    });

    item.appendChild(btnAccept);
    item.appendChild(btnDecline);
    elements.friendRequests.appendChild(item);
  }
}

async function refreshFriends() {
  if (!currentUser) return;
  const res = await api.get(`/api/friends?me=${encodeURIComponent(currentUser)}`);
  currentFriends = res.friends || [];
  
  elements.memberCheckboxes.innerHTML = "";
  for (const friend of currentFriends) {
    const chk = document.createElement("label");
    chk.className = "item";
    chk.innerHTML = `<input type="checkbox" value="${friend}" /> ${friend}`;
    elements.memberCheckboxes.appendChild(chk);
  }

  await renderChatList();
}

async function refreshGroups() {
  if (!currentUser) return;
  const res = await api.get(`/api/groups?me=${encodeURIComponent(currentUser)}`);
  currentGroups = res.groups || [];
  await renderChatList();
}

async function doSearchUsers() {
  const q = elements.searchUser.value.trim();
  if (!q) {
    elements.searchResults.innerHTML = "";
    return;
  }
  const res = await api.get(`/api/users?q=${encodeURIComponent(q)}&me=${encodeURIComponent(currentUser)}`);
  elements.searchResults.innerHTML = "";
  for (const u of res.users || []) {
    const item = document.createElement("div");
    item.className = "item";
    item.textContent = u;

    const btn = document.createElement("button");
    btn.className = "btn small";

    if (currentFriends.includes(u)) {
      btn.textContent = "Chat";
      btn.addEventListener("click", async () => {
        setCurrentChat({ type: "private", to: u, label: u });
        await loadMessageHistory();
      });
    } else {
      btn.textContent = "Gửi yêu cầu";
      btn.addEventListener("click", async () => {
        const res = await api.post("/api/friends/request", { me: currentUser, to: u });
        showAuthMessage(res.message || "Đã gửi yêu cầu.", res.success === false);
        refreshFriendRequests();
      });
    }

    item.appendChild(btn);
    elements.searchResults.appendChild(item);
  }
}

// ===== Socket Communication =====
function connectSocket() {
  if (!currentUser) return;

  const url = `${window.location.protocol}//${window.location.host}`;
  socket = io(url, { query: { username: currentUser } });

  socket.on("connect", () => {
    setStatus("Đã kết nối tới server.");
    socket.emit("authenticate", { username: currentUser });
    console.log(`[Client] Connected and authenticated as ${currentUser}`);
  });

  socket.on("auth_success", (data) => {
    console.log(`[Client] Auth success: ${data.message}`);
  });

  socket.on("disconnect", () => {
    setStatus("Mất kết nối với server.");
  });

  socket.on("message", (payload) => {
    const { from, type, text, groupName, to, groupId } = payload;
    
    // Check if the message is for the current chat
    let shouldDisplay = false;
    if (type === "private") {
      shouldDisplay = (currentChat.type === "private" && currentChat.to === from);
    } else if (type === "group") {
      shouldDisplay = currentChat.type === "group";
    } else if (type === "groupchat") {
      shouldDisplay = currentChat.type === "groupchat" && currentChat.to === groupId;
    }

    if (shouldDisplay) {
      addMessageToDom({ 
        from, 
        text, 
        type, 
        groupName, 
        self: false
      });
    }
  });

  socket.on("message_ack", (payload) => {
    const { clientId } = payload;
    const pending = pendingMessages[clientId];
    if (pending) {
      pending.remove();
      delete pendingMessages[clientId];
    }
  });

  socket.on("friend_request", (payload) => {
    const from = payload?.from;
    if (from) {
      playSound("friend_request");
      showAuthMessage(`📥 Yêu cầu kết bạn từ ${from}`, false);
      
      if (elements.notificationArea) {
        const notification = document.createElement("div");
        notification.className = "notification friend-request-notification";
        notification.innerHTML = `<strong>Lời mời kết bạn mới</strong><br><em>${from}</em>`;
        elements.notificationArea.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
      }
      
      refreshFriendRequests();
    }
  });

  socket.on("friend_accepted", (payload) => {
    const from = payload?.from;
    if (from) {
      playSound("accept");
      showAuthMessage(`✓ ${from} đã chấp nhận lời mời kết bạn`, false);
      
      if (elements.notificationArea) {
        const notification = document.createElement("div");
        notification.className = "notification";
        notification.innerHTML = `<strong>Bạn bè mới!</strong><br><em>${from}</em>`;
        elements.notificationArea.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
      }
      
      refreshFriends();
    }
  });

  socket.on("conversation_deleted", (payload) => {
    const { user, other_user } = payload;
    // Check if the deleted conversation is the current one
    if (currentChat.type === "private" && currentChat.to === user) {
      clearMessages();
      showAuthMessage(`${user} đã xoá toàn bộ đoạn chat.`, false);
    }
  });
}

function sendChatMessage() {
  if (!currentUser || !socket) {
    setStatus("Vui lòng đăng nhập.");
    return;
  }

  const text = elements.messageInput.value.trim();
  if (!text) return;

  const clientId = `cid_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  const payload = {
    from: currentUser,
    clientId,
    text,
    type: currentChat.type,
  };

  if (currentChat.type === "private") {
    payload.to = currentChat.to;
  } else if (currentChat.type === "groupchat") {
    payload.groupId = currentChat.to;
  }

  addMessageToDom({
    from: currentUser,
    text,
    type: currentChat.type,
    groupName: currentChat.groupName,
    self: true,
    clientId,
  });

  socket.emit("send_message", payload);
  elements.messageInput.value = "";
}

// ===== Auth =====
async function login() {
  const username = elements.inputUsername.value.trim();
  const password = elements.inputPassword.value.trim();

  if (!username || !password) {
    showAuthMessage("Nhập đầy đủ username và password.");
    return;
  }

  const res = await api.post("/api/login", { username, password });
  if (!res.success) {
    showAuthMessage(res.message || "Đăng nhập thất bại.");
    return;
  }

  currentUser = username;
  showAuthMessage("Đăng nhập thành công.", false);
  storage.setSession({ username });
  showChatUI();
}

async function registerUser() {
  const username = elements.inputUsername.value.trim();
  const password = elements.inputPassword.value.trim();

  if (!username || !password) {
    showAuthMessage("Nhập đầy đủ username và password.");
    return;
  }

  const res = await api.post("/api/register", { username, password });
  if (!res.success) {
    showAuthMessage(res.message || "Đăng ký thất bại.");
    return;
  }

  showAuthMessage("Đăng ký thành công. Bạn có thể đăng nhập.", false);
}

async function logout() {
  currentUser = null;
  if (socket) {
    socket.disconnect();
    socket = null;
  }
  storage.clearSession();
  showAuthUI();
}

// ===== UI Display =====
async function showChatUI() {
  elements.authSection.style.display = "none";
  elements.chatMainSection.style.display = "flex";
  elements.userInfo.style.display = "flex";
  elements.usernameLabel.textContent = currentUser;

  await refreshFriendRequests();
  await refreshFriends();
  await refreshGroups();
  await loadMessageHistory();
  
  connectSocket();
}

function showAuthUI() {
  elements.authSection.style.display = "flex";
  elements.chatMainSection.style.display = "none";
  elements.userInfo.style.display = "none";
  elements.authMessage.textContent = "";
  clearMessages();
}

// ===== Initialize =====
async function init() {
  // Check session
  const session = storage.getSession();
  if (session && session.username) {
    currentUser = session.username;
    await showChatUI();
  } else {
    showAuthUI();
  }

  // Event listeners
  elements.btnLogin.addEventListener("click", login);
  elements.btnRegister.addEventListener("click", registerUser);
  elements.btnLogout.addEventListener("click", logout);
  elements.btnSend.addEventListener("click", sendChatMessage);
  elements.messageInput.addEventListener("keydown", (evt) => {
    if (evt.key === "Enter") {
      sendChatMessage();
    }
  });
  
  elements.searchUser.addEventListener("input", doSearchUsers);

  elements.btnToggleManage.addEventListener("click", () => {
    const isHidden = elements.managePanel.style.display === "none";
    elements.managePanel.style.display = isHidden ? "block" : "none";
  });

  elements.btnCreateGroup.addEventListener("click", async () => {
    const name = elements.groupName.value.trim();
    const checkboxes = Array.from(
      elements.memberCheckboxes.querySelectorAll("input[type=checkbox]:checked")
    ).map((c) => c.value);

    if (!name || checkboxes.length === 0) {
      elements.groupMessage.textContent = "Nhập tên nhóm và chọn ít nhất một bạn.";
      return;
    }

    const res = await api.post("/api/groups/create", {
      me: currentUser,
      name,
      members: checkboxes,
    });

    if (res.success) {
      elements.groupMessage.textContent = "Đã tạo nhóm.";
      elements.groupName.value = "";
      await refreshGroups();
    } else {
      elements.groupMessage.textContent = res.message || "Không thể tạo nhóm.";
    }
  });
}

// Start app
init();

