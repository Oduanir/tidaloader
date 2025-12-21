import { h } from "preact";
import { useState, useRef, useEffect } from "preact/hooks";
import { api } from "../api/client";
import { downloadManager } from "../utils/downloadManager";
import { useToastStore } from "../stores/toastStore";

export function WeeklyJamsGenerator() {
  const [username, setUsername] = useState("");
  const [playlistType, setPlaylistType] = useState("weekly-jams");
  const [loading, setLoading] = useState(false);
  const [tracks, setTracks] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [error, setError] = useState(null);
  const [progressLogs, setProgressLogs] = useState([]);
  const logsEndRef = useRef(null);

  // Track status map: { idx: 'idle' | 'validating' | 'success' | 'error' }
  const [trackStatuses, setTrackStatuses] = useState({});

  const addToast = useToastStore((state) => state.addToast);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [progressLogs]);

  const handleFetch = async () => {
    if (!username.trim()) {
      setError("Please enter a ListenBrainz username");
      return;
    }

    setLoading(true);
    setError(null);
    setTracks([]);
    setSelected(new Set());
    setProgressLogs([]);
    setTrackStatuses({});

    try {
      // Validate = false for just fetching list
      const { progress_id } = await api.generateListenBrainzPlaylist(
        username.trim(),
        playlistType,
        false
      );

      const eventSource = api.createListenBrainzProgressStream(progress_id);

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "ping") return;

        if (data.type === "info" || data.type === "error") {
          setProgressLogs((prev) => [
            ...prev,
            {
              type: data.type,
              message: data.message,
              timestamp: new Date().toISOString(),
            },
          ]);
        }

        if (data.type === "complete") {
          setTracks(data.tracks);
          setLoading(false);
          eventSource.close();
          addToast(`Fetched ${data.tracks.length} tracks. Check availability before downloading.`, "success");
        }

        if (data.type === "error") {
          setError(data.message);
          setLoading(false);
          eventSource.close();
          addToast(`Failed to fetch playlist: ${data.message}`, "error");
        }
      };

      eventSource.onerror = () => {
        setError("Connection lost to server");
        setLoading(false);
        eventSource.close();
        addToast("Connection lost to server", "error");
      };
    } catch (err) {
      setError(err.message);
      setLoading(false);
      addToast(`Failed to fetch playlist: ${err.message}`, "error");
    }
  };

  const validateTrack = async (idx) => {
    const track = tracks[idx];
    if (!track) return;

    setTrackStatuses(prev => ({ ...prev, [idx]: 'validating' }));

    try {
      const result = await api.validateListenBrainzTrack(track);

      // Update track with result
      const newTracks = [...tracks];
      newTracks[idx] = result;
      setTracks(newTracks);

      if (result.tidal_exists) {
        setTrackStatuses(prev => ({ ...prev, [idx]: 'success' }));
        // Auto-select if found? Maybe not, require explicit "Download" click or select
        setSelected(prev => new Set(prev).add(result.tidal_id));
      } else {
        setTrackStatuses(prev => ({ ...prev, [idx]: 'error' }));
      }

      return result;
    } catch (e) {
      console.error("Validation failed", e);
      setTrackStatuses(prev => ({ ...prev, [idx]: 'error' }));
      return track; // Return original
    }
  };

  const validateAll = async () => {
    // Find all tracks that need validation
    const indicesToValidate = tracks.map((_, i) => i).filter(i => !tracks[i].tidal_exists && trackStatuses[i] !== 'error');

    let validatedCount = 0;

    // Process in batches to avoid overwhelming (though browser handles async well, server might rate limit)
    // Let's do logical concurrency of 3
    const concurrency = 3;
    for (let i = 0; i < indicesToValidate.length; i += concurrency) {
      const batch = indicesToValidate.slice(i, i + concurrency);
      await Promise.all(batch.map(idx => validateTrack(idx)));
    }
  };

  const toggleTrack = (tidalId) => {
    const newSelected = new Set(selected);
    if (newSelected.has(tidalId)) {
      newSelected.delete(tidalId);
    } else {
      newSelected.add(tidalId);
    }
    setSelected(newSelected);
  };

  const toggleAll = () => {
    // Only select tracks that EXIST
    const availableTracks = tracks.filter((t) => t.tidal_exists);

    if (selected.size === availableTracks.length) {
      setSelected(new Set());
    } else {
      setSelected(
        new Set(availableTracks.map((t) => t.tidal_id))
      );
    }
  };

  const handleDownloadSingle = async (idx) => {
    let track = tracks[idx];

    // If not validated, validate first
    if (!track.tidal_exists) {
      track = await validateTrack(idx);
    }

    if (track.tidal_exists) {
      const trackToDl = {
        ...track,
        tidal_track_id: track.tidal_id,
        tidal_artist_id: track.tidal_artist_id,
        tidal_album_id: track.tidal_album_id,
        cover: track.cover
      };
      downloadManager.addToServerQueue([trackToDl]);
      addToast(`Added "${track.title}" to queue`, "success");
    } else {
      addToast(`Could not find "${track.title}" on Tidal`, "error");
    }
  };

  const handleDownloadSelected = () => {
    const selectedTracks = tracks
      .filter((t) => selected.has(t.tidal_id))
      .map((t) => ({
        ...t,
        tidal_track_id: t.tidal_id,
        tidal_artist_id: t.tidal_artist_id,
        tidal_album_id: t.tidal_album_id,
        cover: t.cover
      }));

    if (selectedTracks.length === 0) return;

    downloadManager.addToServerQueue(selectedTracks).then((result) => {
      addToast(`Added ${result.added} tracks to download queue`, "success");
    });
  };

  const PLAYLIST_TYPES = [
    { id: "weekly-jams", label: "Weekly Jams" },
    { id: "weekly-exploration", label: "Weekly Exploration" },
    { id: "year-in-review-discoveries", label: "Year in Review: Discoveries" },
    { id: "year-in-review-missed", label: "Year in Review: Missed" }
  ];

  return (
    <div class="space-y-4 sm:space-y-6">
      <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 sm:gap-4">
        <div class="sm:col-span-1">
          <label class="block text-xs font-semibold text-text-muted mb-1.5 uppercase tracking-wider">
            Playlist Type
          </label>
          <select
            value={playlistType}
            onChange={(e) => setPlaylistType(e.target.value)}
            disabled={loading}
            class="input-field w-full h-[42px] text-sm"
          >
            {PLAYLIST_TYPES.map(type => (
              <option key={type.id} value={type.id}>{type.label}</option>
            ))}
          </select>
        </div>

        <div class="sm:col-span-2">
          <label class="block text-xs font-semibold text-text-muted mb-1.5 uppercase tracking-wider">
            ListenBrainz Username
          </label>
          <input
            type="text"
            value={username}
            onInput={(e) => setUsername(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !loading && username.trim()) {
                handleFetch();
              }
            }}
            placeholder="Username..."
            disabled={loading}
            class="input-field w-full h-[42px] text-sm"
          />
        </div>

        <div class="sm:col-span-1 flex items-end">
          <button
            onClick={handleFetch}
            disabled={loading || !username.trim()}
            class="btn-primary w-full h-[42px] flex items-center justify-center gap-2 text-sm"
          >
            {loading ? (
              <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            ) : (
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            )}
            Fetch Playlist
          </button>
        </div>
      </div>

      {loading && (
        <div class="p-4 bg-surface-alt border border-border-light rounded-lg">
          <div class="flex items-center gap-3 text-text-muted">
            <svg class="animate-spin h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Fetching playlist data...</span>
          </div>
          {progressLogs.length > 0 && (
            <div class="mt-2 text-xs font-mono text-text-muted">
              {progressLogs[progressLogs.length - 1].message}
            </div>
          )}
        </div>
      )}

      {error && (
        <div class="p-4 bg-red-500/10 border border-red-500/20 rounded-lg animate-fadeIn">
          <p class="text-sm text-red-500 flex items-center gap-2">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {error}
          </p>
        </div>
      )}

      {tracks.length > 0 && (
        <div class="space-y-4 animate-fadeIn">
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-border-light">
            <div class="flex items-center gap-3">
              <h3 class="text-lg font-bold text-text">
                Results
              </h3>
              <span class="px-2 py-0.5 rounded-full bg-surface-alt border border-border-light text-xs font-mono text-text-muted">
                {tracks.filter((t) => t.tidal_exists).length}/{tracks.length} FOUND
              </span>
            </div>

            <div class="flex items-center gap-3">
              <button
                onClick={validateAll}
                disabled={loading}
                class="text-xs font-medium text-primary hover:text-primary-light transition-colors uppercase tracking-wider flex items-center gap-1"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Check All
              </button>
              <div class="h-4 w-px bg-border"></div>
              <button
                onClick={toggleAll}
                class="text-xs font-medium text-text-muted hover:text-text transition-colors"
              >
                {selected.size > 0 && selected.size === tracks.filter((t) => t.tidal_exists).length ? "Deselect All" : "Select All Available"}
              </button>
              {selected.size > 0 && (
                <button class="btn-primary py-1.5 px-4 text-sm" onClick={handleDownloadSelected}>
                  Add {selected.size} to Queue
                </button>
              )}
            </div>
          </div>

          <div class="grid grid-cols-1 gap-2 max-h-[600px] overflow-y-auto pr-2 scrollbar-thin">
            {tracks.map((track, idx) => (
              <div
                key={idx}
                class={`group relative flex items-center p-2 rounded-lg border transition-all duration-200 ${track.tidal_exists
                    ? selected.has(track.tidal_id)
                      ? "bg-primary/5 border-primary/30"
                      : "bg-surface hover:bg-surface-alt border-border-light hover:border-border"
                    : trackStatuses[idx] === 'error'
                      ? "bg-red-500/5 border-red-500/10"
                      : "bg-surface border-border-light"
                  }`}
              >
                <div class="absolute left-2 top-1/2 -translate-y-1/2 z-10 flex items-center justify-center">
                  {/* Checkbox only if exists */}
                  {track.tidal_exists ? (
                    <input
                      type="checkbox"
                      checked={selected.has(track.tidal_id)}
                      onChange={() => toggleTrack(track.tidal_id)}
                      class={`w-5 h-5 rounded border-gray-600 text-primary focus:ring-primary focus:ring-offset-gray-900 bg-gray-800/50 transition-opacity`}
                    />
                  ) : (
                    // If not exists, maybe show a status icon or check button?
                    // Let's show check button if idle
                    trackStatuses[idx] === 'validating' ? (
                      <svg class="animate-spin h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : trackStatuses[idx] === 'error' ? (
                      <span class="text-red-500 font-bold text-xs">X</span>
                    ) : (
                      <span class="text-text-muted text-xs font-mono">{idx + 1}</span>
                    )
                  )}
                </div>

                <div class={`relative h-12 w-12 rounded overflow-hidden flex-shrink-0 ml-8 mr-3 bg-surface-alt`}>
                  {track.cover ? (
                    <img
                      src={api.getCoverUrl(track.cover, "160")}
                      alt={track.album}
                      class="h-full w-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div class="h-full w-full flex items-center justify-center text-text-muted/20">
                      <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 14.5c-2.49 0-4.5-2.01-4.5-4.5S9.51 7.5 12 7.5s4.5 2.01 4.5 4.5-2.01 4.5-4.5 4.5zm0-5.5c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z" /></svg>
                    </div>
                  )}
                </div>

                <div class="flex-1 min-w-0 pr-2">
                  <div class="flex items-center gap-2">
                    <p class={`text-sm font-semibold truncate ${track.tidal_exists ? 'text-text' : 'text-text-muted'}`}>
                      {track.title}
                    </p>
                    {!track.tidal_exists && trackStatuses[idx] === 'error' && (
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/10 text-red-500 uppercase">
                        Missing
                      </span>
                    )}
                  </div>
                  <p class="text-xs text-text-muted truncate mt-0.5">
                    {track.artist}
                    {track.album && <span class="opacity-50"> • {track.album}</span>}
                  </p>
                </div>

                <div class="flex items-center gap-2">
                  {!track.tidal_exists && trackStatuses[idx] !== 'error' && trackStatuses[idx] !== 'validating' && (
                    <button
                      onClick={() => validateTrack(idx)}
                      class="p-1.5 rounded hover:bg-surface-alt/50 text-text-muted hover:text-primary transition-colors"
                      title="Check Availability"
                    >
                      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </button>
                  )}

                  <button
                    onClick={() => handleDownloadSingle(idx)}
                    class={`p-1.5 rounded hover:bg-surface-alt/50 transition-colors ${track.tidal_exists ? 'text-text hover:text-primary' : 'text-text-muted hover:text-text'
                      }`}
                    title={track.tidal_exists ? "Add to Queue" : "Check & Add to Queue"}
                  >
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
