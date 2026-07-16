import html2canvas from "html2canvas";
import { useEffect, useRef, useState } from "react";
import ReconnectingWebSocket from "reconnecting-websocket";

import { AdminPanel } from "./components/AdminPanel";
import { CharacterCard } from "./components/CharacterCard";
import { LensingAnimation } from "./components/LensingAnimation";
import { soundManager } from "./components/SoundManager";
import type { CharacterCardData } from "./types/card";

function App() {
    const params = new URLSearchParams(window.location.search);
    const isAdmin = params.get("admin") === "true";
    // 音量設定: ?vol=50 のように指定。デフォルトは0で無効。
    const volumeParam = params.get("vol");
    const soundVolume = volumeParam !== null ? parseInt(volumeParam, 10) / 100 : 0;

    const [currentCard, setCurrentCard] = useState<CharacterCardData | null>(null);
    const [active, setActive] = useState<boolean>(false);
    const socketRef = useRef<ReconnectingWebSocket | null>(null);

    // 魔法陣の演出用のステート
    const [isLensing, setIsLensing] = useState<boolean>(false);
    const [lensingUser, setLensingUser] = useState<string>("");

    const cardContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        soundManager.register("kirakira", "kirakira2.mp3");
        soundManager.register("mad1"    , "magic-attack-darkness1.mp3");
    }, []);

    useEffect(() => {
        soundManager.setVolume(soundVolume);
    }, [soundVolume]);

    useEffect(() => {
        if (active && currentCard && cardContainerRef.current) {
            // 演出のフェードインやアニメーションが落ち着くのを少し待つ
            const timer = setTimeout(async () => {
                await captureAndUploadCard(currentCard.display_name, currentCard.title);
            }, 5000);

            return () => clearTimeout(timer);
        }
    }, [active, currentCard]);

    // 実際の画像化とAPI送信を行う関数
    const captureAndUploadCard = async (displayName: string, title: string) => {
        if (!cardContainerRef.current) return;
        try {
            // DOMをCanvasに変換（高画質化のためにscaleを2に設定）
            const canvas = await html2canvas(cardContainerRef.current, {
                useCORS: true,
                scale: 2,
                backgroundColor: null,
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
                        const animatedContainer = clonedDoc.querySelector(".card-animate-container");
                        if (animatedContainer) {
                            animatedContainer.classList.remove("card-animate-container");
                        }
                    }
                },
            });

            canvas.toBlob(async (blob) => {
                if (!blob) return;
                const formData = new FormData();
                formData.append("file", blob, `${displayName}_card.png`);
                formData.append("user_name", displayName);
                formData.append("rarity", title);

                const response = await fetch("http://localhost:34510/cards/upload", {
                    method: "POST",
                    body: formData,
                });

                if (response.ok) {
                    console.log(`[Success] ${displayName} さんの完成版カードをサーバーに送信しました。`);
                } else {
                    console.error("[Error] カード画像の送信に失敗しました:", response.statusText);
                }
            }, "image/png");
        } catch (error) {
            console.error("[Error] 画像の合成・キャプチャ中に例外が発生しました:", error);
        }
    };

    useEffect(() => {
        const rws = new ReconnectingWebSocket("ws://localhost:34510/ws");
        socketRef.current = rws;

        rws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                // バックエンドから「今からカード作り始めるよ」が来たら魔法陣ON
                if (message.event === "START_GENERATION") {
                    setCurrentCard(null);
                    setActive(false);
                    setLensingUser(message.data?.user_name || "");
                    setIsLensing(true);
                    soundManager.play("mad1");
                }

                // カードが完成したら魔法陣を消してカードをドーン！
                if (message.event === "NEW_CARD") {
                    setIsLensing(false);
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
            }}
        >
            {/* 管理モードの時だけ表示されるコントロールパネル */}
            {isAdmin && <AdminPanel />}

            {/* 錬成中アニメーションの表示位置 */}
            {isLensing && (
                <LensingAnimation userName={lensingUser} />
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
