import html2canvas from "html2canvas";
import { useEffect, useRef, useState } from "react";
import ReconnectingWebSocket from "reconnecting-websocket";

import { CharacterCard } from "./components/CharacterCard";
import { soundManager } from "./components/SoundManager";
import type { CharacterCardData } from "./types/card";

const BASE_URL = "http://localhost:34510";

function App() {
    const params = new URLSearchParams(window.location.search);
    const isAdmin = params.get("admin") === "true";
    // 音量設定: ?vol=50 のように指定。デフォルトは0で無効。
    const volumeParam = params.get("vol");
    const soundVolume = volumeParam !== null ? parseInt(volumeParam, 10) / 100 : 0;

    // 管理画面用のステートたち
    const [action, setAction] = useState("make_card"); // アクション (make_card / repost)
    const [eventType, setEventType] = useState("raid"); // イベントの種類 (raid / sub / etc...)
    const [targetName, setTargetName] = useState("");

    const [currentCard, setCurrentCard] = useState<CharacterCardData | null>(null);
    const [active, setActive] = useState<boolean>(false);
    const socketRef = useRef<ReconnectingWebSocket | null>(null);

    const cardContainerRef = useRef<HTMLDivElement>(null);

    const handleExecute = async () => {
        if (!targetName) return alert("ユーザー名を入力してください");

        try {
            let url = "";
            if (action === "make_card") {
                // 新規生成
                url = `${BASE_URL}/cards/generate?name=${targetName}&event=${eventType}`;
            } else if (action === "repost") {
                // 過去作再表示
                url = `${BASE_URL}/cards/repost?name=${targetName}`;
            }
            if (url) {
                await fetch(url);
            }
        } catch (error) {
            console.error("カード取得エラー:", error);
        }
    };

    useEffect(() => {
        soundManager.register("kirakira", "kirakira2.mp3");
    }, []);

    useEffect(() => {
        soundManager.setVolume(soundVolume);
    }, [soundVolume]);

    useEffect(() => {
        if (active && currentCard && cardContainerRef.current) {
            // 演出のフェードインやアニメーションが落ち着くのを少し待つ
            const timer = setTimeout(async () => {
                await captureAndUploadCard(currentCard.display_name, currentCard.title);
            }, 2000);

            return () => clearTimeout(timer);
        }
    }, [active, currentCard]);

    // 実際の画像化とAPI送信を行う関数
    const captureAndUploadCard = async (displayName: string, title: string) => {
        if (!cardContainerRef.current) return;

        try {
            // DOMをCanvasに変換（高画質化のためにscaleを2に設定）
            const canvas = await html2canvas(cardContainerRef.current, {
                useCORS: true, // Twitchのアイコン画像など、外部URLの画像を読み込むために必須
                scale: 2, // 高画質化（2倍サイズ）
                backgroundColor: null, // 背景を透過させる
                onclone: (clonedDoc) => {
                    {
                        // グラデーションは不要
                        const holoLayer = clonedDoc.querySelector(".holo-shimmer-layer");
                        if (holoLayer) {
                            holoLayer.remove();
                        }
                    }
                    {
                        // 画像が半透明になってしまい保存画像に悪影響があるので削除する
                        const animatedContainer =
                            clonedDoc.querySelector(".card-animate-container");
                        if (animatedContainer) {
                            animatedContainer.classList.remove("card-animate-container");
                        }
                    }
                },
            });

            // CanvasをBlob（バイナリデータ）に変換
            canvas.toBlob(async (blob) => {
                if (!blob) return;

                const formData = new FormData();
                formData.append("file", blob, `${displayName}_card.png`);
                formData.append("user_name", displayName);
                formData.append("rarity", title);

                // FastAPIの合成画像アップロード用API（ポート34510に合わせて調整しています）
                const response = await fetch("http://localhost:34510/cards/upload", {
                    method: "POST",
                    body: formData,
                });

                if (response.ok) {
                    console.log(
                        `[Success] ${displayName} さんの完成版カードをサーバーに送信しました。`,
                    );
                } else {
                    console.error("[Error] カード画像の送信に失敗しました:", response.statusText);
                }
            }, "image/png");
        } catch (error) {
            console.error("[Error] 画像の合成・キャプチャ中に例外が発生しました:", error);
        }
    };

    useEffect(() => {
        // ポート 34510 のWebSocketに接続
        const rws = new ReconnectingWebSocket("ws://localhost:34510/ws");
        socketRef.current = rws;

        rws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.event === "NEW_CARD") {
                    setCurrentCard(message.data);
                    setTimeout(() => {
                        soundManager.play("kirakira");
                        setActive(true);
                    }, 200);
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
            {/* 管理モードの時だけ表示されるコントロールパネル */}
            {isAdmin && (
                <div
                    style={{
                        position: "fixed",
                        top: "15px",
                        left: "15px",
                        zIndex: 9999,
                        background: "#1a1625", // 少し高級感のあるダーク背景
                        border: "2px solid rgba(170, 59, 255, 0.4)",
                        padding: "15px",
                        borderRadius: "12px",
                        display: "flex",
                        gap: "12px",
                        alignItems: "center",
                        boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
                    }}
                >
                    {/* ① アクション選択 (make_card / repost) */}
                    <select
                        value={action}
                        onChange={(e) => setAction(e.target.value)}
                        style={{
                            padding: "6px 10px",
                            borderRadius: "6px",
                            background: "#2e2a3a",
                            color: "white",
                            border: "1px solid #444",
                        }}
                    >
                        <option value="make_card">🃏 トレカ新規生成 (make_card)</option>
                        <option value="repost">🔄 過去作を再表示 (repost)</option>
                    </select>

                    {/* ② イベントの種類選択 (💡 make_card の時だけ disabled を解除する) */}
                    <select
                        value={eventType}
                        onChange={(e) => setEventType(e.target.value)}
                        disabled={action !== "make_card"} // 👈 ここがポイント！条件に合わないとグレーアウトします
                        style={{
                            padding: "6px 10px",
                            borderRadius: "6px",
                            background: action === "make_card" ? "#2e2a3a" : "#1e1b24",
                            color: action === "make_card" ? "white" : "#666",
                            border: "1px solid #444",
                            cursor: action === "make_card" ? "pointer" : "not-allowed",
                        }}
                    >
                        <option value="raid">⚔️ レイド (Raid)</option>
                        <option value="sub">💎 サブスク (Subscription)</option>
                        <option value="cheer">✨ ビッツ (Cheer)</option>
                        <option value="follow">🔰 フォロー (Follow)</option>
                    </select>

                    {/* ③ ユーザー名入力欄 */}
                    <input
                        type="text"
                        placeholder="対象のユーザー名"
                        value={targetName}
                        onChange={(e) => setTargetName(e.target.value)}
                        style={{
                            padding: "6px 10px",
                            borderRadius: "6px",
                            background: "#2e2a3a",
                            color: "white",
                            border: "1px solid #444",
                            width: "150px",
                        }}
                    />

                    {/* ④ 実行ボタン */}
                    <button
                        type="button"
                        onClick={handleExecute}
                        style={{
                            padding: "6px 14px",
                            borderRadius: "6px",
                            background: "#aa3bff",
                            color: "white",
                            border: "none",
                            fontWeight: "bold",
                            cursor: "pointer",
                        }}
                    >
                        実行！
                    </button>
                </div>
            )}

            {active && currentCard && (
                <div ref={cardContainerRef}>
                    <CharacterCard
                        card={currentCard}
                        onClose={() => {
                            setActive(false);
                            setCurrentCard(null);
                        }}
                    />
                </div>
            )}
        </div>
    );
}

export default App;
