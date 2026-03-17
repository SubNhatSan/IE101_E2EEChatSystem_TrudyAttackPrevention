## Architecture - Web Chat System (Refactored)

### Project Structure

```
ChattingApp/webapp/
├── app.py                    # Entrypoint chính
├── config.py                 # Configuration (SECRET_KEY, SESSION, etc)
├── extensions.py             # Flask extensions (SocketIO)
├── requirements.txt          # Dependencies
│
├── storage/                  # Data storage layer
│   ├── __init__.py
│   ├── db.py                 # Load/save JSON files + thread safety
│   ├── users.py              # User operations (get_user, set_user, etc)
│   ├── groups.py             # Group operations
│   └── messages.py           # Message storage & retrieval
│
├── routes/                   # REST API routes
│   ├── __init__.py
│   ├── auth.py               # Register, Login, Get Users
│   ├── friends.py            # Friend requests, accept/decline
│   ├── groups.py             # Create groups
│   ├── messages.py           # Load message history
│   └── debug.py              # Debug endpoints
│
├── sockets/                  # WebSocket handlers
│   └── __init__.py           # Connect, Disconnect, Send Message
│
├── data/                     # Data files
│   ├── users.json
│   ├── groups.json
│   └── messages.json
│
├── templates/
│   └── index.html            # Single page (Messenger-style layout)
│
└── static/
    ├── app.js                # Frontend logic (session + chat list)
    └── style.css             # UI styles (new Messenger layout)
```

### Key Features

#### 1. **Modular Backend** ✅
- `storage/`: Centralized data access layer
- `routes/`: Clean REST API endpoints
- `sockets/`: WebSocket event handlers
- All new features separate from old code

#### 2. **Message Persistence** ✅
- Messages saved in `data/messages.json`
- Conversation format: `type|id` (e.g., `private|user1|user2`, `groupchat|group_1`)
- API endpoint `/api/messages/history` to load past messages
- History loaded when user switches conversations

#### 3. **Session Management** ✅
- Session stored in browser's `localStorage`
- Auto-reload page → user stays logged in if session exists
- Logout button clears session
- Session includes username and basic user info

#### 4. **Chat List UI (Messenger-style)** ✅
- Left sidebar with chat list
- "Phòng chung" (common room) always available
- Friends section (scrollable)
- Groups section (scrollable)
- Search bar for chats
- Collapsible "Manage" panel for friend requests & group creation
- Active chat highlighted
- Click to switch conversations and load history

#### 5. **Message History on Page Reload** ✅
- When page loads, if user is logged in:
  1. Restore session from localStorage
  2. Show chat UI
  3. Load message history for current conversation
  4. Connect WebSocket

### Data Flow

#### Login/Registration
```
Client (auth.html) → POST /api/register or /api/login
                  → Save session to localStorage
                  → Load friends, groups, friend requests
                  → Connect WebSocket
                  → Load message history
```

#### Send Message
```
Client (app.js: sendChatMessage)
  → Socket emit "send_message"
  → Server handler: save to messages.json + emit to recipients
  → Recipients: receive "message" event + display
```

#### Load Message History
```
Client: setConversation() or page reload
  → GET /api/messages/history?type=private&to=friend
  → Server: lookup conversation_id, return stored messages
  → Client: display all past messages
```

#### Manage Panel (Friends/Groups)
```
- Search users: GET /api/users?q=...
- Send request: POST /api/friends/request
- Accept/decline: POST /api/friends/respond
- View requests: GET /api/friends/requests
- Create group: POST /api/groups/create
```

### File Dependencies

```
app.py (main)
  ├─ extensions.py (socketio)
  ├─ config.py (settings)
  ├─ storage/__init__.py (all storage functions)
  ├─ routes/__init__.py (all blueprints)
  │   ├─ auth.py → storage, app context
  │   ├─ friends.py → storage, socketio
  │   ├─ groups.py → storage
  │   ├─ messages.py → storage
  │   └─ debug.py → storage
  └─ sockets/__init__.py → storage, socketio, extensions

Frontend (app.js)
  ├─ localStorage (for session)
  ├─ fetch API (for REST calls)
  └─ Socket.IO library (for real-time)
```

### Configuration

#### Environment Variables (optional)
- `SECRET_KEY`: Flask secret (defaults to "dev-secret-key...")
- `FLASK_DEBUG`: Enable debug mode (True/False)
- `FLASK_HOST`: Server host (default: 127.0.0.1)
- `FLASK_PORT`: Server port (default: 5000)

### How to Run

```bash
# Install dependencies
cd ChattingApp/webapp
pip install -r requirements.txt

# Run server
python app.py
# or
python -m flask run

# Open browser
http://localhost:5000
```

### User Session Flow

1. **First Visit**
   - Page loads, checks localStorage for session
   - No session found → show auth page
   - User registers or logs in
   - Session saved to localStorage

2. **F5 Refresh**
   - Page loads, checks localStorage
   - Session found → skip auth, load chat UI
   - Load friends/groups/requests from API
   - Load message history for last conversation
   - Connect WebSocket

3. **WebSocket Persistence**
   - User stays in chat area
   - Messages sent/received real-time via WebSocket
   - Messages also saved to messages.json
   - If connection drops, reconnect attempts automatically

4. **Logout**
   - User clicks "Đăng xuất"
   - localStorage cleared
   - Socket disconnected
   - Back to auth page

### Security Notes (Important)

⚠️ **This is a demo project. For production:**
- Add password hashing (bcrypt)
- Implement proper authentication (JWT)
- Add HTTPS encryption
- Validate all user inputs
- Rate limiting on API endpoints
- CORS configuration
- Authentication headers for API
- Message encryption

### Future Improvements

- [ ] User profiles
- [ ] Block users
- [ ] Read receipts
- [ ] Typing indicators
- [ ] File sharing
- [ ] Emoji reactions
- [ ] Delete/edit messages
- [ ] Push notifications
- [ ] Dark mode
