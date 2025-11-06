import { h } from "preact";
import { useState } from "preact/hooks";
import { api } from "../api/client";
import { useDownloadStore } from "../stores/downloadStore";

export function SearchBar() {
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState("track");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [error, setError] = useState(null);

  const addToQueue = useDownloadStore((state) => state.addToQueue);

  const handleSearch = async () => {
    if (!query.trim()) {
      setError("Please enter a search query");
      return;
    }

    setLoading(true);
    setError(null);
    setResults([]);
    setSelected(new Set());

    try {
      let result;
      if (searchType === "track") {
        result = await api.searchTracks(query.trim());
      } else if (searchType === "album") {
        result = await api.searchAlbums(query.trim());
      } else {
        result = await api.searchArtists(query.trim());
      }

      setResults(result.items || []);

      if (result.items.length === 0) {
        setError("No results found");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const toggleTrack = (trackId) => {
    const newSelected = new Set(selected);
    if (newSelected.has(trackId)) {
      newSelected.delete(trackId);
    } else {
      newSelected.add(trackId);
    }
    setSelected(newSelected);
  };

  const handleAddToQueue = () => {
    const selectedTracks = results
      .filter((r) => selected.has(r.id))
      .map((r) => ({
        tidal_id: r.id,
        title: r.title,
        artist: r.artist,
        album: r.album,
        tidal_exists: true,
      }));

    addToQueue(selectedTracks);
    alert(`Added ${selectedTracks.length} tracks to download queue!`);
    setSelected(new Set());
  };

  return (
    <div class="search-bar">
      <div class="search-input-group">
        <input
          type="text"
          value={query}
          onInput={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Search for tracks, albums, or artists..."
          disabled={loading}
        />
        <button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "⏳" : "🔍"} Search
        </button>
      </div>

      <div class="search-type">
        <label>
          <input
            type="radio"
            name="type"
            value="track"
            checked={searchType === "track"}
            onChange={() => setSearchType("track")}
          />
          Track
        </label>
        <label>
          <input
            type="radio"
            name="type"
            value="album"
            checked={searchType === "album"}
            onChange={() => setSearchType("album")}
          />
          Album
        </label>
        <label>
          <input
            type="radio"
            name="type"
            value="artist"
            checked={searchType === "artist"}
            onChange={() => setSearchType("artist")}
          />
          Artist
        </label>
      </div>

      {error && <div class="error-message">{error}</div>}

      {loading && <div class="loading-message">Searching Tidal...</div>}

      {searchType === "track" && results.length > 0 && (
        <TrackResults
          results={results}
          selected={selected}
          onToggle={toggleTrack}
          onAddToQueue={handleAddToQueue}
        />
      )}

      {searchType === "album" && results.length > 0 && (
        <AlbumResults
          results={results}
          onSelectAlbum={(album) => {
            // TODO: Implement album track fetching
            console.log("Selected album:", album);
          }}
        />
      )}

      {searchType === "artist" && results.length > 0 && (
        <ArtistResults
          results={results}
          onSelectArtist={(artist) => {
            // TODO: Implement artist track fetching
            console.log("Selected artist:", artist);
          }}
        />
      )}
    </div>
  );
}

function TrackResults({ results, selected, onToggle, onAddToQueue }) {
  return (
    <div class="search-results">
      <div class="results-header">
        <h3>Found {results.length} tracks</h3>
        {selected.size > 0 && (
          <button class="add-selected-btn" onClick={onAddToQueue}>
            Add {selected.size} to Queue
          </button>
        )}
      </div>

      <div class="track-list">
        {results.map((track) => (
          <div key={track.id} class="track-item search-result">
            <label>
              <input
                type="checkbox"
                checked={selected.has(track.id)}
                onChange={() => onToggle(track.id)}
              />
              {track.cover && (
                <img
                  src={api.getCoverUrl(track.cover, "80")}
                  alt={track.title}
                  class="track-cover"
                />
              )}
              <div class="track-info">
                <div class="track-title">{track.title}</div>
                <div class="track-meta">
                  {track.artist}
                  {track.album && ` • ${track.album}`}
                  {track.duration && (
                    <span class="track-duration">
                      {" "}
                      • {formatDuration(track.duration)}
                    </span>
                  )}
                </div>
              </div>
              {track.quality && (
                <span class="quality-badge">{track.quality}</span>
              )}
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}

function AlbumResults({ results, onSelectAlbum }) {
  const [expandedAlbum, setExpandedAlbum] = useState(null);
  const [albumTracks, setAlbumTracks] = useState([]);
  const [loadingTracks, setLoadingTracks] = useState(false);
  const [selectedTracks, setSelectedTracks] = useState(new Set());
  const addToQueue = useDownloadStore((state) => state.addToQueue);

  const handleAlbumClick = async (album) => {
    if (expandedAlbum === album.id) {
      setExpandedAlbum(null);
      setAlbumTracks([]);
      setSelectedTracks(new Set());
      return;
    }

    setExpandedAlbum(album.id);
    setLoadingTracks(true);

    try {
      const result = await api.get(`/album/${album.id}/tracks`);
      setAlbumTracks(result.items || []);

      // Auto-select all tracks
      setSelectedTracks(new Set(result.items.map((t) => t.id)));
    } catch (err) {
      console.error("Failed to load album tracks:", err);
      setAlbumTracks([]);
    } finally {
      setLoadingTracks(false);
    }
  };

  const toggleAlbumTrack = (trackId) => {
    const newSelected = new Set(selectedTracks);
    if (newSelected.has(trackId)) {
      newSelected.delete(trackId);
    } else {
      newSelected.add(trackId);
    }
    setSelectedTracks(newSelected);
  };

  const handleAddAlbumToQueue = () => {
    const tracks = albumTracks
      .filter((t) => selectedTracks.has(t.id))
      .map((t) => ({
        tidal_id: t.id,
        title: t.title,
        artist: t.artist,
        album: t.album,
        tidal_exists: true,
      }));

    addToQueue(tracks);
    alert(`Added ${tracks.length} tracks to download queue!`);
    setExpandedAlbum(null);
    setAlbumTracks([]);
    setSelectedTracks(new Set());
  };

  return (
    <div class="search-results">
      <h3>Found {results.length} albums</h3>
      <div class="album-grid">
        {results.map((album) => (
          <div key={album.id} class="album-card-wrapper">
            <div
              class={`album-card ${
                expandedAlbum === album.id ? "expanded" : ""
              }`}
              onClick={() => handleAlbumClick(album)}
            >
              {album.cover && (
                <img
                  src={api.getCoverUrl(album.cover, "320")}
                  alt={album.title}
                  class="album-cover"
                />
              )}
              <div class="album-info">
                <div class="album-title">{album.title}</div>
                <div class="album-artist">
                  {album.artist?.name || "Unknown Artist"}
                </div>
                {album.numberOfTracks && (
                  <div class="album-tracks">{album.numberOfTracks} tracks</div>
                )}
                {album.releaseDate && (
                  <div class="album-year">
                    {new Date(album.releaseDate).getFullYear()}
                  </div>
                )}
              </div>
            </div>

            {expandedAlbum === album.id && (
              <div class="album-tracks-list">
                {loadingTracks ? (
                  <div class="loading-message">Loading tracks...</div>
                ) : (
                  <>
                    <div class="album-tracks-header">
                      <label>
                        <input
                          type="checkbox"
                          checked={selectedTracks.size === albumTracks.length}
                          onChange={() => {
                            if (selectedTracks.size === albumTracks.length) {
                              setSelectedTracks(new Set());
                            } else {
                              setSelectedTracks(
                                new Set(albumTracks.map((t) => t.id))
                              );
                            }
                          }}
                        />
                        Select All ({albumTracks.length} tracks)
                      </label>
                      <button
                        class="add-selected-btn"
                        onClick={handleAddAlbumToQueue}
                        disabled={selectedTracks.size === 0}
                      >
                        Add {selectedTracks.size} to Queue
                      </button>
                    </div>

                    <div class="track-list">
                      {albumTracks.map((track) => (
                        <div key={track.id} class="track-item search-result">
                          <label>
                            <input
                              type="checkbox"
                              checked={selectedTracks.has(track.id)}
                              onChange={() => toggleAlbumTrack(track.id)}
                            />
                            <div class="track-info">
                              <div class="track-title">{track.title}</div>
                              <div class="track-meta">
                                {track.artist}
                                {track.duration && (
                                  <span class="track-duration">
                                    {" "}
                                    • {formatDuration(track.duration)}
                                  </span>
                                )}
                              </div>
                            </div>
                            {track.quality && (
                              <span class="quality-badge">{track.quality}</span>
                            )}
                          </label>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ArtistResults({ results, onSelectArtist }) {
  console.log("Artist results:", results); // Debug log

  return (
    <div class="search-results">
      <h3>Found {results.length} artists</h3>
      <div class="artist-list">
        {results.map((artist) => {
          console.log("Artist data:", artist); // Debug each artist

          return (
            <div
              key={artist.id}
              class="artist-item"
              onClick={() => onSelectArtist(artist)}
            >
              {artist.picture && (
                <img
                  src={api.getCoverUrl(artist.picture, "160")}
                  alt={artist.name}
                  class="artist-picture"
                  onError={(e) => {
                    console.error(
                      "Failed to load artist picture:",
                      artist.picture
                    );
                    e.target.style.display = "none";
                  }}
                />
              )}
              {!artist.picture && (
                <div class="artist-placeholder">
                  {artist.name?.charAt(0) || "?"}
                </div>
              )}
              <div class="artist-info">
                <div class="artist-name">{artist.name || "Unknown Artist"}</div>
                {artist.popularity && (
                  <div class="artist-popularity">
                    Popularity: {artist.popularity}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function formatDuration(seconds) {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}
