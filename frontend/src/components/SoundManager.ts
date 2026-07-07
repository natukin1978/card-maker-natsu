// 効果音を一括管理するシンプルなクラス
class SoundManager {
    constructor() {
        this.sounds = {};
        this.volume = 1.0;
    }

    // 音声を登録する（事前にロードしておく）
    register(name, url) {
        this.sounds[name] = new Audio(url);
    }

    // 全体の音量を設定する
    setVolume(val) {
        this.volume = val;
        // 登録済みのすべての音に音量を反映
        Object.values(this.sounds).forEach((audio) => {
            audio.volume = this.volume;
        });
    }

    // 指定した名前の音を再生する
    play(name) {
        if (this.volume <= 0 || !this.sounds[name]) return;

        const audio = this.sounds[name];
        audio.currentTime = 0; // 最初から再生（連打対応）
        audio.play().catch((e) => console.warn(`${name} play blocked:`, e));
    }
}

export const soundManager = new SoundManager();
