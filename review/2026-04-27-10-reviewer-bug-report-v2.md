# FINAL_REVIEW_REPORT — 10 审查员 (gpt-5.4-mini) 代码 Bug 审查报告 v2

generated_by: codex_main_agent
review_date: 2026-04-27
source_dir: /Users/busiji/memory/workspace/tools

---

## Input Artifacts

| Artifact | Status |
|----------|--------|
| PROJECT_STRUCTURE_SNAPSHOT | ✅ 16 source files, 21 test files |
| PROJECT_ARCHITECTURE_MAP | ✅ entry / service / domain / repository / infra / config / common |
| PROJECT_RISK_INDEX | ✅ hub_files: gateway.py, impls.py, business_policy_checks.py |
| CALL_GRAPH_INDEX | ✅ main() → build_context_package → core → impls → adapters |
| REVIEW_ASSIGNMENT_PLAN | ✅ R1–R10 assigned |

## Project Summary

| Metric | Value |
|--------|-------|
| Total source files | 16 |
| Total source lines | 4,885 |
| Primary language | Python 3.10+ |
| Hub files | gateway.py (1048), impls.py (1321), business_policy_checks.py (677) |
| High risk paths | module-level globals().update, subprocess.run(no timeout), ArtifactSinkImpl non-atomic write |

## Missing Reviewer Reports

| Reviewer | Status |
|----------|--------|
| R2 (service-layer) | **缺失** — 限流重试失败 |
| R7 (service-repository-boundary) | **缺失** — 限流重试失败 |

> R2 和 R7 的覆盖范围已由 R3, R9, R10 部分覆盖，但 service 层状态流转和 service→repository 边界的专项交叉验证未完成。

---

## Summary

| Severity | Count |
|----------|-------|
| **P0** | **3** |
| **P1** | **9** |
| **P2** | **15** |
| **P3** | **6** |
| **Total** | **33** |

---

## Findings — P0

### P0-01: `_ADAPTER_REGISTRY` 无 Key 校验导致模块加载崩溃

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 92
- **type**: 崩溃 (KeyError)
- **trigger**: `MEMORY_HOOK_ADAPTER` 环境变量设置为 `_ADAPTER_REGISTRY` 中不存在的值
- **call_chain**: 模块加载 → `_ADAPTER_REGISTRY[_ADAPTER_NAME]` → KeyError
- **expected**: 对未注册的 adapter 名称给出明确错误或降级
- **actual**: 直接抛 KeyError，整个模块 import 失败
- **discovered_by**: R1, R10

### P0-02: adapter profile 返回非 dict 导致模块加载崩溃

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 110, 113
- **type**: 崩溃 (TypeError)
- **trigger**: adapter 函数 `_fn(REPO_ROOT, WORKSPACE_ROOT)` 返回非 dict
- **call_chain**: 模块加载 → `load_adapter_config(profile)` → `_adapter_config.update(profile)` → TypeError
- **expected**: `isinstance(profile, dict)` 校验
- **actual**: 无类型检查，直接 `.update()`
- **discovered_by**: R10

### P0-03: adapter 模块缺失预期函数导致模块加载崩溃

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 98
- **type**: 崩溃 (AttributeError)
- **trigger**: `_ADAPTER_REGISTRY` 中注册的函数名在模块中不存在
- **call_chain**: 模块加载 → `getattr(_mod, _fn_name)` → AttributeError
- **expected**: getattr 失败时有 fallback
- **actual**: 无 default 值，模块加载失败
- **discovered_by**: R10

---

## Findings — P1

### P1-01: ArtifactSinkImpl 非原子写入导致并发/崩溃时文件不一致

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`
- **line**: 1133-1134
- **type**: 竞态 / 静默失败
- **trigger**: 两个 hook 进程同时调用 `ArtifactSinkImpl.write()`，或写入中途进程被 kill
- **call_chain**: `main()` → `ArtifactWriter.write()` → `ArtifactSinkImpl.write()` → `write_text()` × 2
- **expected**: 使用 tmp+rename 保证原子性（同文件内 `_write_hook_state_unlocked` 已有此模式）
- **actual**: 直接 `write_text()` 两次，snapshot 和 latest 可能不一致
- **discovered_by**: R3, R9

### P1-02: subprocess.run 全量缺少 timeout — cmux delegate 挂起

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`
- **line**: 150, 245
- **type**: 边界 (资源耗尽)
- **trigger**: cmux 子进程挂起
- **call_chain**: `main()` → delegate.execute() → subprocess.run (无 timeout)
- **expected**: 设置 timeout=30s
- **actual**: 无 timeout，整个 gateway 永久阻塞
- **discovered_by**: R4, R8, R9

