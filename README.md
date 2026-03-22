# NAS Docker MUD Starter

这是一个适合在本地 NAS 上先跑起来的 MUD 骨架，基于 Evennia 官方 Docker 镜像。

## 适合什么场景

- 你想先做一个可进服、可网页登录、后续可继续二开的群聊 MUD
- 你接受先从开源框架起步，而不是 1:1 复制现有站点
- 你更看重 Docker 和后续扩展，而不是老式传统 MUD 的现成内容包

## 目录说明

- `docker-compose.yml`: 单容器启动配置
- `.env.example`: 端口和时区示例
- `game/`: 游戏数据目录，初始化后自动生成
- `docs/progress_2026-03-22.md`: 当前进度记录
- `docs/maintenance.md`: 维护手册

## 第一次启动

1. 复制环境文件

```powershell
Copy-Item .env.example .env
```

2. 初始化游戏目录

```powershell
docker compose run --rm mud evennia --init mygame .
```

3. 创建数据库结构

```powershell
docker compose run --rm mud evennia migrate
```

4. 创建管理员账号

```powershell
docker compose run --rm mud evennia createsuperuser
```

5. 启动服务

```powershell
docker compose up -d
```

## 访问方式

- Telnet: `NAS_IP:4000`
- Web: `http://NAS_IP:4001`
- WebSocket: `NAS_IP:4002`

## 群晖和反代建议

- 先直接用端口访问，确认服务正常后再接入反向代理
- 如果做 HTTPS 反代，记得一并转发 WebSocket
- 如果只打算群里小范围玩，先内网或 Tailscale 暴露会更省事


## 下一步适合补什么

- 中文登录页和创建角色页
- 地图/房间/门派/战斗循环
- 群聊频道和公告
- 每日任务、挂机、掉落、背包
- 简单管理后台
