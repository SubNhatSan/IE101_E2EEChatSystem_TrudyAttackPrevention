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

let socket;
let currentUser = null;
let currentFriends = [];
let currentChat = { type: "group", to: "all", label: "Phòng chung" };
let pendingMessages = {}; // clientId -> dom element
let friendRequestCount = 0; // Track number of pending requests

const elements = {
  inputUsername: document.getElementById("inputUsername"),
  inputPassword: document.getElementById("inputPassword"),
  btnLogin: document.getElementById("btnLogin"),
  btnRegister: document.getElementById("btnRegister"),
  authMessage: document.getElementById("authMessage"),
  authSection: document.getElementById("auth"),
  chatControls: document.getElementById("chatControls"),
  usernameLabel: document.getElementById("usernameLabel"),
  btnLogout: document.getElementById("btnLogout"),
  userInfo: document.getElementById("userInfo"),
  searchUser: document.getElementById("searchUser"),
  searchResults: document.getElementById("searchResults"),
  friendRequests: document.getElementById("friendRequests"),
  friendList: document.getElementById("friendList"),
  groupList: document.getElementById("groupList"),
  groupName: document.getElementById("groupName"),
  memberCheckboxes: document.getElementById("memberCheckboxes"),
  btnCreateGroup: document.getElementById("btnCreateGroup"),
  groupMessage: document.getElementById("groupMessage"),
  conversationSelect: document.getElementById("conversationSelect"),
  messages: document.getElementById("messages"),
  messageInput: document.getElementById("messageInput"),
  btnSend: document.getElementById("btnSend"),
  sendStatus: document.getElementById("sendStatus"),
  chatSection: document.getElementById("chatSection"),
  requestsSection: document.getElementById("requestsSection"),
  requestsBadge: document.getElementById("requestsBadge"),
  notificationArea: document.getElementById("notificationArea"),
};

function setStatus(text) {
  elements.sendStatus.textContent = text;
}

function playSound(type) {
  // Create a simple beep sound using Web Audio API
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    if (type === "accept") {
      oscillator.frequency.value = 600; // Higher frequency for accept
      oscillator.type = "sine";
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.2);
    } else if (type === "decline") {
      oscillator.frequency.value = 400; // Lower frequency for decline
      oscillator.type = "sine";
      gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.15);
    } else { // friend_request
      // Two-tone beep for new friend request
      oscillator.frequency.value = 800;
      oscillator.type = "sine";
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.1);
      
      const osc2 = audioContext.createOscillator();
      const gain2 = audioContext.createGain();
      osc2.connect(gain2);
      gain2.connect(audioContext.destination);
      osc2.frequency.value = 1000;
      osc2.type = "sine";
      gain2.gain.setValueAtTime(0.3, audioContext.currentTime + 0.12);
      gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.22);
      osc2.start(audioContext.currentTime + 0.12);
      osc2.stop(audioContext.currentTime + 0.22);
    }
  } catch (e) {
    console.log("Audio notification not available:", e);
  }
}

function showAuthMessage(text, isError = true) {
  elements.authMessage.textContent = text;
  elements.authMessage.style.color = isError ? "#b91c1c" : "#0b6e4f";
}

function makeOption(value, label) {
  const opt = document.createElement("option");
  opt.value = value;
  opt.textContent = label;
  return opt;
}

