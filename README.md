# 静默之塔 · The Silent Spire

一个纪念碑谷风格的等距小游戏：转动石桥，带旅人走过一条只在视角里成立的路，抵达塔顶。

**在线试玩：** https://wywwywwywwywwyw.github.io/silent-spire/

## 玩法

- 轻点石板，旅人会自己找路走过去
- 拖动或轻点桥中央的转轮，石桥旋转 90°（电脑上也可以按 R）
- 站在桥上转动时，她会随桥一起转

## 技术

单个 `index.html`，用 [three.js](https://threejs.org/) r128 的正交相机画等距视角，音效由 Web Audio 实时合成，不需要构建。
