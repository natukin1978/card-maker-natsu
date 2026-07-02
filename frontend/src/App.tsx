import { useEffect, useState } from "react";

// バックエンド（CharacterParams）に合わせた型定義
interface CharacterCard {
  display_name: string;
  name: string;
  element: string;
  rarity: string;
  role: string;
  flavor_text: string;
  status: {
    HP: number;
    ATK: number;
    DEF: number;
  };
  skills: Array<{
    name: string;
    description: string;
  }>;
  image_url: string | null;
}

function App() {
  const [currentCard, setCurrentCard] = useState<CharacterCard | null>(null);
  const [active, setActive] = useState<boolean>(false);

  useEffect(() => {
    // WebSocket の接続 (FastAPIサーバーを指定)
    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onopen = () => {
      console.log("Connected to Backend WebSocket");
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.event === "NEW_CARD") {
          console.log("Received new card:", message.data);
          // 新しいカードデータをセット
          setCurrentCard(message.data);
          // 演出をアクティブにする
          setActive(true);

          // テスト用に10秒後に自動で閉じる演出（必要に応じて調整）
          // setTimeout(() => setActive(false), 10000);
        }
      } catch (error) {
        console.error("Failed to parse WS message:", error);
      }
    };

    ws.onclose = () => {
      console.log("Disconnected from Backend WebSocket");
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div style={{
      width: "100vw",
      height: "100vh",
      backgroundColor: "transparent", // OBS透過用
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      overflow: "hidden",
      fontFamily: "sans-serif"
    }}>
      {active && currentCard && (
        <div style={{
          padding: "20px",
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          color: "white",
          borderRadius: "15px",
          border: "2px solid #ff007f",
          textAlign: "center",
          maxWidth: "400px"
        }}>
          <h2>{currentCard.rarity} {currentCard.display_name}</h2>
          <h3>【{currentCard.name}】</h3>
          
          {currentCard.image_url && (
            <img 
              src={currentCard.image_url} 
              alt="Character" 
              style={{ width: "100%", borderRadius: "10px", marginBottom: "15px" }} 
            />
          )}

          <p style={{ fontStyle: "italic", color: "#ccc" }}>{currentCard.flavor_text}</p>
          <div style={{ display: "flex", justifyContent: "space-around", marginTop: "10px" }}>
            <div>HP: {currentCard.status.HP}</div>
            <div>ATK: {currentCard.status.ATK}</div>
            <div>DEF: {currentCard.status.DEF}</div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