function addMessage({ from, text, type, groupName, self, clientId }) {
  const row = document.createElement("div");
  row.className = "message-row" + (self ? " sent" : "");

  const meta = document.createElement("div");
  meta.className = "meta";
  if (type === "group") {
    meta.textContent = self ? "Bạn (Nhóm chung)" : `${from} (Nhóm chung)`;
  } else if (type === "private") {
    meta.textContent = self
      ? `Bạn → ${currentChat.label}`
      : `${from} → Bạn`;
  } else if (type === "groupchat") {
    meta.textContent = self
      ? `Bạn (Nhóm: ${groupName})`
      : `${from} (Nhóm: ${groupName})`;
  }
  row.appendChild(meta);

  const textEl = document.createElement("div");
  textEl.className = "text";
  textEl.textContent = text;
  row.appendChild(textEl);

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

function clearMessages() {
  elements.messages.innerHTML = "";
}

async function refreshFriendRequests() {
  if (!currentUser) return;
  const res = await api.get(`/api/friends/requests?me=${encodeURIComponent(currentUser)}`);
  const requests = res.requests || [];
  friendRequestCount = requests.length;
  
  // Update badge display
  if (elements.requestsBadge) {
    elements.requestsBadge.textContent = friendRequestCount;
    elements.requestsBadge.style.display = friendRequestCount > 0 ? "block" : "none";
  }
  
  elements.friendRequests.innerHTML = "";
  
  if (requests.length === 0) {
    const emptyMsg = document.createElement("div");
    emptyMsg.className = "no-requests";
    emptyMsg.textContent = "Không có lời mời nào.";
    elements.friendRequests.appendChild(emptyMsg);
    return;
  }
  
  // Highlight the requests section when there are new requests
  if (requests.length > 0) {
    elements.requestsSection?.classList.add("has-requests");
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
  elements.friendList.innerHTML = "";
  elements.memberCheckboxes.innerHTML = "";
  for (const friend of currentFriends) {
    const item = document.createElement("div");
    item.className = "item";
    item.textContent = friend;
    const btn = document.createElement("button");
    btn.className = "btn small";
    btn.textContent = "Chat";
    btn.addEventListener("click", () => {
      setConversation({ type: "private", to: friend, label: friend });
    });
    item.appendChild(btn);
    elements.friendList.appendChild(item);

    const chk = document.createElement("label");
    chk.className = "item";
    chk.innerHTML = `<input type="checkbox" value="${friend}" /> ${friend}`;
    elements.memberCheckboxes.appendChild(chk);
  }
}

async function refreshGroups() {
  if (!currentUser) return;
  const res = await api.get(`/api/groups?me=${encodeURIComponent(currentUser)}`);
  elements.groupList.innerHTML = "";
  const groups = res.groups || [];

  for (const group of groups) {
    const item = document.createElement("div");
    item.className = "item";
    item.textContent = group.name;
    const btn = document.createElement("button");
    btn.className = "btn small";
    btn.textContent = "Chat";
    btn.addEventListener("click", () => {
      setConversation({
        type: "groupchat",
        to: group.id,
        label: group.name,
        groupName: group.name,
      });
    });
    item.appendChild(btn);
    elements.groupList.appendChild(item);
  }
}

function setConversation({ type, to, label, groupName }) {
  currentChat = { type, to, label, groupName };
  elements.conversationSelect.innerHTML = "";
  elements.conversationSelect.appendChild(makeOption(type + "|" + to, label));
  clearMessages();
}

function initConversationPicker() {
  elements.conversationSelect.innerHTML = "";
  elements.conversationSelect.appendChild(makeOption("group|all", "Phòng chung"));
  if (currentChat.type === "group" || currentChat.type === "groupchat") {
    // keep existing selection
  }
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
      btn.addEventListener("click", () => {
        setConversation({ type: "private", to: u, label: u });
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

function connectSocket() {
  if (!currentUser) return;

  const url = `${window.location.protocol}//${window.location.host}`;
  socket = io(url, { query: { username: currentUser } });

  socket.on("connect", () => {
    setStatus("Đã kết nối tới server.");
    // Send authentication event as fallback
    socket.emit("authenticate", { username: currentUser });
    console.log(`[Client] Socket connected, authenticating as ${currentUser}`);
  });

  socket.on("auth_success", (data) => {
    console.log(`[Client] Authentication successful: ${data.message}`);
  });

  socket.on("auth_error", (data) => {
    console.error(`[Client] Authentication failed: ${data.message}`);
  });

  socket.on("disconnect", () => {
    setStatus("Mất kết nối với server.");
  });

  socket.on("message", (payload) => {
    const { from, type, text, groupName } = payload;
    const isSelf = false;
    addMessage({ from, text, type, groupName, self: isSelf });
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
      // Play notification sound
      playSound("friend_request");
      
      // Show prominent notification
      showAuthMessage(`📥 Bạn có yêu cầu kết bạn từ ${from}`, false);
      
      // Add visual notification in a separate area if available
      if (elements.notificationArea) {
        const notification = document.createElement("div");
        notification.className = "notification friend-request-notification";
        notification.innerHTML = `
          <strong>Lời mời kết bạn mới</strong><br>
          <em>${from}</em> muốn kết bạn với bạn.
        `;
        elements.notificationArea.appendChild(notification);
        
        // Remove notification after 5 seconds
        setTimeout(() => {
          notification.remove();
        }, 5000);
      }
      
      // Update the friend requests list
      refreshFriendRequests();
      
      // Highlight requests section by scrolling to it
      if (elements.requestsSection) {
        elements.requestsSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  });
}

function sendChatMessage() {
  if (!currentUser || !socket) {
    setStatus("Vui lòng đăng nhập trước khi gửi tin nhắn.");
    return;
  }

  const text = elements.messageInput.value.trim();
  if (!text) return;

  const clientId = `cid_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  const payload = {
    from: currentUser,
    clientId,
    text,
  };

  if (currentChat.type === "group") {
    payload.type = "group";
    payload.to = "all";
  } else if (currentChat.type === "private") {
    payload.type = "private";
    payload.to = currentChat.to;
  } else if (currentChat.type === "groupchat") {
    payload.type = "groupchat";
    payload.groupId = currentChat.to;
  }

  addMessage({
    from: currentUser,
    text,
    type: currentChat.type === "groupchat" ? "groupchat" : currentChat.type,
    groupName: currentChat.groupName,
    self: true,
    clientId,
  });

  socket.emit("send_message", payload);
  elements.messageInput.value = "";
}

function showChatUI() {
  elements.authSection.style.display = "none";
  elements.chatControls.style.display = "block";
  elements.chatSection.style.display = "block";
  elements.userInfo.style.display = "flex";
  elements.usernameLabel.textContent = currentUser;
  elements.btnSend.disabled = false;
  elements.messageInput.disabled = false;
  initConversationPicker();
  refreshFriendRequests();
  refreshFriends();
  refreshGroups();
  connectSocket();
}

function logout() {
  currentUser = null;
  if (socket) {
    socket.disconnect();
    socket = null;
  }
  elements.authSection.style.display = "block";
  elements.chatControls.style.display = "none";
  elements.chatSection.style.display = "none";
  elements.userInfo.style.display = "none";
  elements.authMessage.textContent = "";
  clearMessages();
  elements.btnSend.disabled = true;
  elements.messageInput.disabled = true;
}

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

function init() {
  elements.btnLogin.addEventListener("click", login);
  elements.btnRegister.addEventListener("click", registerUser);
  elements.btnLogout.addEventListener("click", logout);
  elements.btnSend.addEventListener("click", sendChatMessage);
  elements.messageInput.addEventListener("keydown", (evt) => {
    if (evt.key === "Enter") {
      sendChatMessage();
    }
  });
  elements.searchUser.addEventListener("input", () => {
    doSearchUsers();
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
      refreshGroups();
    } else {
      elements.groupMessage.textContent = res.message || "Không thể tạo nhóm.";
    }
  });

  // Start hidden until login
  elements.btnSend.disabled = true;
  elements.messageInput.disabled = true;
  elements.chatSection.style.display = "none";

  // Default: show group chat
  setConversation({ type: "group", to: "all", label: "Phòng chung" });
}

init();
