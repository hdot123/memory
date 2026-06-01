# 服务器资产清单

> 更新时间：2026-06-01
> 维护人：busiji

## 服务器总览

| 名称 | 公网 IP | Tailscale IP | OS | 配置 | 磁盘使用 | Droid Computer ID |
|------|---------|-------------|-----|------|---------|-------------------|
| busiji-mac-3 | — | — | macOS | Apple Silicon | — | d6cf2cd1-a7b8-4aad-a71f-ca89c90d2c33 |
| busiji-mac-2 | — | — | macOS | — | — | 18e815ea-22f2-4f4d-8d19-64ffeb8d005c |
| node-22 | 43.167.177.86 | 100.100.1.22 | Ubuntu 24.04 | 4CPU/8GB/59G | 57% (32G/59G) | 313ac75f-0c3f-4893-81ae-a03807cd9ad5 |

## node-22 详情

### 基础信息

| 项目 | 值 |
|------|-----|
| 主机名 | VM-0-8-ubuntu |
| 内核 | 6.8.0-101-generic (x86_64) |
| 公网 IP | 43.167.177.86 |
| Tailscale IP | 100.100.1.22 |
| WireGuard (10.7.0.x) | 10.7.0.8 |
| Droid 版本 | 0.137.1 |
| Droid 启动方式 | systemd (droid-daemon.service, 开机自启) |

### 运行中的服务

| 服务 | 类型 | 说明 |
|------|------|------|
| Nginx | systemd | 反向代理 (端口 80) |
| Docker | systemd | 容器引擎 (29.1.3) |
| Tailscale | systemd | VPN 组网 |
| Cloudflared | systemd | Cloudflare Tunnel |
| GOST | systemd | HTTPS CONNECT 代理 (端口 443/8443/11080) |
| Droid Daemon | systemd | Factory Droid 远程接入 (端口 37643) |
| Factory Trigger | systemd | Linear API 集成 (端口 8765) |
| SSH | systemd | OpenSSH (端口 22) |
| Chrony | systemd | NTP 时间同步 |

### Docker 容器

| 容器 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| n8n-webhook | n8n:2.19.3 | 100.100.1.22:5678 | 工作流自动化 |
| apisix-gateway | apisix:3.11.0 | 9080/9180 | API 网关 |
| apisix-etcd | etcd:3.5.11 | 2379 (内部) | APISIX 配置存储 |
| codex-proxy | codex-proxy:latest | 127.0.0.1:11455/18080 | Codex 代理 |
| webhook-ingress-canary-test | webhook-ingress:factory-adapter | 127.0.0.1:8081 | Webhook 入口 |
| tailscale-socks-proxy | gogost/gost:latest | — | Tailscale SOCKS 代理 |

### 已安装运行时

| 运行时 | 版本 |
|--------|------|
| Node.js | v22.22.2 |
| Python | 3.12.3 |
| Docker | 29.1.3 |
| MySQL Client | 8.0.45 |
| PostgreSQL Client | 16.14 |
| Nginx | 已安装 |

### 网络端口映射

| 端口 | 服务 | 绑定 | 暴露级别 |
|------|------|------|---------|
| 22 | SSH | 0.0.0.0 | 公网 |
| 80 | Nginx | 0.0.0.0 | 公网 |
| 443 | Tailscale/HTTPS | 100.100.1.22 / 10.7.0.8 | Tailscale+WG |
| 5678 | n8n | 100.100.1.22 | Tailscale |
| 8443 | GOST HTTPS | 10.7.0.8 | WireGuard |
| 8765 | Factory Trigger | 0.0.0.0 | 公网 |
| 8888 | Python http.server | 0.0.0.0 | 公网（待审查） |
| 9080 | APISIX | 多地址 | Tailscale+WG+本地 |
| 11080 | GOST | 100.100.1.22 | Tailscale |
| 37643 | Droid Daemon | 127.0.0.1 | 本地 |

### 待办

- [ ] 审查端口 8888 (agentuser 的 college-site http.server，绑定 0.0.0.0)
- [ ] 确认 agentuser 用户用途
