import { useEffect, useState, useRef } from "react";
import ReconnectingWebSocket from 'reconnecting-websocket';

interface CharacterCard {
  display_name: string;
  title: string;
  attribute: string;
  attack_power: number;
  defense_power: number;
  skill_name: string;
  flavor_text: string;
  image_url: string | null;
}

function App() {
  const [currentCard, setCurrentCard] = useState<CharacterCard | null>(null);
  const [active, setActive] = useState<boolean>(false);
  const socketRef = useRef<ReconnectingWebSocket | null>(null);

  useEffect(() => {
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

  // 属性名に応じて、用意したアイコン画像のパスを切り替える関数
  const getAttributeIcon = (attr: string) => {
    // 実際に対応する画像を frontend/public/assets/ などの配下に置くと読み込めます
    if (attr.includes("炎") || attr.includes("火")) return "/assets/icon_fire.png";
    if (attr.includes("水")) return "/assets/icon_water.png";
    if (attr.includes("風") || attr.includes("木")) return "/assets/icon_wind.png";
    if (attr.includes("光")) return "/assets/icon_light.png";
    if (attr.includes("闇")) return "/assets/icon_dark.png";
    return "/assets/icon_default.png"; // フォールバック
  };

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
        <div style={{
          width: "380px",
          backgroundColor: "rgba(20, 15, 25, 0.95)", // 少し高級感のある紫黒
          color: "white",
          borderRadius: "20px",
          border: "2px solid rgba(255, 0, 127, 0.6)",
          boxShadow: "0 0 30px rgba(255, 0, 127, 0.3), inset 0 0 15px rgba(255, 255, 255, 0.05)",
          overflow: "hidden",
        }}>
          
          {/* ==================== 1. イラスト & バッジ領域 ==================== */}
          <div style={{ position: "relative", width: "100%", aspectRatio: "1 / 1" }}>
            
            {/* 生成されたメインイラスト */}
            {currentCard.image_url && (
              <img 
                src={currentCard.image_url} 
                alt="Character" 
                style={{ width: "100%", height: "100%", objectFit: "cover" }} 
              />
            )}

            {/* [右上] レアリティバッジ (画像) */}
            <img 
              src="/assets/badge_ssr.png" 
              alt="SSR" 
              style={{
                position: "absolute",
                top: "12px",
                right: "12px",
                width: "85px", // サイズは適宜調整してください
                filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.5))"
              }}
              // まだ画像が無いときのための文字フォールバック（デバッグ用）
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />

            {/* [左上] 属性バッジ (画像) */}
            <img 
              src={getAttributeIcon(currentCard.attribute)} 
              alt={currentCard.attribute} 
              style={{
                position: "absolute",
                top: "12px",
                left: "12px",
                width: "50px",
                filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.5))"
              }}
              onError={(e) => { e.currentTarget.style.display = "none"; }}
            />

            {/* [イラスト下部] 二つ名と名前をグラデーション帯で重ねる */}
            <div style={{
              position: "absolute",
              bottom: "0",
              left: "0",
              width: "100%",
              background: "linear-gradient(to top, rgba(15,10,20,1) 0%, rgba(15,10,20,0.8) 70%, rgba(15,10,20,0) 100%)",
              padding: "40px 16px 12px 16px",
              boxSizing: "border-box",
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start"
            }}>
              <span style={{ color: "#00e5ff", fontSize: "13px", fontWeight: "bold", letterSpacing: "1px", textShadow: "0 1px 4px rgba(0,0,0,0.8)" }}>
                【{currentCard.title}】
              </span>
              <h2 style={{ margin: "4px 0 0 0", fontSize: "26px", fontWeight: "bold", textShadow: "0 2px 6px rgba(0,0,0,0.9)" }}>
                {currentCard.display_name}
              </h2>
            </div>
          </div>

          {/* ==================== 2. ステータス & テキスト領域 ==================== */}
          <div style={{ padding: "16px" }}>
            
            {/* ステータスバー */}
            <div style={{ 
              display: "flex", 
              justifyContent: "space-around", 
              backgroundColor: "rgba(255,255,255,0.06)", 
              padding: "10px", 
              borderRadius: "10px",
              fontSize: "15px",
              marginBottom: "14px",
              border: "1px solid rgba(255,255,255,0.1)"
            }}>
              <div><span style={{ color: "#aaa", fontSize: "12px" }}>ATK</span> <b style={{ color: "#ff5252", fontSize: "18px" }}>{currentCard.attack_power}</b></div>
              <div style={{ width: "1px", backgroundColor: "rgba(255,255,255,0.2)" }}></div>
              <div><span style={{ color: "#aaa", fontSize: "12px" }}>DEF</span> <b style={{ color: "#4caf50", fontSize: "18px" }}>{currentCard.defense_power}</b></div>
            </div>

            {/* 必殺技 */}
            <div style={{ 
              backgroundColor: "rgba(224, 64, 251, 0.1)", 
              padding: "8px 12px", 
              borderRadius: "8px", 
              borderLeft: "4px solid #e040fb",
              marginBottom: "14px",
              fontSize: "14px"
            }}>
              <span style={{ color: "#e040fb", fontWeight: "bold", display: "block", fontSize: "11px", marginBottom: "2px" }}>SKILL</span>
              <b style={{ color: "#fff" }}>{currentCard.skill_name}</b>
            </div>

            {/* フレーバーテキスト */}
            <p style={{ 
              color: "#ddd", 
              fontSize: "13px", 
              lineHeight: "1.6",
              margin: "0",
              paddingTop: "4px",
              textAlign: "left"
            }}>
              {currentCard.flavor_text}
            </p>
          </div>

        </div>
      )}
    </div>
  );
}

export default App;
