import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useDownloadStore = create(
  persist(
    (set, get) => ({
      queue: [],
      downloading: [],
      completed: [],
      failed: [],
      quality: "LOSSLESS",
      maxConcurrent: 3,
      organizationTemplate: "{Artist}/{Album}/{TrackNumber} - {Title}",
      groupCompilations: true,
      runBeets: false,
      embedLyrics: false,

      addToQueue: (tracks) =>
        set((state) => {
          const existingIds = new Set([
            ...state.queue.map((t) => t.tidal_id),
            ...state.downloading.map((t) => t.tidal_id),
            ...state.completed.map((t) => t.tidal_id),
          ]);

          const newTracks = tracks
            .filter((track) => !existingIds.has(track.tidal_id))
            .map((track) => ({
              ...track,
              id: `${track.tidal_id}-${Date.now()}`,
              status: "queued",
              progress: 0,
              addedAt: Date.now(),
            }));

          if (newTracks.length === 0) {
            console.log("All tracks already in queue");
            return state;
          }

          console.log(
            `Adding ${newTracks.length} new tracks to queue (${tracks.length - newTracks.length
            } duplicates skipped)`
          );

          return {
            queue: [...state.queue, ...newTracks],
          };
        }),

      removeFromQueue: (trackId) =>
        set((state) => ({
          queue: state.queue.filter((t) => t.id !== trackId),
        })),

      startDownload: (trackId) =>
        set((state) => {
          const track = state.queue.find((t) => t.id === trackId);
          if (!track) return state;

          return {
            queue: state.queue.filter((t) => t.id !== trackId),
            downloading: [
              ...state.downloading,
              { ...track, status: "downloading", startedAt: Date.now() },
            ],
          };
        }),

      updateProgress: (trackId, progress) =>
        set((state) => ({
          downloading: state.downloading.map((t) =>
            t.id === trackId ? { ...t, progress } : t
          ),
        })),

      completeDownload: (trackId, filename) =>
        set((state) => {
          const track = state.downloading.find((t) => t.id === trackId);
          if (!track) return state;

          return {
            downloading: state.downloading.filter((t) => t.id !== trackId),
            completed: [
              ...state.completed,
              {
                ...track,
                status: "completed",
                progress: 100,
                completedAt: Date.now(),
                filename,
              },
            ],
          };
        }),

      failDownload: (trackId, error) =>
        set((state) => {
          const track = state.downloading.find((t) => t.id === trackId);
          if (!track) return state;

          return {
            downloading: state.downloading.filter((t) => t.id !== trackId),
            failed: [
              ...state.failed,
              {
                ...track,
                status: "failed",
                error,
                failedAt: Date.now(),
              },
            ],
          };
        }),

      retryFailed: (trackId) =>
        set((state) => {
          const track = state.failed.find((t) => t.id === trackId);
          if (!track) return state;

          return {
            failed: state.failed.filter((t) => t.id !== trackId),
            queue: [
              ...state.queue,
              { ...track, status: "queued", error: undefined, progress: 0 },
            ],
          };
        }),

      clearCompleted: () => set({ completed: [] }),

      clearFailed: () => set({ failed: [] }),

      setQuality: (quality) => set({ quality }),
      setOrganizationTemplate: (template) => set({ organizationTemplate: template }),
      setGroupCompilations: (enabled) => set({ groupCompilations: enabled }),
      setRunBeets: (enabled) => set({ runBeets: enabled }),
      setEmbedLyrics: (enabled) => set({ embedLyrics: enabled }),

      getStats: () => {
        const state = get();
        return {
          queued: state.queue.length,
          downloading: state.downloading.length,
          completed: state.completed.length,
          failed: state.failed.length,
          total:
            state.queue.length +
            state.downloading.length +
            state.completed.length +
            state.failed.length,
        };
      },

      // State reconciliation methods for backend sync
      syncDownloadState: (trackId, backendStatus, backendData) =>
        set((state) => {
          const track = state.downloading.find((t) => t.id === trackId);
          if (!track) return state;

          const newState = { ...state };

          if (backendStatus === "completed") {
            // Move from downloading to completed
            newState.downloading = state.downloading.filter(
              (t) => t.id !== trackId
            );
            newState.completed = [
              ...state.completed,
              {
                ...track,
                status: "completed",
                progress: 100,
                completedAt: Date.now(),
                filename: backendData.filename || track.title,
              },
            ];
          } else if (backendStatus === "failed") {
            // Move from downloading to failed
            newState.downloading = state.downloading.filter(
              (t) => t.id !== trackId
            );
            newState.failed = [
              ...state.failed,
              {
                ...track,
                status: "failed",
                error: backendData.error || "Download failed",
                failedAt: Date.now(),
              },
            ];
          } else if (backendStatus === "downloading") {
            // Update progress if available
            if (backendData.progress !== undefined) {
              newState.downloading = state.downloading.map((t) =>
                t.id === trackId ? { ...t, progress: backendData.progress } : t
              );
            }
          }

          return newState;
        }),

      bulkReconcileWithBackend: (backendState) =>
        set((state) => {
          const newState = {
            downloading: [],
            completed: [...state.completed],
            failed: [...state.failed],
          };

          // Process each downloading track
          for (const track of state.downloading) {
            const trackId = String(track.tidal_id || track.id);

            // Check backend status
            if (backendState.completed && backendState.completed[trackId]) {
              // Move to completed
              const backendData = backendState.completed[trackId];
              newState.completed.push({
                ...track,
                status: "completed",
                progress: 100,
                completedAt: Date.now(),
                filename: backendData.filename || track.title,
              });
            } else if (backendState.failed && backendState.failed[trackId]) {
              // Move to failed
              const backendData = backendState.failed[trackId];
              newState.failed.push({
                ...track,
                status: "failed",
                error: backendData.error || "Download failed",
                failedAt: Date.now(),
              });
            } else if (backendState.active && backendState.active[trackId]) {
              // Still downloading - update progress
              const backendData = backendState.active[trackId];
              newState.downloading.push({
                ...track,
                progress: backendData.progress || track.progress || 0,
              });
            } else {
              // Not found on backend - mark as failed
              newState.failed.push({
                ...track,
                status: "failed",
                error: "Download not found on server (may have been lost)",
                failedAt: Date.now(),
              });
            }
          }

          return newState;
        }),
    }),
    {
      name: "troi-download-queue",
      partialize: (state) => ({
        queue: state.queue,
        downloading: state.downloading,
        completed: state.completed,
        failed: state.failed,
        quality: state.quality,
        maxConcurrent: state.maxConcurrent,
        organizationTemplate: state.organizationTemplate,
        groupCompilations: state.groupCompilations,
        runBeets: state.runBeets,
        embedLyrics: state.embedLyrics,
      }),
    }
  )
);
