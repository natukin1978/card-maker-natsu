import { useEffect, useState, useRef } from "react";
import ReconnectingWebSocket from 'reconnecting-websocket';

// バックエンドの CharacterParams に100%完全に一致させた型定義
interface CharacterCard {
  display_name: string;  // Twitchの表示名
  title: string;         // 二つ名
  attribute: string;     // 属性（炎、水など）
  attack_power: number;  // 攻撃力
  defense_power: number; // 防御力
  skill_name: string;    // 必殺技名
  flavor_text: string;   // 説明文
  image_url: string | null;
}

function App() {
  const [currentCard, setCurrentCard] = useState<CharacterCard | null>(null);
  const [active, setActive] = useState<boolean>(false);
  const socketRef = useRef<ReconnectingWebSocket | null>(null);

  useEffect(() => {
    const rws = new ReconnectingWebSocket("ws://localhost:8000/ws");
    socketRef.current = rws;

    rws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.event === "NEW_CARD") {
          console.log("Received new card:", message.data);
          setCurrentCard(message.data);
          setActive(true);
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    return () => {
      rws.close();
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
          backgroundColor: "rgba(0, 0, 0, 0.85)",
          color: "white",
          borderRadius: "15px",
          border: "2px solid #ff007f",
          textAlign: "center",
          maxWidth: "400px",
          boxShadow: "0 0 20px rgba(255, 0, 127, 0.5)"
        }}>
          {/* 二つ名とユーザー表示名 */}
          <p style={{ color: "#cyan", fontSize: "14px", margin: "0 0 5px 0", letterSpacing: "2px" }}>
            【{currentCard.title}】
          </p>
          <h2 style={{ margin: "0 0 15px 0", fontSize: "24px" }}>
            {currentCard.display_name}
          </h2>
          
          {/* 生成されたイラスト */}
          {currentCard.image_url && (
            <img 
              src={currentCard.image_url} 
              alt="Character" 
              style={{ width: "100%", borderRadius: "10px", marginBottom: "15px" }} 
            />
          )}

          {/* 属性・ステータス表示 */}
          <div style={{ 
            display: "flex", 
            justifyContent: "space-between", 
            backgroundColor: "rgba(255,255,255,0.1)", 
            padding: "8px 12px", 
            borderRadius: "8px",
            fontSize: "14px",
            marginBottom: "12px"
          }}>
            <div>属性: <span style={{ color: "#ffeb3b", fontWeight: "bold" }}>{currentCard.attribute}</span></div>
            <div>ATK: <span style={{ color: "#ff5252", fontWeight: "bold" }}>{currentCard.attack_power}</span></div>
            <div>DEF: <span style={{ color: "#4caf50", fontWeight: "bold" }}>{currentCard.defense_power}</span></div>
          </div>

          {/* 必殺技 */}
          <div style={{ textAlign: "left", marginBottom: "12px", fontSize: "14px" }}>
            <div style={{ color: "#e040fb", fontWeight: "bold" }}>必殺技: {currentCard.skill_name}</div>
          </div>

          {/* フレーバーテキスト */}
          <p style={{ 
            fontStyle: "italic", 
            color: "#ccc", 
            fontSize: "13px", 
            lineHeight: "1.5",
            margin: "0",
            textAlign: "left",
            borderTop: "1px solid rgba(255,255,255,0.2)",
            paddingTop: "10px"
          }}>
            {currentCard.flavor_text}
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
