import { h } from "preact";
import { useState, useEffect } from "preact/hooks";
import { api } from "../../api/client";
import { useToastStore } from "../../stores/toastStore";

export function MonitoredPlaylists() {
    const [playlists, setPlaylists] = useState([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(new Set()); // Set of UUIDs
    const addToast = useToastStore((state) => state.addToast);

    const fetchPlaylists = async () => {
        try {
            const all = await api.getMonitoredPlaylists();
            // Filter strictly for source='spotify'
            // Assuming the API returns a list of objects exactly as stored in JSON
            const spotifyOnly = all.filter(p => p.source === 'spotify');
            setPlaylists(spotifyOnly);
        } catch (e) {
            console.error(e);
            addToast("Failed to load playlists", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPlaylists();
    }, []);

    const handleSync = async (uuid, name) => {
        if (syncing.has(uuid)) return;

        setSyncing(prev => new Set(prev).add(uuid));
        addToast(`Sync started for "${name}"`, "info");

        try {
            const result = await api.syncPlaylist(uuid);
            // Result format depends on backend return. 
            // Usually returns { status: "success", total: X, queued: Y, ... }
            if (result.status === "success" || result.queued !== undefined) {
                addToast(`Sync complete: ${result.queued} new tracks queued`, "success");
            } else {
                addToast(`Sync finished`, "success");
            }
            // Refresh list to update 'last_sync' if API returns updated list or we re-fetch
            fetchPlaylists();
        } catch (e) {
            addToast(`Sync failed: ${e.message}`, "error");
        } finally {
            setSyncing(prev => {
                const next = new Set(prev);
                next.delete(uuid);
                return next;
            });
        }
    };

    const handleDelete = async (uuid, name) => {
        if (!confirm(`Stop monitoring "${name}"? This won't delete downloaded files.`)) return;

        try {
            await api.removeMonitoredPlaylist(uuid);
            addToast(`Stopped monitoring "${name}"`, "success");
            setPlaylists(prev => prev.filter(p => p.uuid !== uuid));
        } catch (e) {
            addToast(`Failed to delete: ${e.message}`, "error");
        }
    };

    if (loading) {
        return (
            <div class="flex items-center justify-center h-64 text-text-muted">
                <svg class="animate-spin h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            </div>
        );
    }

    if (playlists.length === 0) {
        return (
            <div class="flex flex-col items-center justify-center h-64 text-text-muted">
                <svg class="w-16 h-16 mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
                <p>No Spotify playlists found.</p>
                <p class="text-sm mt-2">Use the "Search & Add" tab to start monitoring one.</p>
            </div>
        );
    }

    return (
        <div class="grid grid-cols-1 gap-4">
            {playlists.map(playlist => (
                <div key={playlist.uuid} class="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div class="flex items-start gap-4">
                        <div class="w-12 h-12 rounded bg-surface-alt flex items-center justify-center text-primary font-bold text-xl flex-shrink-0">
                            {playlist.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <h3 class="font-bold text-text text-lg">{playlist.name}</h3>
                            <div class="flex flex-wrap gap-2 mt-1">
                                <span class="badge bg-primary/10 text-primary border-primary/20">
                                    {playlist.frequency.charAt(0).toUpperCase() + playlist.frequency.slice(1)}
                                </span>
                                <span class="badge bg-surface-alt text-text-muted border-border">
                                    {playlist.quality}
                                </span>
                                {playlist.last_sync && (
                                    <span class="text-xs text-text-muted flex items-center h-5">
                                        Last sync: {new Date(playlist.last_sync).toLocaleDateString()}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    <div class="flex items-center gap-2 self-end sm:self-center">
                        <button
                            onClick={() => handleSync(playlist.uuid, playlist.name)}
                            disabled={syncing.has(playlist.uuid)}
                            class="btn-ghost text-primary hover:bg-primary/10"
                            title="Force Sync Now"
                        >
                            {syncing.has(playlist.uuid) ? (
                                <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            ) : (
                                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                            )}
                        </button>

                        <div class="h-8 w-px bg-border mx-1"></div>

                        <button
                            onClick={() => handleDelete(playlist.uuid, playlist.name)}
                            class="btn-ghost text-red-500 hover:bg-red-500/10 hover:text-red-600"
                            title="Stop Monitoring"
                        >
                            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
}