### P1-03: `_canonicalize_cmux_refs` subprocess 无 timeout

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 938
- **type**: 边界 (资源耗尽)
- **trigger**: cmux identify 进程挂起
- **call_chain**: `ClaudeDelegate.execute()` → `self._canonicalizer()` → subprocess.run (无 timeout)
- **expected**: 设置 timeout
- **actual**: 无 timeout
- **discovered_by**: R4, R8, R9

### P1-04: `globals().update(profile)` 模块级命名空间污染

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 113, 119
- **type**: 安全 (模块状态污染)
- **trigger**: adapter profile 包含与已有全局变量同名的 key
- **call_chain**: 模块加载 → `load_adapter_config()` → `globals().update(profile)`
- **expected**: 使用封闭 namespace，不污染 globals()
- **actual**: 任意 key 直接覆盖模块级变量
- **discovered_by**: R1, R8, R9

### P1-05: adapter profile 函数被调用两次

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 117-119
- **type**: 逻辑错误
- **trigger**: 模块加载时无条件执行
- **call_chain**: L117 `_adapter_profile = _fn(...)` → L119 `globals().update(_fn(...))`
- **expected**: 只调用一次
- **actual**: 调用两次，可能造成 `_adapter_config` 和 `globals()` 不一致
- **discovered_by**: R1, R8

### P1-06: `_load_external_core_builder()` 任意模块加载

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 194
- **type**: 安全 (任意代码执行)
- **trigger**: `MEMORY_HOOK_EXTERNAL_CORE_MODULE` 设为恶意模块名
- **call_chain**: `_resolve_core_builder()` → `__import__(module_name)`
- **expected**: 白名单校验或路径前缀限制
- **actual**: 直接 `__import__()` 环境变量内容
- **discovered_by**: R1, R9

### P1-07: `write_artifacts()` fallback 中 KeyError

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 911, 916
- **type**: 崩溃 (KeyError)
- **trigger**: `package` 缺少 `host` 或 `event` key 时进入 fallback
- **call_chain**: `write_artifacts()` → RuntimeError fallback → `package['host']` → KeyError
- **expected**: 使用 `.get()` 防御性访问
- **actual**: 直接 `package['host']`
- **discovered_by**: R1, R10

### P1-08: ArtifactSinkImpl.write 未防御 package key

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`
- **line**: 1120
- **type**: 崩溃 (KeyError)
- **trigger**: 传入 `package` 缺少 `host` 或 `event`
- **call_chain**: `ArtifactWriter.write()` → `_sink.write(package)` → `package['host']` → KeyError
- **discovered_by**: R10

### P1-09: PolicyRegistryImpl 缺失 "default" conflict strategy

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`
- **line**: 379
- **type**: 崩溃 (KeyError)
- **trigger**: policy-pack JSON 覆盖后不包含 `"default"` key
- **call_chain**: `get_policy_pack()` → `self._conflict_strategies["default"]` → KeyError
- **discovered_by**: R10

---

## Findings — P2

### P2-01: 文件名生成 TOCTOU 竞争窗口

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`
- **line**: 1122-1124
- **type**: 竞态
- **trigger**: 两个进程同一微秒调用 `write()` 生成相同文件名
- **discovered_by**: R3, R9

### P2-02: `_write_hook_state_unlocked` 验证回读在写入成功后抛异常

- **file**: `/Users/busiji/memory/workspace/tools/cmux_hook_state.py`
- **line**: 141
- **type**: 静默失败
- **trigger**: `Path.replace()` 成功后 `load_hook_state_strict()` 失败
- **discovered_by**: R3

### P2-03: ClaudeDelegate noop_response stdout 为空（与 CodexDelegate 不一致）

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`
- **line**: 254-255
- **type**: 逻辑错误
- **trigger**: Claude noop 返回 `""`, Codex 返回 `"{}\n"`
- **discovered_by**: R4

