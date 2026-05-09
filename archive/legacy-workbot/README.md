# archive/legacy-workbot/

> 归档目录 | 创建时间：2026-05-09 | 来源：memory-core v0.2.x Phase 1 业务残留迁出

## 用途

本目录归档 memory-core 仓库历史上沉淀的、与 **workbot / AxonHub** 等具体业务项目耦合的内容。这些内容违反 `docs/BOUNDARY.md` 4.1 单一归属原则与 4.3 通用 vs 专用原则，从 v0.2.x 起从主路径迁出。

## 内容清单

### kb/ — 8 个业务知识文件

| 文件 | 原路径 | 性质 |
|---|---|---|
| `workbot.md` | `memory_core/memory/kb/projects/workbot.md` | workbot 项目真相 |
| `workbot-truth-model.md` | `memory_core/memory/kb/global/workbot-truth-model.md` | workbot 真相模型 |
| `workbot-memory-system.md` | 同前缀 | workbot 记忆系统说明 |
| `workbot-hook-contract.md` | 同前缀 | workbot hook 合约 |
| `workbot-project-map-governance.md` | 同前缀 | workbot 地图治理 |
| `workbot-policy-pack.md` | 同前缀 | workbot policy pack（说明） |
| `workbot-policy-pack.json` | 同前缀 | workbot policy pack（数据） |
| `workbot-memory-routing.md` | 同前缀 | workbot 记忆路由 |

### tests-disabled/ — 8 个业务耦合测试

测试用例在源码中通过硬编码路径直接读取 kb/ 下文件内容，或自标 "workbot-scoped" 强制启用 workbot adapter，因此随业务文件一起归档，从 `tests/` 路径下迁出以避免 pytest 收集失败。

| 文件 | 依赖的 kb 资源 |
|---|---|
| `test_m3_doc_scope_coverage.py` | 6 个 workbot-*.md/.json |
| `test_m3_consumer_truth_cleanup.py` | workbot-memory-routing.md + workbot.md |
| `test_m3_policy_pack_wiring.py` | workbot-policy-pack.json |
| `test_m2_adapter_extraction.py` | workbot-hook-contract.md |
| `test_memory_hook_core_m5_adapter_slimming.py` | workbot-* kb |
| `test_business_policy_errors.py` | workbot-* kb |
| `test_m7_independent_repo_baseline.py` | workbot-project-map-governance.md |
| `test_m7_p3_smoke.py` | 强制启用 workbot adapter，需 8 个 kb 文件 |

### projects-spec-axonhub-section.md — AxonHub 部署运维段

`memory_core/memory/kb/global/projects-spec.md` 第 11 节"CE-01 自动化部署"被剥离至此（含 SSH 别名、IP 地址、Docker 服务名、镜像版本号等业务专属运维信息）。

## 恢复方法

如需在 workbot adapter 启用时恢复这些文件：

```bash
# 1. 恢复 8 个 kb 文件到原位置
mv archive/legacy-workbot/kb/workbot.md memory_core/memory/kb/projects/workbot.md
mv archive/legacy-workbot/kb/workbot-*.md archive/legacy-workbot/kb/workbot-policy-pack.json memory_core/memory/kb/global/

# 2. 恢复 7 个测试文件
mv archive/legacy-workbot/tests-disabled/*.py tests/

# 3. 恢复 projects-spec.md 第 11 节
cat archive/legacy-workbot/projects-spec-axonhub-section.md >> memory_core/memory/kb/global/projects-spec.md
# 然后手工删除 projects-spec.md 末尾的剥离说明段

# 4. 启用 workbot adapter
export MEMORY_HOOK_ADAPTER=workbot

# 5. 验证
ruff check . && python3 -m pytest -q tests
```

## 注意事项

- **archive/** 目录已在 pytest 配置 `testpaths = ["tests"]` 范围之外，pytest 默认不会收集，不影响 CI。
- `memory_hook_adapters/workbot_runtime_profile.py` 中仍硬编码引用了部分原路径，**仅在显式启用 workbot adapter 时生效**。如需运行 workbot adapter，必须先按上述恢复方法恢复文件。
- 本归档保留 git 历史。`git log --follow archive/legacy-workbot/<file>` 可追溯原文件历史变更。

## 相关决策

- 决策依据：`docs/BOUNDARY.md` 4.1 单一归属、4.3 通用 vs 专用
- 审计来源：`docs/audit/2026-05-09-memory-core-audit.md` A.13/A.14
- 处置选项：Phase1=A（真正迁出，保留可回滚）
