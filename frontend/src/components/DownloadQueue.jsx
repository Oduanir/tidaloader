import { h } from "preact";
import { useDownloadStore } from "../stores/downloadStore";

export function DownloadQueue() {
  const queue = useDownloadStore((state) => state.queue);
  const downloading = useDownloadStore((state) => state.downloading);
  const completed = useDownloadStore((state) => state.completed);

  const totalInQueue = queue.length + downloading.length;

  return (
    <div class="download-queue">
      <h3>
        Download Queue ({downloading.length} active, {queue.length} pending)
      </h3>

      {downloading.map((track) => (
        <div key={track.id} class="queue-item downloading">
          <span>
            {track.artist} - {track.title}
          </span>
          <div class="progress-bar">
            <div class="progress" style={{ width: `${track.progress}%` }}></div>
          </div>
        </div>
      ))}

      {queue.slice(0, 3).map((track) => (
        <div key={track.id} class="queue-item queued">
          <span>
            {track.artist} - {track.title}
          </span>
          <span class="status">Queued</span>
        </div>
      ))}

      {completed.length > 0 && (
        <div class="completed-summary">✓ {completed.length} completed</div>
      )}
    </div>
  );
}
