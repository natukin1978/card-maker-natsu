import { useEffect, useRef, useState } from "react";
import ReconnectingWebSocket from "reconnecting-websocket";
import html2canvas from "html2canvas";

import { CharacterCard } from "./components/CharacterCard";
import { soundManager } from "./components/SoundManager";
import type { CharacterCardData } from "./types/card";

function App() {
  const params = new URLSearchParams(window.location.search);
  // 音量設定: ?vol=50 のように指定。デフォルトは0で無効。
  const volumeParam = params.get("vol");
  const soundVolume = volumeParam !== null ? parseInt(volumeParam, 10) / 100 : 0;

  const [currentCard, setCurrentCard] = useState<CharacterCardData | null>(null);
  const [active, setActive] = useState<boolean>(false);
  const socketRef = useRef<ReconnectingWebSocket | null>(null);

  const cardContainerRef = useRef<HTMLDivElement>(null);

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
        useCORS: true,        // Twitchのアイコン画像など、外部URLの画像を読み込むために必須
        scale: 2,             // 高画質化（2倍サイズ）
        backgroundColor: null // 背景を透過させる
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
    // ポート 34510 のWebSocketに接続
    const rws = new ReconnectingWebSocket("ws://localhost:34510/ws");
    socketRef.current = rws;

    rws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.event === "NEW_CARD") {
          soundManager.play("kirakira");
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
