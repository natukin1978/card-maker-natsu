import { useEffect, useState, useRef } from "react";
import ReconnectingWebSocket from 'reconnecting-websocket';
import type { CharacterCardData } from "./types/card";
import { CharacterCard } from "./components/CharacterCard";

function App() {
  const [currentCard, setCurrentCard] = useState<CharacterCardData | null>(null);
  const [active, setActive] = useState<boolean>(false);
  const socketRef = useRef<ReconnectingWebSocket | null>(null);

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
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    return () => rws.close();
  }, []);

  return (
    <div style={{
      width: "100vw",
      height: "100vh",
      backgroundColor: "transparent",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      overflow: "hidden",
      fontFamily: "'Helvetica Neue', Arial, sans-serif",
    }}>
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
