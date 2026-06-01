# 1Password Connect MCP

> 更新时间：2026-05-31

## 架构概览

```
Factory Droid (Mac)
  └── APISIX (192.168.88.11:9080)
        ├── key-auth (consumer: droid_mcp)
        ├── ip-restriction (内网/Tailscale 白名单)
        └── upstream: 1password-connect-mcp:8000 (Docker 网络)
              └── op-connect-api (172.19.0.2:8080)
                    └── 1Password Connect Server (Bearer token auth)
```

## 组件部署位置

| 组件 | 服务器 | 监听地址 | Docker 网络 |
|------|--------|---------|------------|
| APISIX 网关 | apisix-gw-test-01 (192.168.88.11) | 0.0.0.0:9080 | apisix-gw-test-01_default |
| 1password-connect-mcp | apisix-gw-test-01 | 127.0.0.1:8000 | 1password-connect_default + apisix-gw-test-01_default |
| op-connect-api | apisix-gw-test-01 | 127.0.0.1:8080 | 1password-connect_default |
| op-connect-sync | apisix-gw-test-01 | 127.0.0.1:8081 | 1password-connect_default |

## MCP 端点

| 参数 | 值 |
|------|------|
| 入口 URL | `http://192.168.88.11:9080/mcp/1password` |
| 类型 | SSE (HTTP) |
| 认证 | `apikey` header (APISIX consumer key) |
| APISIX 路由 | mcp-1password (priority=1) |
| 上游 | 1password-connect-mcp:8000 (Docker 网络) |

## 认证链路

1. **客户端 → APISIX**：`apikey` header（APISIX consumer key）
2. **MCP → Connect API**：`Authorization: Bearer <JWT>` header

## MCP 工具列表

| 工具 | 描述 |
|------|------|
| `list_vaults` | 列出所有可访问的 vault（仅元数据） |
| `search_items` | 按标题搜索 vault 中的 item |
| `get_item` | 按 ID 获取 item 详情（含非敏感字段） |
| `read_secret` | 读取单个敏感字段值（需 vault_id + item_id + field_label） |

## Consumer 配置

| Consumer | 用途 |
|----------|------|
| `droid_mcp` | Factory Droid 访问 1Password MCP |

## 容器配置

```yaml
name: 1password-connect-mcp
image: safe-1password-mcp-safe-1password-mcp:latest
restart: unless-stopped
networks:
  - 1password-connect_default
  - apisix-gw-test-01_default
ports:
  - 127.0.0.1:8000:8000
environment:
  OP_CONNECT_HOST: http://<op-connect-api-ip>:8080
  OP_API_KEY: <JWT Bearer Token (665 字符)>
  SSE_PATH: /mcp/1password
  MESSAGE_PATH: /mcp/1password/messages
  PORT: 8000
```

## Droid MCP 配置

```json
{
  "mcpServers": {
    "1password-connect": {
      "type": "http",
      "url": "http://192.168.88.11:9080/mcp/1password",
      "headers": {
        "apikey": "<droid_mcp_consumer_key>"
      }
    }
  }
}
```

## 1Password 凭证映射

| 条目 | 字段 | 用途 |
|------|------|------|
| 1Password Connect / Server (API_CREDENTIAL) | 凭据 | JWT Bearer Token（OP_API_KEY，665 字符） |
| Linear / API Token | 凭据 | Linear API 访问 (lin_api_...) |

## 已知问题与修复记录

### ConnectClient 认证方式不匹配

**问题：** `safe-1password-mcp` 的 `ConnectClient.request()` 使用 `apikey` header 发送认证，但 1Password Connect API 的 JWT token 仅支持 `Authorization: Bearer` header。

**修复：** 修改容器内 `/app/index.js`：

```diff
- apikey: this.apiKey,
+ Authorization: `Bearer ${this.apiKey}`,
```

### Docker 网络隔离

**问题：** MCP 容器在 `1password-connect_default` 网络，APISIX 在 `apisix-gw-test-01_default` 网络，APISIX 无法解析容器名。

**修复：** 将 MCP 容器连接到两个网络：

```bash
docker network connect apisix-gw-test-01_default 1password-connect-mcp
```

## 故障排查

```bash
# 1. 检查容器状态
docker ps | grep 1password-connect-mcp

# 2. 检查容器日志
docker logs 1password-connect-mcp --tail 50

# 3. 检查 Connect API 健康状态
curl http://127.0.0.1:8080/health

# 4. 检查 Docker 网络连通性
docker exec apisix-gw-test-01 sh -c "getent hosts 1password-connect-mcp"

# 5. 检查 APISIX 路由
docker exec apisix-etcd etcdctl get /apisix/routes/mcp-1password --print-value-only

# 6. 检查 Consumer 配置
docker exec apisix-etcd etcdctl get /apisix/consumers/droid_mcp --print-value-only

# 7. 端到端测试
curl -sfN "http://192.168.88.11:9080/mcp/1password" \
  -H "Accept: text/event-stream" \
  -H "apikey: <key>"
```

## 完整 ShowDoc 文档

更详细的 APISIX 路由配置见：
- APISIX 网关文档 → 路由配置 → [路由详情 - 1Password MCP](http://192.168.88.11:9080/showdoc/web/#/664858315/269622089)
