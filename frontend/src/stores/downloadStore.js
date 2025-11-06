import { create } from "zustand";

/**
 * Download queue store using Zustand
 */
export const useDownloadStore = create((set) => ({
  // Queue state
  queue: [],
  downloading: [],
  completed: [],
  failed: [],

  // Settings
  quality: "LOSSLESS",
  maxConcurrent: 3,

  // Actions
  addToQueue: (tracks) =>
    set((state) => ({
      queue: [
        ...state.queue,
        ...tracks.map((track) => ({
          ...track,
          id: `${track.tidal_id}-${Date.now()}`,
          status: "queued",
          progress: 0,
        })),
      ],
    })),

  startDownload: (trackId) =>
    set((state) => {
      const track = state.queue.find((t) => t.id === trackId);
      if (!track) return state;

      return {
        queue: state.queue.filter((t) => t.id !== trackId),
        downloading: [
          ...state.downloading,
          { ...track, status: "downloading" },
        ],
      };
    }),

  updateProgress: (trackId, progress) =>
    set((state) => ({
      downloading: state.downloading.map((t) =>
        t.id === trackId ? { ...t, progress } : t
      ),
    })),

  completeDownload: (trackId) =>
    set((state) => {
      const track = state.downloading.find((t) => t.id === trackId);
      if (!track) return state;

      return {
        downloading: state.downloading.filter((t) => t.id !== trackId),
        completed: [
          ...state.completed,
          { ...track, status: "completed", progress: 100 },
        ],
      };
    }),

  failDownload: (trackId, error) =>
    set((state) => {
      const track = state.downloading.find((t) => t.id === trackId);
      if (!track) return state;

      return {
        downloading: state.downloading.filter((t) => t.id !== trackId),
        failed: [...state.failed, { ...track, status: "failed", error }],
      };
    }),

  clearCompleted: () => set({ completed: [] }),

  setQuality: (quality) => set({ quality }),
}));
