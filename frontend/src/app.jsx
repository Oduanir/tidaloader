import { h } from "preact";
import { useState } from "preact/hooks";
import { SearchBar } from "./components/SearchBar";
import { TroiGenerator } from "./components/TroiGenerator";
import { DownloadQueue } from "./components/DownloadQueue";

export function App() {
  const [activeTab, setActiveTab] = useState("troi"); // 'troi' or 'search'

  return (
    <div class="app">
      <header class="header">
        <h1>🎵 Troi Tidal Downloader</h1>
        <button class="settings-btn">⚙️ Settings</button>
      </header>

      <nav class="tabs">
        <button
          class={`tab ${activeTab === "troi" ? "active" : ""}`}
          onClick={() => setActiveTab("troi")}
        >
          Troi Playlist
        </button>
        <button
          class={`tab ${activeTab === "search" ? "active" : ""}`}
          onClick={() => setActiveTab("search")}
        >
          Custom Search
        </button>
      </nav>

      <main class="content">
        {activeTab === "troi" && <TroiGenerator />}
        {activeTab === "search" && <SearchBar />}
      </main>

      <footer class="queue-section">
        <DownloadQueue />
      </footer>
    </div>
  );
}