### P2-04: resolve_policies 硬编码绝对导入路径

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_adapters/workbot_policy.py`
- **line**: 79
- **type**: 代码异味
- **trigger**: `from workspace.tools.memory_hook_impls import PolicyRegistryImpl` 无 fallback
- **discovered_by**: R4

### P2-05: git subprocess 调用无 timeout

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 604, 624, 631
- **type**: 边界
- **trigger**: 损坏的 repo 或锁定文件系统上 git 操作挂起
- **discovered_by**: R8

### P2-06: inject_policy_pack_config / resolve_policies 死代码

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_adapters/workbot_policy.py`
- **line**: 54-82
- **type**: 代码异味
- **trigger**: 方法已定义但从未被调用
- **discovered_by**: R8

### P2-07: AEdu 硬编码路径无加载时校验

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_adapters/workbot_runtime_profile.py`
- **line**: 111-124
- **type**: 边界
- **trigger**: AEdu 目录不存在时静默失败
- **discovered_by**: R8

### P2-08: CoreConfig 缺少 project_map_governance / event_log 的 Path 类型校验

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_config.py`
- **line**: 90
- **type**: 验证不完整
- **trigger**: 传入 `Path("")` 通过验证
- **discovered_by**: R5

### P2-09: convert_to_v1 不校验输入 schema_version

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_schema.py`
- **line**: 30
- **type**: 静默失败
- **trigger**: v1 package 被重复转换，静默产出错误格式
- **discovered_by**: R5

### P2-10: TypedDict total=False 导致所有 key 可选

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_interfaces.py`
- **line**: 23, 37
- **type**: 代码异味
- **trigger**: 实现可返回 `{}` 满足类型检查但运行时出错
- **discovered_by**: R5

### P2-11: `_read_payload()` 无 schema 验证

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 331-338
- **type**: 安全 / 输入验证
- **trigger**: stdin 传入任意 JSON 结构
- **discovered_by**: R1, R9

### P2-12: `_path_is_under_lexical()` 不 resolve symlinks

- **file**: `/Users/busiji/memory/workspace/tools/business_policy_checks.py`
- **line**: 82-88
- **type**: 安全 / 路径逃逸
- **trigger**: cwd 为指向 repo 外的符号链接
- **discovered_by**: R9

### P2-13: event log 并发追加写无锁

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`
- **line**: 1136
- **type**: 竞态
- **trigger**: 多进程同时写入 events.jsonl
- **discovered_by**: R9

### P2-14: `_registration_payload_paths()` 从 payload 直接取值无 repo 内校验

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 540-544
- **type**: 安全 / 路径遍历
- **trigger**: payload 中包含 `registration_paths` 指向 repo 外路径
- **discovered_by**: R9

### P2-15: validate_project_map_files 越界访问

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`
- **line**: 840
- **type**: 崩溃 (IndexError)
- **trigger**: `project_map_files` 少于 3 个元素
- **discovered_by**: R10

---

## Findings — P3

### P3-01: `_write_hook_state_unlocked` 缺少目录 fsync

- **file**: `/Users/busiji/memory/workspace/tools/cmux_hook_state.py`
- **line**: 135-136
- **discovered_by**: R3

### P3-02: policy-pack TOCTOU (exists → read_text)

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_adapters/workbot_policy.py`
- **line**: 47-48, 57-59
- **discovered_by**: R4

### P3-03: `CLAUDE_HOOK_STATE_FILE` 模块加载时固化

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_adapters/workbot_runtime_profile.py`
- **line**: 253
- **discovered_by**: R8

### P3-04: `_adapter_config` 与 `globals()` 双写/双读不一致

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 109-113, 119, 758
- **discovered_by**: R8

### P3-05: CoreConfig surface_id / workspace_id 允许空字符串

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_config.py`
- **line**: 144
- **discovered_by**: R5

### P3-06: `from_gateway_kwargs` 死代码

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_config.py`
- **line**: 189
- **discovered_by**: R5

---

## Rejected Findings

无。所有 finding 均包含必要字段。

---

## Coverage Matrix

