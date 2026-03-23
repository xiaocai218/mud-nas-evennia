# H5 Frontend Scaffold

当前目录提供第一版 H5 前端骨架，目标是先把布局、组件和视觉规范固定下来，再逐步接后端接口。

## 技术栈

- Vue 3
- Vite
- TypeScript

## 当前内容

- 顶部资源栏
- 底部五栏导航
- 地图页
- 房间页
- 更多页
- NPC / 玩家详情弹窗
- 世界入口弹窗

当前使用的是本地 mock 数据，不依赖后端联调。

## 启动

```powershell
cd C:\Users\CZH\Documents\Playground\mud-nas-evennia\frontend\h5
npm install
npm run dev
```

## 当前原则

1. 先固定 UI 骨架和组件语言。
2. 再逐步把页面接到 `/api/h5/*`。
3. 在 WebSocket 完成前，优先用静态数据和 HTTP 数据驱动页面。

