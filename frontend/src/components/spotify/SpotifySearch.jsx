import { h } from "preact";
import { useState } from "preact/hooks";
import { api } from "../../api/client";
import { useToastStore } from "../../stores/toastStore";

const AddModal = ({ playlist, onClose, onAdd }) => {
    const [frequency, setFrequency] = useState("daily");
    const [quality, setQuality] = useState("LOSSLESS");
    const [useFolder, setUseFolder] = useState(true);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async () => {
        setLoading(true);
        try {
            await onAdd({
                uuid: playlist.id,
                name: playlist.name,
                frequency,
                quality,
                source: "spotify",
                extra_config: { spotify_id: playlist.id },
                use_playlist_folder: useFolder
            });
            onClose();
        } catch (e) {
            console.error(e);
            // Error handling done by caller usually, but good to have
        } finally {
            setLoading(false);
        }
    };

    return (
        <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fadeIn">
            <div class="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-md p-6 m-4 animate-scaleUp">
                <h3 class="text-xl font-bold text-text mb-4">Monitor Playlist</h3>

                <div class="mb-4 flex items-center gap-4">
                    <img src={playlist.image} alt={playlist.name} class="w-16 h-16 rounded-md object-cover bg-surface-alt" />
                    <div>
                        <p class="font-semibold text-text">{playlist.name}</p>
                        <p class="text-sm text-text-muted">{playlist.owner}</p>
                        <p class="text-xs text-text-muted mt-1">{playlist.track_count} tracks</p>
                    </div>
                </div>

                <div class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-text-muted mb-1.5 uppercase tracking-wider">Sync Frequency</label>
                        <select
                            value={frequency}
                            onChange={(e) => setFrequency(e.target.value)}
                            class="input-field w-full"
                        >
                            <option value="manual">Manual (No Auto-Sync)</option>
                            <option value="daily">Daily (Every 24h)</option>
                            <option value="weekly">Weekly (Every 7 days)</option>
                            <option value="monthly">Monthly</option>
                        </select>
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-text-muted mb-1.5 uppercase tracking-wider">Quality</label>
                        <select
                            value={quality}
                            onChange={(e) => setQuality(e.target.value)}
                            class="input-field w-full"
                        >
                            <option value="LOW">Low (96kbps AAC)</option>
                            <option value="HIGH">High (320kbps AAC)</option>
                            <option value="LOSSLESS">Lossless (1411kbps FLAC)</option>
                            <option value="HI_RES">Hi-Res (Max Available)</option>
                        </select>
                    </div>

                    <div class="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="useFolder"
                            checked={useFolder}
                            onChange={(e) => setUseFolder(e.target.checked)}
                            class="rounded border-border bg-surface-alt text-primary focus:ring-primary"
                        />
                        <label for="useFolder" class="text-sm text-text">Use Playlist Folder</label>
                    </div>
                </div>

                <div class="flex justify-end gap-3 mt-6">
                    <button onClick={onClose} class="btn-ghost" disabled={loading}>Cancel</button>
                    <button onClick={handleSubmit} class="btn-primary" disabled={loading}>
                        {loading ? 'Adding...' : 'Start Monitoring'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export function SpotifySearch() {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [selectedPlaylist, setSelectedPlaylist] = useState(null);
    const addToast = useToastStore((state) => state.addToast);

    const handleSearch = async () => {
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        setResults([]);

        try {
            const data = await api.searchSpotifyPlaylists(query);
            setResults(data.items || []);
        } catch (err) {
            setError(err.message);
            addToast(`Search failed: ${err.message}`, "error");
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async (config) => {
        try {
            await api.monitorPlaylist(
                config.uuid,
                config.name,
                config.frequency,
                config.quality,
                config.source,
                config.extra_config,
                config.use_playlist_folder
            );
            addToast(`Started monitoring "${config.name}"`, "success");
            // Optionally clear search or show success state
        } catch (e) {
            addToast(`Failed to add playlist: ${e.message}`, "error");
            throw e; // Propagate to modal to keep it open or show specific error
        }
    };

    return (
        <div class="space-y-6">
            <div class="flex gap-2">
                <input
                    type="text"
                    value={query}
                    onInput={(e) => setQuery(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                    placeholder="Search Spotify Playlists..."
                    class="input-field flex-1"
                />
                <button
                    onClick={handleSearch}
                    disabled={loading || !query.trim()}
                    class="btn-primary px-6"
                >
                    {loading ? (
                        <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    ) : "Search"}
                </button>
            </div>

            {error && (
                <div class="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm">
                    {error}
                </div>
            )}

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {results.map(playlist => (
                    <div key={playlist.id} class="card p-4 hover:border-primary/50 transition-colors flex flex-col gap-3 group">
                        <div class="relative aspect-square rounded-lg overflow-hidden bg-surface-alt">
                            {playlist.image ? (
                                <img src={playlist.image} alt={playlist.name} class="w-full h-full object-cover" loading="lazy" />
                            ) : (
                                <div class="w-full h-full flex items-center justify-center text-text-muted">
                                    <svg class="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                                    </svg>
                                </div>
                            )}
                            <button
                                onClick={() => setSelectedPlaylist(playlist)}
                                class="absolute inset-0 bg-black/40 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-all duration-200 flex items-center justify-center"
                            >
                                <span class="btn-primary transform scale-90 group-hover:scale-100 transition-transform">Add to Monitor</span>
                            </button>
                        </div>
                        <div>
                            <h3 class="font-bold text-text truncate">{playlist.name}</h3>
                            <p class="text-sm text-text-muted truncate">by {playlist.owner}</p>
                            <p class="text-xs text-text-muted/50 mt-1">{playlist.track_count} tracks</p>
                        </div>
                    </div>
                ))}
            </div>

            {!loading && results.length === 0 && query && !error && (
                <div class="text-center py-12 text-text-muted">
                    No results found for "{query}"
                </div>
            )}

            {selectedPlaylist && (
                <AddModal
                    playlist={selectedPlaylist}
                    onClose={() => setSelectedPlaylist(null)}
                    onAdd={handleAdd}
                />
            )}
        </div>
    );
}
