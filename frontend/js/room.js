/* ========================================
   OPEN JAM — Room Page Controller v2
   Live members, volume control, democratic playback
   ======================================== */

const YOUTUBE_API_KEY = window.YOUTUBE_API_KEY || '';

(async function () {
  const roomId = getRoomIdFromUrl();
  if (!roomId) { window.location.href = '/'; return; }

  let currentUser = null;
  let currentRoomData = null;
  let isMuted = false;
  let currentVolume = 80;

  const socketClient = new SocketClient();
  const ytPlayer = new YouTubePlayer();

  // Wire YouTube player → socket (democratic control)
  ytPlayer.setControlCallback((action, extra) => {
    if (!currentUser) return;
    const payload = buildPlaybackPayload(action, extra);
    if (action === 'play') {
      socketClient.emit('playback_update', { ...payload, is_playing: true });
      updatePlayPauseBtn(true);
    } else if (action === 'pause') {
      socketClient.emit('playback_update', { ...payload, is_playing: false });
      updatePlayPauseBtn(false);
    } else if (action === 'ended') {
      socketClient.emit('next_track', { room_id: roomId });
    }
  });

  function buildPlaybackPayload(action, extra = {}) {
    const posMs = extra.position_ms !== undefined ? extra.position_ms : ytPlayer.positionMs;
    return {
      room_id: roomId,
      track_uri: ytPlayer.currentVideoId || '',
      track_name: $('#now-playing-title').textContent,
      artist: $('#now-playing-artist').textContent,
      album_art_url: $('#now-playing-art').src || '',
      position_ms: posMs,
      duration_ms: ytPlayer.durationMs || 0,
      is_playing: action === 'play',
    };
  }

  // ---- Play/Pause Icon state ----
  function updatePlayPauseBtn(playing) {
    const playIcon = $('#play-icon');
    const pauseIcon = $('#pause-icon');
    if (!playIcon || !pauseIcon) return;
    if (playing) {
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
    } else {
      playIcon.style.display = 'block';
      pauseIcon.style.display = 'none';
    }
  }

  // ---- Auth ----
  async function checkAuth() {
    try {
      const data = await API.getCurrentUser();
      currentUser = data.user;
    } catch { currentUser = null; }

    if (!currentUser) {
      const savedName = localStorage.getItem('openjam_display_name');
      if (savedName) {
        try {
          const data = await API.join(savedName);
          currentUser = data.user;
        } catch { /* silent */ }
      }
    }

    if (!currentUser) { window.location.href = '/'; return; }

    $('#navbar-user').style.display = 'flex';
    $('#navbar-username').textContent = currentUser.display_name;
    $('#navbar-avatar').textContent = getInitials(currentUser.display_name);
  }

  // Edit Name
  const editNameBtn = $('#btn-edit-name');
  if (editNameBtn) {
    editNameBtn.addEventListener('click', () => {
      const cur = $('#navbar-username').textContent;
      const newName = prompt('New display name:', cur);
      if (newName && newName.trim() !== cur) {
        const t = newName.trim();
        socketClient.setGuestName(t);
        localStorage.setItem('openjam_display_name', t);
      }
    });
  }

  socketClient.on('name_updated', (data) => {
    $('#navbar-username').textContent = data.display_name;
    $('#navbar-avatar').textContent = getInitials(data.display_name);
    if (currentUser) currentUser.display_name = data.display_name;
  });

  // ---- Volume Controls ----
  const volSlider = $('#volume-slider');
  const volPct = $('#volume-pct');
  const volIcon = $('#volume-icon');

  function applyVolume(vol) {
    currentVolume = vol;
    if (ytPlayer._ready && ytPlayer.player && ytPlayer.player.setVolume) {
      ytPlayer.player.setVolume(vol);
    }
    if (volPct) volPct.textContent = `${vol}%`;
    // Update slider visual fill
    if (volSlider) {
      volSlider.style.background = `linear-gradient(to right, var(--accent-primary) ${vol}%, var(--bg-hover) ${vol}%)`;
    }
    // Update mute icon
    const high = $('#vol-icon-high');
    const muted = $('#vol-icon-mute');
    if (high && muted) {
      high.style.display = vol > 0 ? 'block' : 'none';
      muted.style.display = vol > 0 ? 'none' : 'block';
    }
  }

  if (volSlider) {
    volSlider.addEventListener('input', (e) => {
      isMuted = false;
      applyVolume(parseInt(e.target.value));
    });
    applyVolume(80); // initial
  }

  if (volIcon) {
    volIcon.addEventListener('click', () => {
      if (isMuted) {
        isMuted = false;
        if (volSlider) volSlider.value = currentVolume || 80;
        applyVolume(currentVolume || 80);
      } else {
        isMuted = true;
        if (volSlider) volSlider.value = 0;
        applyVolume(0);
      }
    });
  }

  // Apply volume once YouTube player is ready
  const origReady = ytPlayer._createPlayer.bind(ytPlayer);
  // Hook: once player loads, set volume
  const volApplyInterval = setInterval(() => {
    if (ytPlayer._ready && ytPlayer.player && ytPlayer.player.setVolume) {
      ytPlayer.player.setVolume(currentVolume);
      clearInterval(volApplyInterval);
    }
  }, 500);

  // ---- Load Room ----
  async function loadRoom() {
    try {
      const data = await API.getRoom(roomId);
      currentRoomData = data;
      const room = data.room;
      document.title = `${room.name} — Open Jam`;

      const infoBar = $('#room-info-bar');
      if (infoBar) {
        infoBar.style.display = 'flex';
        $('#room-info-name').textContent = room.name;
        $('#room-info-host').textContent = `Hosted by ${room.host_name || 'Unknown'}`;
        const tags = (room.genre_tags || []).join(' · ');
        if (tags) $('#room-info-tags').textContent = `· ${tags}`;
      }

      if (currentUser && room.host_user_id === currentUser.id) {
        const closeBtn = $('#btn-close-room');
        if (closeBtn) closeBtn.style.display = 'inline-flex';
      }

      if (room.current_track) updateNowPlaying(room.current_track);
      renderQueue(data.queue);
      if (data.listeners) updateMembers(data.listeners);
    } catch {
      showToast('Room not found', 'error');
      setTimeout(() => window.location.href = '/', 2000);
    }
  }

  // ---- Now Playing ----
  const BLANK_ART = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Crect fill='%231a1410' width='300' height='300'/%3E%3Ctext x='150' y='165' text-anchor='middle' fill='%23444' font-size='64'%3E%F0%9F%8E5%3C/text%3E%3C/svg%3E`;

  function updateNowPlaying(track) {
    const artEl = $('#now-playing-art');
    const vinylRing = $('#vinyl-ring');
    const eqEl = $('#np-equalizer');

    if (!track || !track.track_uri) {
      $('#now-playing-title').textContent = 'Nothing playing';
      $('#now-playing-artist').textContent = 'Add a track to get started';
      artEl.src = BLANK_ART;
      artEl.classList.remove('is-playing');
      if (vinylRing) vinylRing.classList.remove('is-playing');
      if (eqEl) eqEl.style.display = 'none';
      if ($('#room-blur-bg')) $('#room-blur-bg').style.backgroundImage = 'none';
      updatePlayPauseBtn(false);
      return;
    }

    $('#now-playing-title').textContent = track.track_name;
    $('#now-playing-artist').textContent = track.artist;
    if (track.album_art_url && track.album_art_url !== artEl.src) {
      artEl.src = track.album_art_url;
      const bg = $('#room-blur-bg');
      if (bg) bg.style.backgroundImage = `url(${track.album_art_url})`;
    }

    const playing = track.is_playing !== false;
    if (playing) {
      artEl.classList.add('is-playing');
      if (vinylRing) vinylRing.classList.add('is-playing');
      if (eqEl) eqEl.style.display = 'flex';
    } else {
      artEl.classList.remove('is-playing');
      if (vinylRing) vinylRing.classList.remove('is-playing');
      if (eqEl) eqEl.style.display = 'none';
    }
    updatePlayPauseBtn(playing);

    ytPlayer.setTrack({
      track_uri: track.track_uri,
      position_ms: track.position_ms || 0,
      duration_ms: track.duration_ms || 0,
      is_playing: playing,
    });
  }

  // ---- Queue ----
  function renderQueue(queue) {
    const list = $('#queue-list');
    const empty = $('#queue-empty');
    const count = $('#queue-count');
    const pending = (queue || []).filter(i => i.status !== 'played');

    count.textContent = `${pending.length} track${pending.length !== 1 ? 's' : ''}`;

    if (pending.length === 0) {
      list.innerHTML = '';
      list.appendChild(empty);
      empty.style.display = 'flex';
      return;
    }

    empty.style.display = 'none';
    list.innerHTML = pending.map(item => {
      const hasVoted = currentUser && item.voter_ids && item.voter_ids.includes(currentUser.id);
      const isNowPlaying = item.status === 'playing';
      return `
      <div class="queue-item ${isNowPlaying ? 'now-playing' : ''}" data-item-id="${item.id}">
        <img class="queue-item-art" src="${item.album_art_url || ''}" alt=""
             onerror="this.style.background='var(--bg-elevated)'">
        <div class="queue-item-info">
          <div class="queue-item-name">${escapeHtml(item.track_name)}</div>
          <div class="queue-item-artist">${escapeHtml(item.artist)}</div>
          <div class="queue-item-added-by">by ${escapeHtml(item.added_by_name || 'Unknown')}</div>
        </div>
        ${isNowPlaying ? `
          <div class="equalizer" style="margin-right:4px;">
            <div class="equalizer-bar"></div>
            <div class="equalizer-bar"></div>
            <div class="equalizer-bar"></div>
          </div>` : `
          <button class="vote-btn ${hasVoted ? 'voted' : ''}" onclick="handleVote('${item.id}')"
                  title="${hasVoted ? 'Voted' : 'Upvote'}" ${hasVoted ? 'disabled' : ''}>
            ▲ <span>${item.votes}</span>
          </button>`}
      </div>`;
    }).join('');
  }

  window.handleVote = (itemId) => socketClient.voteTrack(itemId);

  // ---- Live Members ----
  function updateMembers(listeners) {
    const list = $('#members-list');
    const badge = $('#members-count-badge');
    if (!list) return;

    const arr = Array.isArray(listeners) ? listeners : [];
    if (badge) badge.textContent = arr.length;
    if (typeof listeners === 'number') {
      if (badge) badge.textContent = listeners;
      return;
    }

    list.innerHTML = arr.map(l => {
      const isSelf = currentUser && l.user_id === currentUser.id;
      const isHost = currentRoomData && l.user_id === currentRoomData.room?.host_user_id;
      return `
      <div class="member-item">
        <div class="member-avatar" title="${escapeHtml(l.display_name)}">
          ${getInitials(l.display_name)}
          <div class="member-online-dot"></div>
        </div>
        <div class="member-info">
          <div class="member-name">${escapeHtml(l.display_name)}${isSelf ? ' <span style="color:var(--text-muted);font-size:10px;">(you)</span>' : ''}</div>
          <div class="member-status">Listening</div>
        </div>
        ${isHost ? '<span class="member-host-badge">Host</span>' : ''}
      </div>`;
    }).join('');
  }

  // ---- Track Search (iTunes → YouTube ID) ----
  const searchInput = $('#track-search-input');
  const searchResults = $('#search-results');

  if (searchInput) {
    searchInput.addEventListener('input', debounce(async (e) => {
      const q = e.target.value.trim();
      if (!q) { searchResults.classList.remove('active'); return; }
      try {
        const data = await API.searchTracks(q);
        renderSearchResults(data.tracks);
      } catch (err) { console.error('Search error:', err); }
    }, 350));

    document.addEventListener('click', (e) => {
      if (!e.target.closest('#queue-search-container')) searchResults.classList.remove('active');
    });
  }

  function renderSearchResults(tracks) {
    if (!tracks || !tracks.length) {
      searchResults.innerHTML = `<div style="padding:var(--sp-4);text-align:center;color:var(--text-muted);font-size:var(--fs-sm);">No results found</div>`;
      searchResults.classList.add('active');
      return;
    }

    searchResults.innerHTML = tracks.map(t => `
      <div class="search-result-item"
        data-uri="${escapeHtml(t.uri)}" data-name="${escapeHtml(t.name)}"
        data-artist="${escapeHtml(t.artist)}" data-art="${t.album_art_url || ''}"
        data-duration="${t.duration_ms || 0}">
        <img class="search-result-art" src="${t.album_art_url || ''}" alt=""
             onerror="this.style.background='var(--bg-elevated)'">
        <div class="search-result-info">
          <div class="search-result-name">${escapeHtml(t.name)}</div>
          <div class="search-result-artist">${escapeHtml(t.artist)}</div>
        </div>
        <button class="btn btn-ghost" style="font-size:20px;flex-shrink:0;padding:0 var(--sp-2);">+</button>
      </div>`).join('');
    searchResults.classList.add('active');

    searchResults.querySelectorAll('.search-result-item').forEach(item => {
      item.addEventListener('click', async () => {
        const query = item.dataset.uri;
        const name = item.dataset.name;
        const artist = item.dataset.artist;
        searchResults.classList.remove('active');
        searchInput.value = '';

        showToast('Finding on YouTube... 🎵', 'info');
        let videoId = null;
        if (YOUTUBE_API_KEY) {
          videoId = await API.resolveYouTubeId(query, YOUTUBE_API_KEY);
        }
        if (!videoId) {
          showToast('Track not found on YouTube. Try another.', 'error');
          return;
        }

        socketClient.addToQueue({
          track_uri: videoId,
          track_name: name,
          artist,
          album_art_url: item.dataset.art,
          duration_ms: parseInt(item.dataset.duration) || 0,
        });
        showToast(`Added: ${name} — ${artist}`, 'success');
      });
    });
  }

  // ---- Democratic Controls ----
  const playPauseBtn = $('#btn-play-pause');
  if (playPauseBtn) {
    playPauseBtn.addEventListener('click', () => {
      const playing = ytPlayer.isPlaying;
      if (ytPlayer._ready && ytPlayer.player) {
        if (playing) ytPlayer.player.pauseVideo();
        else ytPlayer.player.playVideo();
      }
      updatePlayPauseBtn(!playing);
      socketClient.emit('playback_update', {
        ...buildPlaybackPayload(playing ? 'pause' : 'play'),
        is_playing: !playing,
      });
    });
  }

  const nextBtn = $('#btn-next-track');
  if (nextBtn) nextBtn.addEventListener('click', () => socketClient.nextTrack());

  const closeRoomBtn = $('#btn-close-room');
  if (closeRoomBtn) {
    closeRoomBtn.addEventListener('click', async () => {
      if (!confirm('Close this room?')) return;
      try {
        await API.closeRoom(roomId);
        showToast('Room closed', 'success');
        setTimeout(() => window.location.href = '/', 1500);
      } catch { showToast('Failed to close room', 'error'); }
    });
  }

  // ---- Chat ----
  function renderChatMessage(msg) {
    const messagesEl = $('#chat-messages');
    const empty = $('#chat-empty');
    if (empty) empty.style.display = 'none';

    const isSelf = currentUser && msg.user_id === currentUser.id;
    const div = document.createElement('div');
    div.className = `chat-message ${isSelf ? 'self' : ''}`;
    div.innerHTML = `
      <div class="avatar avatar-sm">${getInitials(msg.user_name)}</div>
      <div class="chat-message-content">
        <div class="chat-message-header">
          <span class="chat-message-name">${escapeHtml(msg.user_name)}</span>
          <span class="chat-message-time">${timeAgo(msg.timestamp)}</span>
        </div>
        <div class="chat-message-text">${escapeHtml(msg.content)}</div>
      </div>`;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  const chatInput = $('#chat-input');
  const sendBtn = $('#btn-send-chat');

  function sendMessage() {
    const msg = chatInput.value.trim();
    if (!msg) return;
    socketClient.sendChat(msg);
    chatInput.value = '';
  }

  if (sendBtn) sendBtn.addEventListener('click', sendMessage);
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
  }

  // ---- Socket Event Handlers ----
  socketClient.on('chat_message', (data) => renderChatMessage(data));

  socketClient.on('chat_history', (data) => {
    const empty = $('#chat-empty');
    if (data.messages?.length) {
      if (empty) empty.style.display = 'none';
      data.messages.forEach(m => renderChatMessage(m));
    }
  });

  socketClient.on('queue_updated', (data) => renderQueue(data.queue));

  socketClient.on('playback_sync', (data) => {
    if (data?.track_uri) {
      updateNowPlaying(data);
      ytPlayer.syncPosition(data.position_ms, data.is_playing);
    }
  });

  socketClient.on('track_changed', (data) => {
    if (data) {
      updateNowPlaying(data);
      showToast(`Now: ${data.track_name}`, 'success');
    } else {
      updateNowPlaying(null);
    }
  });

  socketClient.on('user_joined', (data) => {
    showToast(`${data.display_name} joined 🎧`, 'info');
  });

  socketClient.on('user_left', (data) => {
    showToast(`${data.display_name} left`, 'info');
  });

  socketClient.on('listener_count', (data) => {
    updateMembers(data.listeners || data.count || []);
  });

  socketClient.on('room_closed', (data) => {
    showToast(data?.reason || 'Room closed', 'info');
    setTimeout(() => window.location.href = '/', 2500);
  });

  window.addEventListener('beforeunload', () => {
    socketClient.leaveRoom(roomId);
    ytPlayer.destroy();
  });

  // ---- Init ----
  await checkAuth();
  await loadRoom();
  socketClient.connect();
  socketClient.joinRoom(roomId);
})();
