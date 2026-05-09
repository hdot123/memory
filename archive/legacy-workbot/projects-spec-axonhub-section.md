## 11. CE-01 自动化部署

> CE-01 是构建验证和预发布服务器，所有任务必须通过 CE-01 的验证才能视为完成。

### 11.1 服务器信息

| 项目 | 值 |
|------|-----|
| SSH 别名 | `ce-01` |
| IP | `192.168.88.15` |
| 用户 | `root` |
| Go 版本 | 1.26.2 |
| OS | Ubuntu, 8核 / 23GB RAM |
| 仓库路径 | `/root/axonhub-ci/` |
| 端口 | `8090`（AxonHub）, `5432`（PostgreSQL） |
| Docker 服务 | `axonhub-app`（应用）, `axonhub-postgres`（数据库） |
| 当前镜像 | `axonhub-hdot:v0.9.37-latest` |
| PATH 注意 | 需 `export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin` |

### 11.2 自动化集成点

CE-01 在以下环节自动参与：

```
制定流程完成
    │
    ├── L1 Worker 验收（本地）→ 通过
    │
    ├── L2 集成验收（本地）→ 通过
    │
    ├── ★ CE-01 部署验证（远程）← 新增
    │   ├── 同步代码到 CE-01
    │   ├── 远程编译
    │   ├── 远程测试
    │   ├── 重建镜像 + 重启服务
    │   └── 健康检查
    │
    ├── L3 最终验收（本地）→ 通过
    │
    └── P1 merge + push
```

### 11.3 CE-01 部署步骤

以下步骤在 P1 之前、L2 通过之后执行，由主线程直接操作。

#### Step 1: 同步代码

```bash
# 将本地 branch-2 推送到 origin
cd <project-root>/axonhub
git push origin branch-2

# 在 CE-01 上拉取最新代码
ssh ce-01 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin && \
  cd /root/axonhub-ci && \
  git fetch origin && \
  git checkout branch-2 && \
  git reset --hard origin/branch-2'
```

#### Step 2: 远程编译验证

```bash
ssh ce-01 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin && \
  cd /root/axonhub-ci && \
  go build -ldflags "-s -w" -tags=nomsgpack -o axonhub ./cmd/axonhub && \
  echo "BUILD OK"'
```

**编译失败 → 不继续，回到 L2 修复。**

#### Step 3: 远程测试

```bash
ssh ce-01 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin && \
  cd /root/axonhub-ci && \
  go test ./... -count=1 -timeout 300s'
```

**测试失败 → 不继续，回到 L2 修复。**

#### Step 4: 构建镜像

```bash
ssh ce-01 'cd /root/axonhub-ci && \
  docker build -t axonhub-hdot:v0.9.38-latest -t axonhub-hdot:v0.9.37-latest .'
```

**镜像版本号：** 从 `internal/build/VERSION` 读取或手动指定。每次部署打两个标签：
- `v0.9.XX-latest`：固定 latest 标签，docker-compose 引用这个
- `v0.9.XX-<短hash>`：可追溯的具体版本

#### Step 5: 重启服务

```bash
ssh ce-01 'cd /root/axonhub-ci && \
  docker stop axonhub-app && \
  docker rm axonhub-app && \
  docker compose up -d axonhub && \
  sleep 5 && \
  docker ps --format "{{.Names}} {{.Status}}"'
```

#### Step 6: 健康检查

```bash
# 等待服务启动
ssh ce-01 'sleep 10 && \
  curl -sf http://localhost:8090/api/health 2>/dev/null && \
  echo "HEALTH OK" || echo "HEALTH FAIL"'

# 检查日志
ssh ce-01 'docker logs axonhub-app --tail 30'
```

**健康检查失败 → 查日志定位问题，回滚到上一版本镜像。**

#### Step 7: 回滚方案

```bash
# 如果新版本有问题，回滚到旧镜像
ssh ce-01 'cd /root/axonhub-ci && \
  docker stop axonhub-app && \
  docker rm axonhub-app && \
  docker run -d \
    --name axonhub-app \
    --network axonhub-network \
    -p 8090:8090 \
    -v /root/axonhub-ci/config.yml:/app/config.yml:ro \
    -e AXONHUB_DB_DIALECT=postgres \
    -e "AXONHUB_DB_DSN=YOUR_DATABASE_DSN_HERE" \
    --restart unless-stopped \
    axonhub-hdot:v0.9.37-latest'
```

### 11.4 CE-01 在 STATE 文件中的记录

```markdown
## CE-01 部署记录

### 部署 — YYYY-MM-DD HH:MM
- 代码同步：✅/❌
- 远程编译：✅/❌
- 远程测试：✅/❌
- 镜像构建：✅/❌（版本：v0.9.XX-<hash>）
- 服务重启：✅/❌
- 健康检查：✅/❌
- 最终状态：SUCCESS / ROLLBACK
```

### 11.5 CE-01 与验收层级的关系

| 层级 | 执行位置 | CE-01 参与 |
|------|----------|------------|
| L1 Worker 验收 | 本地 | 否 |
| L2 集成验收 | 本地 | 否 |
| **CE-01 部署验证** | **远程** | **是（核心）** |
| L3 最终验收 | 本地 | CE-01 通过后才执行 L3 |

流程变为：

```
L1 全部通过 → L2 通过 → CE-01 部署验证 → L3 → P1 merge
                              │
                              ├── 失败 → 修复 → 重跑 L2 → 重试 CE-01
                              └── 通过 → 继续 L3
```

### 11.6 通用项目的 CE-01 使用

如果项目不是 AxonHub，CE-01 仍可用于：

- 远程编译验证（有 Go 环境）
- Docker 镜像构建（有 Docker）
- 服务部署（有 docker-compose）

主线程在制定流程中判断是否需要 CE-01：
- 涉及 Go 编译 → Step 2 远程编译
- 涉及 Docker → Step 4-5 构建部署
- 不涉及 → 跳过 CE-01

### 11.7 CE-01 快捷命令速查

```bash
# SSH 前缀（每次都需要）
CE="ssh ce-01 'export PATH=\$PATH:/usr/local/go/bin:\$HOME/go/bin && "

# 查看状态
ssh ce-01 'docker ps --format "{{.Names}} {{.Status}}" && cat /root/axonhub-ci/internal/build/VERSION'

# 查看日志
ssh ce-01 'docker logs axonhub-app --tail 50 -f'

# 重启服务
ssh ce-01 'cd /root/axonhub-ci && docker compose restart axonhub'

# 查看磁盘
ssh ce-01 'df -h / && docker system df'

# 清理旧镜像
ssh ce-01 'docker image prune -f'
```
