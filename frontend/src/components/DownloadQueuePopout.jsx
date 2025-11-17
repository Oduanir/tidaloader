import { h } from "preact";
import { useState, useEffect, useRef } from "preact/hooks";
import { useDownloadStore } from "../stores/downloadStore";
import { startDownloads } from "../utils/downloadManager";

export function DownloadQueuePopout() {
  const [isOpen, setIsOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [showCompleted, setShowCompleted] = useState(false);
  const [showHoverTray, setShowHoverTray] = useState(false);
  const hoverTimeoutRef = useRef(null);

  const queue = useDownloadStore((state) => state.queue);
  const downloading = useDownloadStore((state) => state.downloading);
  const completed = useDownloadStore((state) => state.completed);
  const failed = useDownloadStore((state) => state.failed);
  const removeFromQueue = useDownloadStore((state) => state.removeFromQueue);
  const retryFailed = useDownloadStore((state) => state.retryFailed);
  const clearCompleted = useDownloadStore((state) => state.clearCompleted);
  const clearFailed = useDownloadStore((state) => state.clearFailed);

  const totalInQueue = queue.length + downloading.length;
  const totalActivity = totalInQueue + completed.length + failed.length;
  const currentDownload = downloading[0];
  const currentProgress = currentDownload?.progress || 0;

  useEffect(() => {
    setIsRunning(downloading.length > 0);
  }, [downloading.length]);

  const handleStart = async () => {
    try {
      await startDownloads();
      setIsRunning(true);
    } catch (error) {
      console.error("Failed to start downloads:", error);
    }
  };

  const handleStop = () => {
    setIsRunning(false);
  };

  const handleToggleDownloads = () => {
    if (isRunning) {
      handleStop();
    } else {
      handleStart();
    }
  };

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      setIsOpen(false);
      setIsClosing(false);
    }, 300);
  };

  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    hoverTimeoutRef.current = setTimeout(() => {
      setShowHoverTray(true);
    }, 300);
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    setShowHoverTray(false);
  };

  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

  if (totalActivity === 0) return null;

  return (
    <>
      <div
        class="fixed bottom-4 right-4 z-40"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {showHoverTray && !isOpen && (
          <div class="absolute bottom-full right-0 mb-2 bg-surface border border-border-light rounded-lg shadow-lg p-3 min-w-[200px] max-w-[280px] sm:min-w-[250px] animate-slide-in-tray">
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-text-muted">
                  In Queue
                </span>
                <span class="text-sm font-bold text-primary">
                  {totalInQueue}
                </span>
              </div>
              {completed.length > 0 && (
                <div class="flex items-center justify-between">
                  <span class="text-xs font-medium text-text-muted">
                    Completed
                  </span>
                  <span class="text-sm font-bold text-primary">
                    {completed.length}
                  </span>
                </div>
              )}
              {failed.length > 0 && (
                <div class="flex items-center justify-between">
                  <span class="text-xs font-medium text-text-muted">
                    Failed
                  </span>
                  <span class="text-sm font-bold text-red-500">
                    {failed.length}
                  </span>
                </div>
              )}
              {currentDownload && (
                <div class="pt-2 border-t border-border-light">
                  <div class="text-xs text-text-muted mb-1 truncate">
                    Downloading: {currentDownload.title}
                  </div>
                  <div class="w-full bg-background-alt rounded-full h-1.5">
                    <div
                      class="bg-primary h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${currentProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <button
          onClick={() => setIsOpen(!isOpen)}
          class="w-12 h-12 sm:w-14 sm:h-14 bg-primary hover:bg-primary-dark text-white rounded-full shadow-lg flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95"
        >
          <div class="relative">
            <svg
              class="w-6 h-6 sm:w-7 sm:h-7"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
              />
            </svg>
            {totalActivity > 0 && (
              <span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                {totalActivity > 99 ? "99+" : totalActivity}
              </span>
            )}
          </div>
        </button>
      </div>

      {isOpen && (
        <div class="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div
            class={`bg-surface border-t sm:border border-border-light sm:rounded-2xl shadow-2xl w-full sm:w-[90vw] sm:max-w-2xl max-h-[85vh] sm:max-h-[80vh] flex flex-col ${
              isClosing ? "animate-popout-close" : "animate-popout-open"
            }`}
          >
            <div class="flex items-center justify-between p-4 sm:p-6 border-b border-border-light bg-gradient-to-r from-primary/5 to-transparent">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                  <svg
                    class="w-6 h-6 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
                    />
                  </svg>
                </div>
                <div>
                  <h2 class="text-lg sm:text-xl font-bold text-text">
                    Download Queue
                  </h2>
                  <p class="text-xs sm:text-sm text-text-muted">
                    {totalInQueue} in queue · {completed.length} completed ·{" "}
                    {failed.length} failed
                  </p>
                </div>
              </div>
              <button
                onClick={handleClose}
                class="text-text-muted hover:text-text transition-colors p-2 hover:bg-background-alt rounded-lg"
              >
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div class="flex-1 overflow-y-auto custom-scrollbar">
              {currentDownload && (
                <div class="p-4 sm:p-6 bg-primary/5 border-b border-primary/20">
                  <div class="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                    {currentDownload.cover && (
                      <img
                        src={currentDownload.cover}
                        alt={currentDownload.title}
                        class="w-16 h-16 sm:w-20 sm:h-20 rounded-lg object-cover shadow-md flex-shrink-0"
                      />
                    )}
                    <div class="flex-1 min-w-0">
                      <p class="font-semibold text-text mb-1 truncate">
                        {currentDownload.title}
                      </p>
                      <p class="text-sm text-text-muted mb-2 truncate">
                        {currentDownload.artist}
                      </p>
                      <div class="flex items-center gap-2">
                        <div class="flex-1 bg-background-alt rounded-full h-2">
                          <div
                            class="bg-primary h-2 rounded-full transition-all duration-300"
                            style={{ width: `${currentProgress}%` }}
                          />
                        </div>
                        <span class="text-sm font-medium text-primary whitespace-nowrap">
                          {currentProgress}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div class="p-4 sm:p-6 space-y-4">
                <div class="flex flex-col sm:flex-row gap-3">
                  <button
                    onClick={handleToggleDownloads}
                    disabled={totalInQueue === 0}
                    class={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all duration-200 ${
                      isRunning
                        ? "bg-secondary hover:bg-secondary-dark text-white"
                        : "btn-primary"
                    }`}
                  >
                    {isRunning ? (
                      <>
                        <svg
                          class="w-5 h-5"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                        </svg>
                        <span class="hidden sm:inline">Pause Downloads</span>
                        <span class="sm:hidden">Pause</span>
                      </>
                    ) : (
                      <>
                        <svg
                          class="w-5 h-5"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path d="M8 5v14l11-7z" />
                        </svg>
                        <span class="hidden sm:inline">Start Downloads</span>
                        <span class="sm:hidden">Start</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setShowCompleted(!showCompleted)}
                    class="flex-1 sm:flex-initial btn-surface flex items-center justify-center gap-2 px-4 py-3"
                  >
                    <svg
                      class={`w-5 h-5 transition-transform ${
                        showCompleted ? "rotate-180" : ""
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                    <span class="hidden sm:inline">
                      {showCompleted ? "Hide" : "Show"} History
                    </span>
                    <span class="sm:hidden">History</span>
                  </button>
                </div>

                {queue.length > 0 && (
                  <div>
                    <h3 class="text-sm font-semibold text-text-muted mb-3 flex items-center gap-2">
                      <svg
                        class="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      Queued ({queue.length})
                    </h3>
                    <div class="space-y-2">
                      {queue.map((item) => (
                        <div
                          key={item.id}
                          class="flex items-center gap-3 p-3 bg-surface-alt rounded-lg border border-border-light hover:border-primary/30 transition-all group"
                        >
                          {item.cover && (
                            <img
                              src={item.cover}
                              alt={item.title}
                              class="w-12 h-12 rounded-md object-cover flex-shrink-0"
                            />
                          )}
                          <div class="flex-1 min-w-0">
                            <p class="font-medium text-text text-sm truncate">
                              {item.title}
                            </p>
                            <p class="text-xs text-text-muted truncate">
                              {item.artist}
                            </p>
                          </div>
                          <button
                            onClick={() => removeFromQueue(item.id)}
                            class="opacity-0 group-hover:opacity-100 text-text-muted hover:text-red-500 transition-all p-2 hover:bg-red-50 rounded-lg flex-shrink-0"
                          >
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
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                              />
                            </svg>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {showCompleted && (
                  <>
                    {completed.length > 0 && (
                      <div>
                        <div class="flex items-center justify-between mb-3">
                          <h3 class="text-sm font-semibold text-text-muted flex items-center gap-2">
                            <svg
                              class="w-4 h-4 text-primary"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path
                                fill-rule="evenodd"
                                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                                clip-rule="evenodd"
                              />
                            </svg>
                            Completed ({completed.length})
                          </h3>
                          <button
                            onClick={clearCompleted}
                            class="text-xs text-text-muted hover:text-primary transition-colors"
                          >
                            Clear All
                          </button>
                        </div>
                        <div class="space-y-2">
                          {completed.map((item) => (
                            <div
                              key={item.id}
                              class="flex items-center gap-3 p-3 bg-primary/5 rounded-lg border border-primary/20"
                            >
                              {item.cover && (
                                <img
                                  src={item.cover}
                                  alt={item.title}
                                  class="w-12 h-12 rounded-md object-cover flex-shrink-0"
                                />
                              )}
                              <div class="flex-1 min-w-0">
                                <p class="font-medium text-text text-sm truncate">
                                  {item.title}
                                </p>
                                <p class="text-xs text-text-muted truncate">
                                  {item.artist}
                                </p>
                              </div>
                              <svg
                                class="w-5 h-5 text-primary flex-shrink-0"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fill-rule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clip-rule="evenodd"
                                />
                              </svg>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {failed.length > 0 && (
                      <div>
                        <div class="flex items-center justify-between mb-3">
                          <h3 class="text-sm font-semibold text-text-muted flex items-center gap-2">
                            <svg
                              class="w-4 h-4 text-red-500"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path
                                fill-rule="evenodd"
                                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                                clip-rule="evenodd"
                              />
                            </svg>
                            Failed ({failed.length})
                          </h3>
                          <button
                            onClick={clearFailed}
                            class="text-xs text-text-muted hover:text-primary transition-colors"
                          >
                            Clear All
                          </button>
                        </div>
                        <div class="space-y-2">
                          {failed.map((item) => (
                            <div
                              key={item.id}
                              class="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-200"
                            >
                              {item.cover && (
                                <img
                                  src={item.cover}
                                  alt={item.title}
                                  class="w-12 h-12 rounded-md object-cover flex-shrink-0"
                                />
                              )}
                              <div class="flex-1 min-w-0">
                                <p class="font-medium text-text text-sm truncate">
                                  {item.title}
                                </p>
                                <p class="text-xs text-red-600 truncate">
                                  {item.error || "Download failed"}
                                </p>
                              </div>
                              <button
                                onClick={() => retryFailed(item.id)}
                                class="text-primary hover:text-primary-dark transition-colors p-2 hover:bg-primary/10 rounded-lg flex-shrink-0"
                              >
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
                                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                                  />
                                </svg>
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {queue.length === 0 &&
                  downloading.length === 0 &&
                  (!showCompleted ||
                    (completed.length === 0 && failed.length === 0)) && (
                    <div class="text-center py-12">
                      <svg
                        class="w-16 h-16 mx-auto text-text-muted/30 mb-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                        />
                      </svg>
                      <p class="text-text-muted">
                        No items in queue
                      </p>
                    </div>
                  )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}