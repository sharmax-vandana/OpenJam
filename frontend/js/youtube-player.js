/* ========================================
   OPEN JAM — YouTube Player
   Full-length playback via YouTube IFrame API
   Replaces spotify-player.js
   ======================================== */

class YouTubePlayer {
  constructor() {
    this.player = null;           // YT.Player instance
    this.currentVideoId = null;
    this.positionMs = 0;
    this.durationMs = 0;
    this.isPlaying = false;
    this.progressInterval = null;
    this.onProgressUpdate = null;
    this._ready = false;
    this._pendingLoad = null;     // { videoId, startSeconds } to load once ready
    this._suppressStateChange = false;
    this._onPlaybackControl = null; // callback(action, data) for socket emit
    this._initYouTubeAPI();
  }

  /** Load YouTube IFrame API if not already loaded. */
  _initYouTubeAPI() {
    if (window.YT && window.YT.Player) {
      this._createPlayer();
      return;
    }
    window.onYouTubeIframeAPIReady = () => this._createPlayer();
    if (!document.getElementById('youtube-iframe-api')) {
      const tag = document.createElement('script');
      tag.id = 'youtube-iframe-api';
      tag.src = 'https://www.youtube.com/iframe_api';
      document.head.appendChild(tag);
    }
  }

  _createPlayer() {
    const container = document.getElementById('youtube-player-container');
    if (!container) return;

    this.player = new YT.Player('youtube-player-container', {
      height: '0',
      width: '0',
      playerVars: {
        autoplay: 1,
        controls: 0,
        disablekb: 1,
        fs: 0,
        modestbranding: 1,
        rel: 0,
        origin: window.location.origin,
      },
      events: {
        onReady: () => {
          this._ready = true;
          if (this._pendingLoad) {
            const { videoId, startSeconds } = this._pendingLoad;
            this._pendingLoad = null;
            this._loadVideo(videoId, startSeconds);
          }
        },
        onStateChange: (event) => this._onStateChange(event),
      },
    });
  }

  _onStateChange(event) {
    if (this._suppressStateChange) return;
    const state = event.data;

    // YT.PlayerState: PLAYING=1, PAUSED=2, ENDED=0, BUFFERING=3
    if (state === YT.PlayerState.PLAYING) {
      this.isPlaying = true;
      this.startProgressTimer();
      this._emitControlEvent('play');
    } else if (state === YT.PlayerState.PAUSED) {
      this.isPlaying = false;
      this.stopProgressTimer();
      const pos = this.player ? Math.round(this.player.getCurrentTime() * 1000) : this.positionMs;
      this._emitControlEvent('pause', { position_ms: pos });
    } else if (state === YT.PlayerState.ENDED) {
      this.isPlaying = false;
      this.stopProgressTimer();
      this._emitControlEvent('ended');
    }
    this.updateDisplay();
  }

  _emitControlEvent(action, extra = {}) {
    if (this._onPlaybackControl) {
      this._onPlaybackControl(action, { ...extra });
    }
  }

  /** Called by room.js to wire up socket emissions on local user interaction. */
  setControlCallback(fn) {
    this._onPlaybackControl = fn;
  }

  _loadVideo(videoId, startSeconds = 0) {
    if (!this._ready || !this.player) {
      this._pendingLoad = { videoId, startSeconds };
      return;
    }
    this._suppressStateChange = true;
    this.player.loadVideoById({ videoId, startSeconds });
    setTimeout(() => { this._suppressStateChange = false; }, 1000);
  }

  /** Called when a new track starts (from socket track_changed or initial load). */
  setTrack(trackData) {
    const videoId = trackData.track_uri;  // track_uri is now a YouTube video ID
    const startSeconds = Math.round((trackData.position_ms || 0) / 1000);
    this.positionMs = trackData.position_ms || 0;
    this.durationMs = trackData.duration_ms || 0;
    this.isPlaying = trackData.is_playing !== false;

    if (videoId && videoId !== this.currentVideoId) {
      this.currentVideoId = videoId;
      this._loadVideo(videoId, startSeconds);
    }

    if (this.isPlaying) {
      this.startProgressTimer();
    } else {
      this.stopProgressTimer();
    }
    this.updateDisplay();
  }

  /** Called on every playback_sync socket event. */
  syncPosition(positionMs, isPlaying) {
    this.isPlaying = isPlaying;
    this.positionMs = positionMs;

    if (this._ready && this.player && this.player.getPlayerState) {
      const actualMs = Math.round((this.player.getCurrentTime?.() || 0) * 1000);
      const drift = Math.abs(actualMs - positionMs);

      this._suppressStateChange = true;
      if (drift > 3000) {
        this.player.seekTo(positionMs / 1000, true);
      }
      if (isPlaying) {
        this.player.playVideo();
        this.startProgressTimer();
      } else {
        this.player.pauseVideo();
        this.stopProgressTimer();
      }
      setTimeout(() => { this._suppressStateChange = false; }, 500);
    }

    this.updateDisplay();
  }

  startProgressTimer() {
    this.stopProgressTimer();
    this.progressInterval = setInterval(() => {
      if (this._ready && this.player && this.player.getCurrentTime) {
        const actualMs = Math.round(this.player.getCurrentTime() * 1000);
        if (actualMs > 0) this.positionMs = actualMs;
      } else if (this.isPlaying) {
        this.positionMs += 1000;
      }
      this.updateDisplay();
    }, 1000);
  }

  stopProgressTimer() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
  }

  updateDisplay() {
    const fill = document.getElementById('progress-fill');
    const elapsed = document.getElementById('time-elapsed');
    const total = document.getElementById('time-total');

    if (fill) {
      const pct = this.durationMs > 0 ? (this.positionMs / this.durationMs) * 100 : 0;
      fill.style.width = `${Math.min(pct, 100)}%`;
    }
    if (elapsed) elapsed.textContent = formatTime(this.positionMs);
    if (total) total.textContent = formatTime(this.durationMs);
    if (this.onProgressUpdate) {
      this.onProgressUpdate(this.positionMs, this.durationMs, this.isPlaying);
    }
  }

  destroy() {
    this.stopProgressTimer();
    if (this.player && this.player.destroy) {
      try { this.player.destroy(); } catch (_) {}
    }
  }
}
