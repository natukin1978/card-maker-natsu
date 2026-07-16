import React from "react";

interface LensingAnimationProps {
  userName: string;
}

export const LensingAnimation: React.FC<LensingAnimationProps> = ({ userName }) => {
  return (
    <div className="lensing-container">
      {/* コンポーネント固有のドラマチックアニメーションCSS */}
      <style>{`
        @keyframes magic-rotate {
          0% { transform: scale(0.8) rotate(0deg); opacity: 0; }
          10% { transform: scale(1) rotate(36deg); opacity: 0.9; }
          100% { transform: scale(1) rotate(360deg); opacity: 0.9; }
        }
        @keyframes aura-pulse {
          0%, 100% { transform: scale(0.9); opacity: 0.4; filter: blur(25px); }
          50% { transform: scale(1.15); opacity: 0.7; filter: blur(35px); }
        }
        @keyframes text-glow {
          0%, 100% { opacity: 0.6; text-shadow: 0 0 10px #6441a5; }
          50% { opacity: 1; text-shadow: 0 0 25px #a970ff, 0 0 10px #6441a5; }
        }
        .lensing-container {
          position: relative;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          width: 500px;
          height: 500px;
        }
        .magic-aura {
          position: absolute;
          width: 85%;
          height: 85%;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(169,112,255,0.6) 0%, rgba(100,65,165,0.2) 50%, rgba(0,0,0,0) 70%);
          animation: aura-pulse 3s ease-in-out infinite;
        }
        @keyframes magic-fade-in {
          0% { transform: scale(0.5); opacity: 0; }
          100% { transform: scale(1); opacity: 0.9; }
        }
        @keyframes magic-rotate {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .magic-circle-img {
          position: absolute;
          width: 100%;
          height: 100%;
          animation:
            magic-fade-in 1s ease-out forwards,
            magic-rotate 12s linear infinite;
          filter: drop-shadow(0 0 20px #6441a5);
        }
        .lensing-text {
          position: absolute;
          bottom: -40px;
          color: #fff;
          font-family: 'Arial Black', sans-serif;
          font-size: 20px;
          letter-spacing: 2px;
          animation: text-glow 2s ease-in-out infinite;
          text-align: center;
          white-space: nowrap;
        }
      `}</style>

      {/* 怪光オーラ */}
      <div className="magic-aura" />

      {/* 魔法陣（透過処理した画像をセットしてください） */}
      <img
        src={`${import.meta.env.BASE_URL}assets/magic_circle.png`}
        className="magic-circle-img"
        alt="Lensing Magic Circle"
      />

      {/* 演出用のテキスト表示 */}
      <div className="lensing-text">
        {userName ? `${userName.toUpperCase()} CARD LENSING...` : "CARD LENSING..."}
      </div>
    </div>
  );
};
