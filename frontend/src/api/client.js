/**
 * API client for Troi Tidal Downloader backend
 */

const API_BASE = "/api";

class ApiClient {
  /**
   * Make GET request
   */
  async get(path, params = {}) {
    const url = new URL(API_BASE + path, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, value);
      }
    });

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Make POST request
   */
  async post(path, data = {}) {
    const response = await fetch(API_BASE + path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  /**
   * Search for tracks
   */
  searchTracks(query) {
    return this.get("/search/tracks", { q: query });
  }

  /**
   * Search for albums
   */
  searchAlbums(query) {
    return this.get("/search/albums", { q: query });
  }

  /**
   * Search for artists
   */
  searchArtists(query) {
    return this.get("/search/artists", { q: query });
  }

  /**
   * Generate Troi playlist
   */
  generateTroiPlaylist(username, playlistType = "periodic-jams") {
    return this.post("/troi/generate", {
      username,
      playlist_type: playlistType,
    });
  }

  /**
   * Get cover URL from Tidal
   */
  getCoverUrl(coverId, size = "640") {
    if (!coverId) return null;

    // Handle different cover ID formats
    const cleanId = String(coverId).replace(/-/g, "/");
    return `https://resources.tidal.com/images/${cleanId}/${size}x${size}.jpg`;
  }
}

export const api = new ApiClient();
