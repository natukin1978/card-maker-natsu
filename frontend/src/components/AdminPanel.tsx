import { useState } from "react";

const BASE_URL = "http://localhost:34510";

export const AdminPanel = () => {
  const [targetName, setTargetName] = useState("");
  const [action, setAction] = useState("make_card");
  const [eventType, setEventType] = useState("raid");
  // 🚀 熱量の数値を管理するステートを追加（デフォルトは1）
  const [eventValue, setEventValue] = useState<number>(1);

  // 💡 選択されたイベントに応じて、入力欄のヒントの単位を切り替える
  const getValuePlaceholder = () => {
    switch (eventType) {
      case "raid": return "レイド人数 (例: 15)";
      case "sub": return "継続月数 (例: 3)";
      case "cheer": return "ビッツ数 (例: 500)";
      default: return "数値・熱量";
    }
  };

  const handleExecute = async () => {
    if (!targetName) return alert("ユーザー名を入力してください");

    try {
      let url = "";
      if (action === "make_card") {
          // 新規生成
          url = `${BASE_URL}/cards/generate?name=${targetName}&event=${eventType}&value=${eventValue}`;
      } else if (action === "repost") {
          // 過去作再表示
          url = `${BASE_URL}/cards/repost?name=${targetName}`;
      }
      if (url) {
          await fetch(url);
      }
    } catch (error) {
      console.error("送信エラー:", error);
    }
  };

  return (
    <div style={{ padding: "20px", background: "#222", color: "#fff", borderRadius: "8px" }}>
      <h2>管理画面</h2>

      {/* ユーザー名入力 */}
      <div style={{ marginBottom: "15px" }}>
        <label>ユーザー名 (Twitch ID):
          <input
            type="text"
            value={targetName}
            onChange={(e) => setTargetName(e.target.value)}
            style={{ padding: "5px", marginLeft: "10px" }}
          />
        </label>
      </div>

      {/* アクション選択 */}
      <div style={{ marginBottom: "15px" }}>
        <label>操作の種類:
          <select value={action} onChange={(e) => setAction(e.target.value)} style={{ padding: "5px", marginLeft: "10px" }}>
            <option value="make_card">🃏 トレカ新規生成 (make_card)</option>
            <option value="repost">🔄 過去作を再表示 (repost)</option>
          </select>
        </label>
      </div>

      {/* 新規生成のときだけ表示するオプション */}
      {action === "make_card" && (
        <div style={{ padding: "10px", background: "#333", borderRadius: "5px", marginBottom: "15px" }}>
          <div style={{ marginBottom: "10px" }}>
            <label>イベント:
              <select value={eventType} onChange={(e) => setEventType(e.target.value)} style={{ padding: "5px", marginLeft: "10px" }}>
                <option value="sub">💎 サブスク (Subscription)</option>
                <option value="cheer">✨ ビッツ (Cheer)</option>
                <option value="raid">⚔️ レイド (Raid)</option>
                <option value="follow">🔰 フォロー (Follow)</option>
              </select>
            </label>
          </div>

          {/* 🚀 【追加】規模・熱量の入力欄（フォロー以外の時に表示、または常に表示） */}
          {eventType !== "follow" && (
            <div>
              <label>熱量・規模:
                <input
                  type="number"
                  min="1"
                  value={eventValue}
                  onChange={(e) => setEventValue(Number(e.target.value))}
                  placeholder={getValuePlaceholder()}
                  style={{ padding: "5px", marginLeft: "10px", width: "150px" }}
                />
              </label>
            </div>
          )}
        </div>
      )}

      <button type="button" onClick={handleExecute} style={{ padding: "10px 20px", background: "#6441a5", color: "#fff", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}>
        実行する
      </button>
    </div>
  );
};
