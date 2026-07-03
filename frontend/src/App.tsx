import { useEffect, useRef, useState } from "react";
import ReconnectingWebSocket from "reconnecting-websocket";
import { CharacterCard } from "./components/CharacterCard";
import { soundManager } from "./SoundManager";
import type { CharacterCardData } from "./types/card";

function App() {
  const params = new URLSearchParams(window.location.search);
  // 音量設定: ?vol=50 のように指定。デフォルトは0で無効。
  const volumeParam = params.get("vol");
  const soundVolume = volumeParam !== null ? parseInt(volumeParam, 10) / 100 : 0;

  const [currentCard, setCurrentCard] = useState<CharacterCardData | null>(null);
  const [active, setActive] = useState<boolean>(false);
  const socketRef = useRef<ReconnectingWebSocket | null>(null);

  useEffect(() => {
    soundManager.register("kirakira", "kirakira.mp3");
  }, []);

  // 音量の初期設定
  useEffect(() => {
    soundManager.setVolume(soundVolume);
  }, [soundVolume]);

  useEffect(() => {
    // ポート 34510 のWebSocketに接続
    const rws = new ReconnectingWebSocket("ws://localhost:34510/ws");
    socketRef.current = rws;

    rws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.event === "NEW_CARD") {
          setCurrentCard(message.data);
          setActive(true);

          soundManager.play("kirakira");
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    return () => rws.close();
  }, []);

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        backgroundColor: "transparent",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        overflow: "hidden",
        fontFamily: "'Helvetica Neue', Arial, sans-serif",
      }}
    >
      {active && currentCard && (
        <CharacterCard
          card={currentCard}
          onClose={() => {
            // 10秒後のフェードアウトが終わったらここが呼ばれ、完全に消去される
            setActive(false);
            setCurrentCard(null);
          }}
        />
      )}
    </div>
  );
}

export default App;
