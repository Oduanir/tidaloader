import { h } from "preact";
import { useState } from "preact/hooks";
import { api } from "../api/client";
import { useDownloadStore } from "../stores/downloadStore";

export function TroiGenerator() {
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [tracks, setTracks] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [error, setError] = useState(null);

  const addToQueue = useDownloadStore((state) => state.addToQueue);
  const quality = useDownloadStore((state) => state.quality);

  const handleGenerate = async (type) => {
    if (!username.trim()) {
      setError("Please enter a ListenBrainz username");
      return;
    }

    setLoading(true);
    setError(null);
    setTracks([]);
    setSelected(new Set());

    try {
      const result = await api.generateTroiPlaylist(username.trim(), type);
      setTracks(result.tracks);

      // Auto-select tracks that exist on Tidal
      const autoSelected = new Set(
        result.tracks.filter((t) => t.tidal_exists).map((t) => t.tidal_id)
      );
      setSelected(autoSelected);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
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
    if (selected.size === tracks.filter((t) => t.tidal_exists).length) {
      setSelected(new Set());
    } else {
      setSelected(
        new Set(tracks.filter((t) => t.tidal_exists).map((t) => t.tidal_id))
      );
    }
  };

  const handleDownload = () => {
    const selectedTracks = tracks.filter((t) => selected.has(t.tidal_id));
    addToQueue(selectedTracks);
    alert(`Added ${selectedTracks.length} tracks to download queue!`);
  };

  return (
    <div class="troi-generator">
      <div class="input-section">
        <label>
          ListenBrainz Username:
          <input
            type="text"
            value={username}
            onInput={(e) => setUsername(e.target.value)}
            placeholder="z3r069"
            disabled={loading}
          />
        </label>

        <div class="button-group">
          <button
            onClick={() => handleGenerate("daily-jams")}
            disabled={loading}
          >
            {loading ? "⏳ Generating..." : "🎲 Generate Daily Jams"}
          </button>
          <button
            onClick={() => handleGenerate("periodic-jams")}
            disabled={loading}
          >
            {loading ? "⏳ Generating..." : "📅 Generate Periodic Jams"}
          </button>
        </div>
      </div>

      {error && <div class="error-message">✗ {error}</div>}

      {tracks.length > 0 && (
        <>
          <div class="track-controls">
            <label>
              <input
                type="checkbox"
                checked={
                  selected.size === tracks.filter((t) => t.tidal_exists).length
                }
                onChange={toggleAll}
              />
              Select All ({tracks.filter((t) => t.tidal_exists).length} tracks)
            </label>
            <select
              value={quality}
              onChange={(e) =>
                useDownloadStore.setState({ quality: e.target.value })
              }
            >
              <option value="LOSSLESS">LOSSLESS</option>
              <option value="HIGH">HIGH (320kbps)</option>
              <option value="LOW">LOW (96kbps)</option>
            </select>
          </div>

          <div class="track-list">
            {tracks.map((track, idx) => (
              <div
                key={idx}
                class={`track-item ${track.tidal_exists ? "" : "not-found"}`}
              >
                <label>
                  <input
                    type="checkbox"
                    checked={selected.has(track.tidal_id)}
                    onChange={() => toggleTrack(track.tidal_id)}
                    disabled={!track.tidal_exists}
                  />
                  <span class="track-info">
                    <strong>{track.artist}</strong> - {track.title}
                  </span>
                  {!track.tidal_exists && (
                    <span class="not-found-label">Not Found</span>
                  )}
                </label>
              </div>
            ))}
          </div>

          <button
            class="download-btn"
            onClick={handleDownload}
            disabled={selected.size === 0}
          >
            Download Selected ({selected.size}/{tracks.length})
          </button>
        </>
      )}
    </div>
  );
}
