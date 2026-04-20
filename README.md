<div align="center">
  <img src="https://raw.githubusercontent.com/Chaitanyahoon/OpenJam/main/frontend/assets/logo.png" width="120" alt="OpenJam Icon" />
  <h1>Open Jam 🎵</h1>
  <p><strong>Listen Together, Discover Together.</strong></p>
  <p>A premium, real-time music synchronization platform designed with a pristine "Vinyl & Analog" aesthetic.</p>
</div>

<br />

> 🚀 **Live Production Demo:** [https://openjam-lrnl.onrender.com/] 

> **Open Jam** democratizes the listening party. Built entirely on a **100% free-tier architecture**, it removes the friction of Spotify OAuth, paid APIs, and user logins. Jump straight into a room, build a queue, and vibe.

---

## ✨ Key Features

* **Instant Anonymous Sessions:** No sign-up required. Pick a display name and instantly join the music via cryptographically signed cookies.
* **Intelligent Track Resolution:** Powered by the high-availability iTunes API for stunning album art + metadata, seamlessly resolving audio via the YouTube IFrame API—bypassing rate limits.
* **Democratic Playback:** Anyone in the room can add tracks, but designated **Hosts** maintain absolute playback control and synchronization authority.
* **Real-time Sync:** Ultra-fast Socket.IO architecture keeps playback cursors, track queues, listener presence, and live chat synchronized across all connected clients.
* **Premium "Analog" UI:** A centralized design system featuring glowing amber accents, interactive vinyl visualizers, responsive volume sliders, and live inline member statuses.

## 🛠 Tech Stack

**Backend:**
* [FastAPI](https://fastapi.tiangolo.com/) (High-performance Python API framework)
* [Socket.IO](https://socket.io/) (Real-time bidirectional event-based communication)
* [SQLAlchemy](https://www.sqlalchemy.org/) + SQLite/PostgreSQL (Flexible ORM architecture)

**Frontend:**
* Pure Vanilla JavaScript + CSS Design Tokens 
* YouTube IFrame API

## 🚀 Quick Setup (Local Development)

Getting Open Jam running locally is incredibly simple. You only need a single Google Cloud YouTube API Key.

**1. Clone & Install**
```bash
git clone https://github.com/Chaitanyahoon/OpenJam.git
cd OpenJam
python -m venv .venv
source .venv/bin/activate  # Or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

**2. Environment Configuration**
Create a `.env` file in the root directory:
```env
YOUTUBE_API_KEY=your_google_cloud_youtube_data_api_v3_key
SECRET_KEY=generate_a_random_secure_string_here
```

**3. Run the Development Server**
```bash
python run.py
```
*Open Jam will now be live on http://localhost:8000*

## 🐳 Production Deployment

Open Jam is fully containerized and production-ready out of the box.

**1. Create a production env file**
```bash
cp .env.production.example .env.production
```

Update `.env.production` with your real values:
```env
YOUTUBE_API_KEY=your_google_cloud_youtube_data_api_v3_key
SECRET_KEY=generate_a_long_random_secret
ALLOWED_ORIGINS=https://your-domain.com
DATABASE_URL=postgresql://jamgres_user:your_password@dpg-d7j6n4hf9bms738j57sg-a.oregon-postgres.render.com/jamgres?sslmode=require
```

If you are using a Render external PostgreSQL URL, keep `?sslmode=require` on the connection string.

**2. Start the production container**
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```
*The production `docker-compose.prod.yml` expects a managed PostgreSQL database via `DATABASE_URL`.*

**3. Open the app**

The app listens on port `8000` inside the container. Point your domain or reverse proxy to that port on the machine running Docker.

---
<div align="center">
  <i>Designed & Engineered by <a href="https://github.com/Chaitanyahoon">Chaitanyahoon</a></i>
</div>