| Layer | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 |
|-------|----|----|----|----|----|----|----|----|----|----|
| entry | ✅ | — | — | — | — | ✅ | — | — | ✅ | ✅ |
| service | — | ❌ | — | — | — | — | — | ✅ | ✅ | ✅ |
| repository | — | — | ✅ | — | — | — | ❌ | — | ✅ | — |
| infra | — | — | — | ✅ | — | — | — | ✅ | ✅ | — |
| common/config | — | — | — | — | ✅ | — | — | — | — | — |
| entry↔service | — | — | — | — | — | ✅ | — | — | — | — |
| service↔repo | — | — | — | — | — | — | ❌ | — | — | — |
| service↔infra | — | — | — | — | — | — | — | ✅ | — | — |
| security/concurrency | — | — | — | — | — | — | — | — | ✅ | — |
| crash-paths | — | — | — | — | — | — | — | — | — | ✅ |

---

## Non-Findings Summary

已验证为安全的路径（共 40+ non-findings），关键结论：

- `cmux_hook_state.py` 的锁+原子写入链路（lock → mkstemp → fsync → replace → verify）设计正确
- `_path_within_repo()` 使用 `resolve().relative_to()` 正确阻止路径遍历
- 所有 subprocess.run 使用列表参数，无 shell=True，无命令注入
- CLI 入参通过 argparse required + choices 完整校验
- Error logging 有双层回退机制
- CoreConfig `__post_init__` 对 37 个字段做类型校验

---

## 补充：R6 (entry-service-boundary) 迟到报告

R6 报告因限流延迟到达，以下发现为新增或交叉验证：

### 新增 P2

#### P2-16: `write_artifacts()` 仅捕获 RuntimeError，漏捕获 OSError/KeyError

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 904-927
- **type**: 异常传播缺陷
- **trigger**: `ArtifactSinkImpl.write()` 内部 `package['host']` 抛 KeyError 或 `write_text()` 抛 OSError
- **call_chain**: `write_artifacts()` → `_write_artifacts_via_sink()` → `ArtifactSinkImpl.write()` → KeyError/OSError 穿透
- **expected**: 捕获 `Exception` 或 `(RuntimeError, OSError, KeyError)`
- **actual**: 仅 `except RuntimeError`
- **discovered_by**: R6

#### P2-17: `append_error_log()` 同样仅捕获 RuntimeError

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 893-901
- **type**: 异常传播缺陷
- **trigger**: `ErrorSinkImpl.log()` 内部 `mkdir`/`open` 抛 OSError
- **discovered_by**: R6

#### P2-18: `main()` 直接索引 package["status"] 和 package["missing_paths"]

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py`
- **line**: 987, 994
- **type**: 不安全键访问
- **trigger**: `build_context_package` 返回不含这些键的 dict（shadow-run 或 external-core 异常）
- **discovered_by**: R6

### 新增 P3

#### P3-07: `_resolve_callbacks()` interface 对象路径为死代码

- **file**: `/Users/busiji/memory/workspace/tools/memory_hook_core.py`
- **line**: 22-46
- **type**: 死代码
- **trigger**: `config.policy_registry` 始终为 None，interface 路径从未被激活
- **discovered_by**: R6

### R6 交叉验证 Non-Findings

R6 确认了以下 entry↔service 边界的安全性（8 项 non-findings）：

1. CoreConfig 字段与 `build_context_package()` kwargs 1:1 匹配 ✅
2. `build_context_package_from_config → build_context_package_core` 33 个参数映射完整 ✅
3. `GatewayBusinessPolicyConfig` 37 个字段与 gateway 传递值匹配 ✅
4. `PolicyRegistryImpl` 实现 `PolicyRegistry` 全部 12 个抽象方法 ✅
5. `RouteTargetPolicyImpl` / `WriteTargetPolicyImpl` 签名匹配 ✅
6. `ArtifactSinkImpl` / `ErrorSinkImpl` 接口契约满足 ✅
7. `CodexDelegate` / `ClaudeDelegate` 方法名、参数、返回类型匹配 ✅
8. Context package DTO 17 个顶层键对消费者完整 ✅

### 更新后统计

| Severity | 原始 | 补充 | 总计 |
|----------|------|------|------|
| P0 | 3 | 0 | **3** |
| P1 | 9 | 0 | **9** |
| P2 | 15 | +3 | **18** |
| P3 | 6 | +1 | **7** |
| **Total** | **33** | **+4** | **37** |
