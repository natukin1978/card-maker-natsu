import type React from "react";
import { useEffect, useState } from "react";
import type { CharacterCardData } from "../types/card";
import "./CharacterCard.css";

interface CharacterCardProps {
    card: CharacterCardData;
    onClose: () => void;
}

export const CharacterCard: React.FC<CharacterCardProps> = ({ card, onClose }) => {
    const [isFadingOut, setIsFadingOut] = useState(false);

    useEffect(() => {
        // 1. 経過したらフェードアウトフラグを立てる
        const displayTimer = setTimeout(() => {
            setIsFadingOut(true);
        }, 25000);

        return () => clearTimeout(displayTimer);
    }, []);

    useEffect(() => {
        if (isFadingOut) {
            // 2. フェードアウトアニメーションが完了したら、親側の表示を完全にオフにする
            const fadeTimer = setTimeout(() => {
                onClose();
            }, 500);
            return () => clearTimeout(fadeTimer);
        }
    }, [isFadingOut, onClose]);

    // 属性アイコンの解決
    const getAttributeIcon = (attr: string) => {
        if (!attr) return "about:blank";
        const base = import.meta.env.BASE_URL;
        if (attr.includes("炎") || attr.includes("火")) return `${base}assets/icon_fire.png`;
        if (attr.includes("水")) return `${base}assets/icon_water.png`;
        if (attr.includes("風") || attr.includes("木")) return `${base}assets/icon_wind.png`;
        if (attr.includes("光")) return `${base}assets/icon_light.png`;
        if (attr.includes("闇")) return `${base}assets/icon_dark.png`;
        return `${base}assets/icon_default.png`;
    };

    return (
        <div
            className={`card-animate-container ${isFadingOut ? "fade-out" : ""}`}
            style={{
                width: "380px",
                backgroundColor: "rgba(20, 15, 25, 0.95)",
                color: "white",
                borderRadius: "20px",
                border: "2px solid rgba(255, 0, 127, 0.6)",
                overflow: "hidden",
                position: "relative", // ホログラムレイヤーの基準
            }}
        >
            {/* 🌟 煌めくホログラム加工レイヤー */}
            <div className="holo-shimmer-layer" />

            {/* イラスト & バッジ領域 */}
            <div style={{ position: "relative", width: "100%", aspectRatio: "1 / 1" }}>
                {card.image_url && (
                    <img
                        src={card.image_url ? `${card.image_url}?t=${Date.now()}` : ""}
                        alt="Character"
                        crossOrigin="anonymous"
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    />
                )}

                {/* 右上：SSRバッジ */}
                <img
                    src={`${import.meta.env.BASE_URL}assets/badge_ssr.png`}
                    alt="SSR"
                    style={{
                        position: "absolute",
                        top: "12px",
                        right: "12px",
                        width: "85px",
                        filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.5))",
                    }}
                />

                {/* 左上：属性バッジ */}
                <img
                    src={getAttributeIcon(card.attribute)}
                    alt={card.attribute}
                    style={{
                        position: "absolute",
                        top: "12px",
                        left: "12px",
                        width: "50px",
                        filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.5))",
                    }}
                />

                {/* イラスト下部：二つ名と名前 */}
                <div
                    style={{
                        position: "absolute",
                        bottom: "0",
                        left: "0",
                        width: "100%",
                        background:
                            "linear-gradient(to top, rgba(15,10,20,1) 0%, rgba(15,10,20,0.8) 70%, rgba(15,10,20,0) 100%)",
                        padding: "40px 16px 12px 16px",
                        boxSizing: "border-box",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "flex-start",
                    }}
                >
                    <span
                        style={{
                            color: "#00e5ff",
                            fontSize: "13px",
                            fontWeight: "bold",
                            letterSpacing: "1px",
                            textShadow: "0 1px 4px rgba(0,0,0,0.8)",
                        }}
                    >
                        【{card.title}】
                    </span>
                    <h2
                        style={{
                            margin: "4px 0 0 0",
                            fontSize: "26px",
                            fontWeight: "bold",
                            textShadow: "0 2px 6px rgba(0,0,0,0.9)",
                        }}
                    >
                        {card.display_name}
                    </h2>
                </div>
            </div>

            {/* ステータス & テキスト領域 */}
            <div style={{ padding: "16px" }}>
                {/* ステータスバー */}
                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-around",
                        backgroundColor: "rgba(255,255,255,0.06)",
                        padding: "10px",
                        borderRadius: "10px",
                        fontSize: "15px",
                        marginBottom: "14px",
                        border: "1px solid rgba(255,255,255,0.1)",
                    }}
                >
                    <div>
                        <span style={{ color: "#aaa", fontSize: "12px" }}>ATK</span>{" "}
                        <b className="count-display atk-display">{card.attack_power}</b>
                    </div>
                    <div style={{ width: "1px", backgroundColor: "rgba(255,255,255,0.2)" }}></div>
                    <div>
                        <span style={{ color: "#aaa", fontSize: "12px" }}>DEF</span>{" "}
                        <b className="count-display def-display">{card.defense_power}</b>
                    </div>
                </div>

                {/* 必殺技 */}
                <div
                    style={{
                        backgroundColor: "rgba(224, 64, 251, 0.1)",
                        padding: "8px 12px",
                        borderRadius: "8px",
                        borderLeft: "4px solid #e040fb",
                        marginBottom: "14px",
                        fontSize: "14px",
                    }}
                >
                    <span
                        style={{
                            color: "#e040fb",
                            fontWeight: "bold",
                            display: "block",
                            fontSize: "11px",
                            marginBottom: "2px",
                        }}
                    >
                        SKILL
                    </span>
                    <b style={{ color: "#fff" }}>{card.skill_name}</b>
                </div>

                {/* フレーバーテキスト */}
                <p
                    style={{
                        color: "#ddd",
                        fontSize: "13px",
                        lineHeight: "1.6",
                        margin: "0",
                        paddingTop: "4px",
                        textAlign: "left",
                    }}
                >
                    {card.flavor_text}
                </p>
            </div>
        </div>
    );
};
