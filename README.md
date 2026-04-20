<div align="center">
  <img src="https://raw.githubusercontent.com/Chaitanyahoon/OpenJam/main/frontend/assets/logo.png" width="120" alt="OpenJam Icon" />
  <h1>Open Jam 🎵</h1>
  <p><strong>Listen Together, Discover Together.</strong></p>
  <p>A premium, real-time music synchronization platform designed with a pristine "Vinyl & Analog" aesthetic.</p>
</div>

<br />

> 🚀 **Live Production Demo:** https://openjam-lrnl.onrender.com/

> **Open Jam** democratizes the listening party. Built entirely on a **100% free-tier architecture**, it removes the friction of Spotify OAuth, paid APIs, and user logins. Jump straight into a room, build a queue, and vibe.

---

## ✨ Key Features & Advanced Engineering

* **Instant Anonymous Sessions:** No sign-up required. Pick a display name and instantly join the music via cryptographically signed cookies.
* **Just-In-Time Database Integrity:** Engineered a silent JIT upsert mechanism to dynamically generate user records in PostgreSQL, fully satisfying strict Foreign Key constraints without friction.
* **Democratic Playback & Vote-to-Skip:** Instead of direct skipping, listeners cast votes. The backend mathematically tracks thresholds dynamically, preventing malicious users from ruining the queue.
* **Real-time Sync & Fault Tolerance:** Ultra-fast Socket.IO architecture keeps playback synchronized to the millisecond. Implemented a silent background polling fallback to elegantly correct the UI if a WebSocket packet drops on poor mobile connections.
* **API Debouncing:** The YouTube search bar implements a custom debounce algorithm with an `AbortController` to prevent race conditions and protect YouTube API quotas.
* **Premium "Analog" UI & Glassmorphism:** A centralized design system featuring glowing amber accents, interactive vinyl visualizers, and a dynamic background that extracts and blurs the current album artwork.
* **Sleep/Inactive Mode:** An aggressive frontend performance optimization that pauses unnecessary DOM repaints (like the visual progress bar) when inactive, saving massive amounts of battery and CPU.

## 🛠 Tech Stack

**Backend:**
* [FastAPI](https://fastapi.tiangolo.com/) (High-performance Python API framework)
* [Socket.IO](https://socket.io/) (Real-time bidirectional event-based communication)
* [SQLAlchemy](https://www.sqlalchemy.org/) + PostgreSQL (Production) / SQLite (Local Dev)

**Frontend:**
* Pure Vanilla JavaScript (ES6+) + CSS Design Tokens (No heavy frameworks)
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

**2. Start the production container**
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```
*The production `docker-compose.prod.yml` expects a managed PostgreSQL database via `DATABASE_URL`.*

---
<div align="center">
  <i>Designed & Engineered by <a href="https://github.com/sharmax-vandana">Vandana</a></i>
</div>
