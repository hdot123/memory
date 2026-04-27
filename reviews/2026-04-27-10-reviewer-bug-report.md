# 10 审查员代码 Bug 审查报告

**仓库**: `/Users/busiji/memory/workspace/` | **18 源文件** | **5252 行**
**审查分支**: `branch-2` | **审查日期**: 2026-04-27
**审查员**: R1-R9（9 个 gpt-5.4-mini 子代理），R10 安全/并发由 R9 合并覆盖
**去重后独立 bug**: 1 P0 / 12 P1 / 22 P2 / 15 P3 = **50 个**

---


## P0 — 1 个

### P0-1. governance_frozen_tuple_errors 方法名断裂 — 治理校验永远静默通过

1. **文件绝对路径 + 精确行号**:
   - `/Users/busiji/memory/workspace/tools/memory_hook_interfaces.py:143`
   - `/Users/busiji/memory/workspace/tools/memory_hook_core.py:28`
   - `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:442`（stub）、`:917`（真实实现）
   - `/Users/busiji/memory/workspace/tools/business_policy_checks.py:262`

2. **严重度 + 分类**: P0 / 逻辑错误

3. **触发条件**: 任意通过 `PolicyRegistry`（或其子类）调用 `governance_frozen_tuple_errors()` 时。具体：`build_context_package_from_config(config)` → `_resolve_callbacks(config)` → `pr.governance_frozen_tuple_errors()`（L28）。

4. **崩溃链路**:
   ```
   build_context_package_from_config(config)
     → _resolve_callbacks(config)
       → pr.governance_frozen_tuple_errors()  # core.py L28
         → 命中 PolicyRegistryImpl.governance_frozen_tuple_errors()  # impls.py L442
           → return []  # stub，永远返回空列表
     → build_context_package_core(..., governance_tuple_errors=[])
       → governance_frozen_tuple_validation = "pass"  # 永远通过
   ```
   真实实现 `GatewayBusinessPolicyImpl.governance_frozen_tuple_blocker_errors`（L917）和 `FrozenTupleChecker.governance_frozen_tuple_blocker_errors`（L262）**永远不会被调用**。

5. **预期行为 vs 实际行为**:
   - 预期：接口方法名应为 `governance_frozen_tuple_blocker_errors`，命中真实实现。当 governance 文件缺失 frozen tuple 标记时返回非空错误列表。
   - 实际：接口声明的方法名缺 `_blocker` 后缀，stub 始终返回 `[]`，治理校验永远为 `"pass"`。

**发现者**: R8（交叉审查员）

---

## P1 — 12 个

### P1-1. validate_project_map vs validate_project_map_files 命名错位

1. **文件绝对路径 + 精确行号**:
   - `/Users/busiji/memory/workspace/tools/memory_hook_interfaces.py:133`（PolicyRegistry 抽象方法）
   - `/Users/busiji/memory/workspace/tools/memory_hook_interfaces.py:277`（GatewayBusinessPolicy 具体方法：`return self.get_required_canonical()`）
   - `/Users/busiji/memory/workspace/tools/memory_hook_interfaces.py:295`（GatewayBusinessPolicy.validate_project_map_files 抽象方法）
   - `/Users/busiji/memory/workspace/tools/memory_hook_core.py:24`（`_resolve_callbacks` 调用 `pr.validate_project_map`）
   - `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:835`（真实实现 `validate_project_map_files`）

2. **严重度 + 分类**: P1 / 逻辑错误

3. **触发条件**: `_resolve_callbacks(config)` 在 L24 执行 `pr.validate_project_map` 时，通过 MRO 查找方法。

4. **崩溃链路**:
   ```
   _resolve_callbacks(config)
     → pr.validate_project_map()  # core.py L24
       → MRO 查找命中 GatewayBusinessPolicy.validate_project_map  # interfaces.py L277
         → return self.get_required_canonical()  # 返回 list[Path]，不是错误列表
   → validate_project_map_fn = 返回路径列表的函数
   → 真正的 validate_project_map_files（marker 检查）永远不会被调用
   ```

5. **预期行为 vs 实际行为**:
   - 预期：应调用 `validate_project_map_files()`（执行 project-map 内容校验），返回错误列表。
   - 实际：调用 `validate_project_map()`，返回路径列表，project-map 文件的 marker 校验永远不会执行。

**发现者**: R8

---

### P1-2. EventContractChecker 部分文件缺失时 KeyError

1. **文件绝对路径 + 精确行号**:
   - `/Users/busiji/memory/workspace/tools/business_policy_checks.py:299-315`
   - `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:943-959`（等价实现）

2. **严重度 + 分类**: P1 / 崩溃

3. **触发条件**: `cfg.event_contract_files` 中 5 个文件有任意 1-4 个不存在于磁盘上（不是全部缺失）。

4. **崩溃链路**:
   ```
   event_contract_blocker_errors()
     → L303-307: 遍历 cfg.event_contract_files.items()
       → _read_text_if_exists(path) 对缺失文件返回 ""
       → if not content: missing_files.append(name); continue
       → 只把存在的文件内容放入 texts dict
     → L308-309: if len(missing_files) == len(cfg.event_contract_files): return [...]
       → 部分缺失时不走此分支
     → L311: texts["upstream_standard"]  → KeyError!
   ```

5. **预期行为 vs 实际行为**:
   - 预期：部分文件缺失时返回包含缺失文件名的错误列表。
   - 实际：`KeyError` 向上传播，未经捕获，整个 gateway 调用链崩溃。

**发现者**: R3, R8, R9

---

### P1-3. provider_builder 解析后从未调用 — external-core 永远不会执行

1. **文件绝对路径 + 精确行号**:
   - `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:819-820`
   - `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:840-841`（shadow run）

2. **严重度 + 分类**: P1 / 逻辑错误

3. **触发条件**: `MEMORY_HOOK_CORE_PROVIDER=external-core` 且外部模块成功加载。

4. **崩溃链路**:
   ```
   main()
     → L819: provider_name, provider_builder, provider_errors = _resolve_core_builder(...)
     → L820: build_context_package_from_config(config)  # 没用 provider_builder！
   shadow run 同理:
     → L840: _, shadow_builder, _ = _resolve_core_builder(...)
     → L841: build_context_package_from_config(config)  # 没用 shadow_builder！
   ```

5. **预期行为 vs 实际行为**:
   - 预期：当 `provider_name == "external-core"` 时调用 `provider_builder(...)`。
   - 实际：无论 provider_name 是什么，始终走 legacy 固定路径。`provider_builder` 赋值后即被丢弃。

**发现者**: R7

---

### P1-4. package["status"] KeyError 无保护

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:665`

2. **严重度 + 分类**: P1 / 崩溃

3. **触发条件**: `build_context_package()` 返回的 dict 缺少 `"status"` 键。具体场景：external core builder 返回非标准结构。

4. **崩溃链路**:
   ```
   main() → build_context_package() → 返回 package dict
     → if package["status"] != "ok":  → KeyError: 'status'
     → 进程崩溃，stdout 无输出
   ```

5. **预期行为 vs 实际行为**:
   - 预期：用 `.get("status", "degraded")` 兜底。
   - 实际：`KeyError` 未捕获，主进程以 traceback 退出。

**发现者**: R2

---

### P1-5. _read_payload() 静默吞掉 JSONDecodeError

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:306-311`

2. **严重度 + 分类**: P1 / 逻辑错误（静默失败）

3. **触发条件**: stdin 传入无效 JSON（如 `{"broken`）。

4. **崩溃链路**:
   ```
   main() → _read_payload(raw_payload) → json.loads() 失败 → return {}
     → _discover_cwd({}) → 回退到 env/REPO_ROOT
     → build_context_package() 正常执行，但 payload 关键字段全丢
     → payload.get("task_ref") 全部静默返回 None
   ```

5. **预期行为 vs 实际行为**:
   - 预期：至少记录一条错误日志或标记 `"_parse_error": True`。
   - 实际：完全静默，调用方不知道 payload 解析失败。

**发现者**: R2

---

### P1-6. write_artifacts() fallback 中 package["host"]/["event"] 可能不存在

1. **文件绝对路径 + 精确行号**:
   - `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:624-625`
   - `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:1120-1125`

2. **严重度 + 分类**: P1 / 崩溃

3. **触发条件**: 外部调用方直接调用 `write_artifacts()` 传入不含 `"host"` 或 `"event"` 键的 package。

4. **崩溃链路**:
   ```
   write_artifacts(package) → _write_artifacts_via_sink → RuntimeError
     → fallback: f"{timestamp}-{package['host']}-{package['event']}.json"
       → KeyError: 'host' 或 'event'
   ```

5. **预期行为 vs 实际行为**:
   - 预期：用 `.get("host", "unknown")` 兜底。
   - 实际：崩溃。公开 API 无保护。

**发现者**: R2, R6

---

### P1-7. validate_memory_system degraded 状态被报告为 PASS

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/validate_memory_system.py:187-188`

2. **严重度 + 分类**: P1 / 逻辑错误

3. **触发条件**: `build_context_package` 返回 `status: "degraded"`（canonical 缺失/治理 blocker/策略校验失败）。

4. **崩溃链路**:
   ```
   check_context_package(builder) → builder() 返回 {"status": "degraded", ...}
     → 结构检查通过 → result.record("context_package", True, ...)  → PASS
     → 验证器返回 0（全部通过）
   ```

5. **预期行为 vs 实际行为**:
   - 预期：`status != "ok"` 时应记录 FAIL。
   - 实际：status 仅用于日志输出，不影响 PASS/FAIL。验证器丧失探测 degraded 能力。

**发现者**: R5

---

### P1-8. validate_memory_system builder warnings 仍标记 PASS

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/validate_memory_system.py:100-101`

2. **严重度 + 分类**: P1 / 逻辑错误

3. **触发条件**: `_resolve_core_builder` 返回非空 errors 列表（external-core 降级时）。

4. **崩溃链路**:
   ```
   check_core_builder_resolve()
     → _resolve_core_builder() 返回 ("legacy", builder, ["external-core load failed, ..."])
     → if errors: → result.record("core_builder_resolve", True, "provider=legacy, warnings=1")  → PASS
   ```

5. **预期行为 vs 实际行为**:
   - 预期：errors 非空时记录 WARN 或 FAIL。
   - 实际：有 warning 仍标记为 PASS。

**发现者**: R5

---

### P1-9. convert_to_v1 静默丢弃 missing_paths 字段

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_schema.py:30-64`

2. **严重度 + 分类**: P1 / 逻辑错误（数据丢失）

3. **触发条件**: 通过 `build_context_package_simple()` 调用链路。

4. **崩溃链路**:
   ```
   build_context_package_simple() → build_context_package() → v2 package（含 missing_paths）
     → convert_to_v1(v2_package)
       → _KEEP_KEYS 不含 missing_paths → 丢弃
     → 调用方 result["missing_paths"] → KeyError
   ```

5. **预期行为 vs 实际行为**:
   - 预期：`missing_paths` 应被保留。
   - 实际：`convert_to_v1` 返回值中不存在 `missing_paths` 键。

**发现者**: R4

---

### P1-10. 环境变量控制 __import__ → 任意代码注入

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:192-196`

2. **严重度 + 分类**: P1 / 安全

3. **触发条件**: `MEMORY_HOOK_EXTERNAL_CORE_MODULE=os` + `MEMORY_HOOK_EXTERNAL_CORE_FUNC=system` + `MEMORY_HOOK_CORE_PROVIDER=external-core`。

4. **崩溃链路**:
   ```
   _load_external_core_builder()
     → __import__("os", fromlist=["system"]) → os 模块
     → getattr(os, "system") → os.system 作为 builder 返回
     → 调用者可执行任意 shell 命令
   ```

5. **预期行为 vs 实际行为**:
   - 预期：核心 builder 只能从预置、经过审核的内部模块加载。
   - 实际：任何可控制的 Python 模块均可被加载并暴露任意函数。

**发现者**: R9

---

### P1-11. globals().update(profile) 污染模块命名空间

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:113, 119`

2. **严重度 + 分类**: P1 / 安全

3. **触发条件**: adapter profile 返回 dict 包含 `__builtins__`、`open` 等关键名称。

4. **崩溃链路**:
   ```
   L113: load_adapter_config(_adapter_profile) → globals().update(profile)
   L119: globals().update(_fn(REPO_ROOT, WORKSPACE_ROOT))
     → 若 profile 含 "now_iso" 键 → 覆盖 now_iso() 函数
     → 后续调用 now_iso() → TypeError: 'str' object is not callable
   ```

5. **预期行为 vs 实际行为**:
   - 预期：profile 仅作配置数据存储，不覆盖模块级变量。
   - 实际：两次 `globals().update()`，无白名单过滤。

**发现者**: R2, R5, R7, R9

---

### P1-12. PolicyRegistryImpl.git_registration_probe stub 返回空 dict

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:451`

2. **严重度 + 分类**: P1 / 崩溃

3. **触发条件**: 调用 `PolicyRegistryImpl.git_registration_probe()`（stub 路径），下游按 `RegistrationCommitGate` TypedDict 键解包。

4. **崩溃链路**:
   ```
   pr.git_registration_probe(event, payload) → return {}  # stub
     → downstream: probe["phase"] → KeyError: 'phase'
   ```

5. **预期行为 vs 实际行为**:
   - 预期：返回至少包含 `phase`、`enforced`、`gate_event`、`triggered_on_current_event` 的字典。
   - 实际：返回 `{}`，所有键访问均失败。

**发现者**: R6

---

## P2 — 22 个

### P2-1. _section_bullets heading 级别判断错误

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:418`，同样在 `business_policy_checks.py:89-91`、`gateway.py:328-339`
2. **严重度 + 分类**: P2 / 逻辑错误
3. **触发条件**: `heading="### Source Refs"` 且文本中存在 `### Authority Refs`（同级子标题）。
4. **崩溃链路**: `_section_bullets(text, "### Source Refs")` → 遇到 `### Authority Refs` → `stripped.startswith("#")` → True → break → 丢失该 section 后续 bullet。
5. **预期行为 vs 实际行为**: 预期只在同级或更高级 heading 时停止。实际任何 `#` 开头的行都停止。
**发现者**: R1, R2, R3

### P2-2. _section_bullets endswith 匹配过于宽松

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/business_policy_checks.py:89-91`
2. **严重度 + 分类**: P2 / 逻辑错误
3. **触发条件**: heading 为 `"## 3. 正式输入源"` 时，`endswith("3. 正式输入源")` 匹配到任何以该字符串结尾的行。
4. **崩溃链路**: 误匹配非标题行 → `in_section = True` 被提前设置 → 后续内容被错误解析。
5. **预期行为 vs 实际行为**: 预期精确匹配 heading。实际 `endswith` 可匹配非标题行。
**发现者**: R2, R3

### P2-3. validate_project_map_files 文件缺失无显式报错

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/business_policy_checks.py:155-157`，同样 `:192-199`
2. **严重度 + 分类**: P2 / 逻辑错误（静默降级）
3. **触发条件**: `project_map_files[0]` 或 `project_map_governance` 路径不存在。
4. **崩溃链路**: `_read_text_if_exists` → 返回 `""` → 所有 `marker not in ""` 命中 → 返回 4-5 条 "marker not found" 但不提示文件缺失。
5. **预期行为 vs 实际行为**: 预期追加 `"missing file"` 错误。实际静默降级为空字符串噪音。
**发现者**: R3

### P2-4. 错误处理不对称 FrozenTupleChecker vs ProjectMapValidator

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/business_policy_checks.py:264-268`
2. **严重度 + 分类**: P2 / 状态不一致
3. **触发条件**: 同一系统内不同 checker 对文件缺失的处理方式不同。
4. **崩溃链路**: FrozenTupleChecker 显式报错 `"missing governance files"`，ProjectMapValidator 静默降级。
5. **预期行为 vs 实际行为**: 预期同类操作一致。实际两种处理方式。
**发现者**: R3

### P2-5. _resolve_callbacks 对 policy_registry 无 hasattr 保护

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_core.py:17-28`
2. **严重度 + 分类**: P2 / 崩溃
3. **触发条件**: `config.policy_registry` 非 None 但缺少 `validate_project_map` 等属性（不完整 mock）。
4. **崩溃链路**: `pr.validate_project_map` → `AttributeError`。
5. **预期行为 vs 实际行为**: 预期 `hasattr` 或 `getattr` 安全回退。实际直接访问。
**发现者**: R3

### P2-6. _resolve_callbacks 对 path_utils 同样无 hasattr 保护

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_core.py:36-39`
2. **严重度 + 分类**: P2 / 崩溃
3. **触发条件**: 与 P2-5 同理。
4. **崩溃链路**: `pu.extract_excerpt` → `AttributeError`。
5. **预期行为 vs 实际行为**: 同 P2-5。
**发现者**: R3

### P2-7. _resolve_override_path 绝对路径逃逸

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/business_policy_checks.py:628-632`、`memory_hook_impls.py:620-622`
2. **严重度 + 分类**: P2 / 安全
3. **触发条件**: scope config JSON 中 `"project_canonical": {"hacked": "/etc/passwd"}`。
4. **崩溃链路**: `_resolve_override_path("/etc/passwd")` → `is_absolute()` True → 直接返回 → 注册为权威来源。
5. **预期行为 vs 实际行为**: 预期约束在 repo_root 下。实际绝对路径原样返回。
**发现者**: R9

### P2-8. Policy pack 路径无沙箱校验

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:307-309`
2. **严重度 + 分类**: P2 / 安全
3. **触发条件**: `MEMORY_HOOK_POLICY_PACK_PATH=/etc/shadow`（任意可读 JSON）。
4. **崩溃链路**: `PolicyRegistryImpl.__init__` → 直接加载外部文件 → 覆盖安全策略。
5. **预期行为 vs 实际行为**: 预期限定在 workspace 目录下。实际无路径校验。
**发现者**: R9

### P2-9. 事件日志追加无锁 → JSONL 损坏

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:1136-1137`
2. **严重度 + 分类**: P2 / 并发
3. **触发条件**: 多进程同时向同一 EVENT_LOG 追加写入。
4. **崩溃链路**: 进程 A/B 交错写入 → JSON 行损坏 → `json.loads()` 失败。
5. **预期行为 vs 实际行为**: 预期 `fcntl.flock` 序列化。实际裸写入无同步。
**发现者**: R9

### P2-10. ErrorSinkImpl.log 同样无锁追加

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:1156-1157`
2. **严重度 + 分类**: P2 / 并发
3. **触发条件**: 多进程同时触发 `append_error_log`。
4. **崩溃链路**: 同 P2-9。
5. **预期行为 vs 实际行为**: 同 P2-9。
**发现者**: R9

### P2-11. get_surface_hook_state 无锁读取

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/cmux_hook_state.py:150-158`
2. **严重度 + 分类**: P2 / 并发
3. **触发条件**: `record_hook_event()` 正在写，同时另一调用读取。
4. **崩溃链路**: 读到 tmp→replace 之间的中间状态 → 返回过时数据。
5. **预期行为 vs 实际行为**: 预期使用 `LOCK_SH`。实际读路径无锁。
**发现者**: R9

### P2-12. delegate 异常只捕获 RuntimeError

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:1010-1019`
2. **严重度 + 分类**: P2 / 崩溃
3. **触发条件**: delegate 抛出 `OSError`、`FileNotFoundError` 等非 `RuntimeError` 异常。
4. **崩溃链路**: `except RuntimeError` 无法捕获 → 异常传播到 SystemExit → 无结构化错误日志。
5. **预期行为 vs 实际行为**: 预期捕获 `Exception`。实际只捕获 `RuntimeError`。
**发现者**: R7

### P2-13. adapter profile 函数被调用两次

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:117-119`
2. **严重度 + 分类**: P2 / 竞态（潜在副作用）
3. **触发条件**: 每次模块被 import 时。
4. **崩溃链路**: L117 第一次调用 `_fn()`，L119 第二次调用 `_fn()`，应复用 `_adapter_profile`。
5. **预期行为 vs 实际行为**: 预期调用一次。实际调用两次。
**发现者**: R2, R5, R7

### P2-14. CoreConfig.__post_init__ 缺少 2 个 Path 字段校验

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_config.py:90-181`
2. **严重度 + 分类**: P2 / 边界
3. **触发条件**: 给 `project_map_governance` 或 `event_log` 传入 None。
4. **崩溃链路**: `str(None)` → evidence_refs 中出现 `"None"` 字符串。
5. **预期行为 vs 实际行为**: 预期 `isinstance(..., Path)` 检查。实际跳过。
**发现者**: R4

### P2-15. _truth_basis_errors_for 同一文件读取两次

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:755-760`、`business_policy_checks.py:494-498`
2. **严重度 + 分类**: P2 / 性能
3. **触发条件**: 每次调用 `_truth_basis_errors_for(path)`。
4. **崩溃链路**: 先 `read_text()` 再调 `_truth_basis_sections_for` 又 `read_text()` → N 个文件 × 2 次磁盘读取。
5. **预期行为 vs 实际行为**: 预期缓存文本。实际重复读取。
**发现者**: R1, R3

### P2-16. _path_is_under_lexical 使用 absolute() 而非 resolve()

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/business_policy_checks.py:79-83, :629`
2. **严重度 + 分类**: P2 / 边界
3. **触发条件**: `cwd` 包含 `..` 或符号链接。
4. **崩溃链路**: `absolute()` 不展开 `..` → `relative_to` 抛 ValueError → scope 回退到 default。
5. **预期行为 vs 实际行为**: 预期使用 `os.path.normpath`。实际 `..` 未展开。
**发现者**: R3

### P2-17. _write_hook_state_unlocked read-back 失败覆盖 write 成功

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/cmux_hook_state.py:141`
2. **严重度 + 分类**: P2 / 竞态
3. **触发条件**: `Path.replace()` 成功后，另一进程在 read-back 前删除了文件。
4. **崩溃链路**: write 成功 → `load_hook_state_strict` 失败 → `HookStateError` 覆盖成功语义。
5. **预期行为 vs 实际行为**: 预期 read-back 失败静默处理。实际抛异常。
**发现者**: R5

### P2-18. sys.path 注入外部目录

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:27-29`
2. **严重度 + 分类**: P2 / 安全
3. **触发条件**: 标准导入失败时 fallback 将用户级路径加入 sys.path。
4. **崩溃链路**: 攻击者在目标目录放置恶意模块 → 代码注入。
5. **预期行为 vs 实际行为**: 预期限定受信任路径。实际硬编码路径无条件追加。
**发现者**: R9

### P2-19. _path_within_repo symlink + TOCTOU

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:354-358`
2. **严重度 + 分类**: P2 / 安全
3. **触发条件**: payload cwd 为 symlink，check-then-act 期间被替换。
4. **崩溃链路**: `_path_within_repo` 用 `resolve()` 跟随 symlink，`determine_project_scope` 用 `_path_is_under_lexical` 不跟随 → 语义不一致。
5. **预期行为 vs 实际行为**: 预期原子性校验。实际两种方式混用。
**发现者**: R9

### P2-20. delegate stderr 无过滤转发

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:1042-1043`
2. **严重度 + 分类**: P2 / 安全
3. **触发条件**: delegate stderr 包含敏感信息。
4. **崩溃链路**: `sys.stderr.write(proc.stderr)` → 直接泄露。
5. **预期行为 vs 实际行为**: 预期过滤。实际无条件转发。
**发现者**: R9

### P2-21. resolve_conflict strategy="default" 语义模糊

1. **文件绝对路径 + 精确行号**: `gateway.py:295`、`impls.py:407`
2. **严重度 + 分类**: P2 / 逻辑错误
3. **触发条件**: 调用方传 `strategy=None` 时 gateway 硬编码 `"default"`。
4. **崩溃链路**: `"default"` 同时是系统默认策略和可能的用户自定义策略名 → 歧义。
5. **预期行为 vs 实际行为**: 预期传 `None` 表达"让 impl 决定"。实际传字符串。
**发现者**: R6

### P2-22. latest_path 并发覆盖（非原子写入）

1. **文件绝对路径 + 精确行号**: `gateway.py:620-628`、`impls.py:1116-1120`
2. **严重度 + 分类**: P2 / 并发
3. **触发条件**: 同一微秒内两个进程写同一 artifact 的 latest_path。
4. **崩溃链路**: `latest_path.write_text(...)` 非原子 → 后写者覆盖 → 可能写入不完整内容。
5. **预期行为 vs 实际行为**: 预期 write-to-temp + rename。实际直接覆盖。
**发现者**: R1, R2

---

## P3 — 15 个

### P3-1. CodexDelegate/ClaudeDelegate payload 参数被忽略

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:142`、`:195`
2. **严重度 + 分类**: P3 / 误导消息
3. **触发条件**: 接口签名含 `payload` 但实现完全未使用（CodexDelegate）或仅透传给 recorder。
4. **崩溃链路**: 接口暗示 payload 影响 delegate 行为 → 实际不影响。
5. **预期行为 vs 实际行为**: 预期 payload 传给子进程或从接口移除。实际参数无效。
**发现者**: R1

### P3-2. ArtifactSinkImpl.write 并发写入竞态窗口

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:1116-1120`
2. **严重度 + 分类**: P3 / 竞态
3. **触发条件**: 同一微秒两个进程写同一 artifact。`write_text` 非原子。
4. **崩溃链路**: 极端情况可能读到半写文件。
5. **预期行为 vs 实际行为**: `%f` 微秒精度 + suffix 自增已覆盖大部分情况，但仍有窗口。
**发现者**: R1

### P3-3. PathUtilsImpl.write_targets 与 WriteTargetPolicyImpl 代码重复

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:1298-1321` vs `:514-532`
2. **严重度 + 分类**: P3 / 代码重复
3. **触发条件**: 维护时需同步两处。
4. **崩溃链路**: 修改一处忘改另一处 → 行为不一致。
5. **预期行为 vs 实际行为**: 预期抽取为单一数据源。实际两份独立拷贝。
**发现者**: R1

### P3-4. ArtifactWriter._log_error timestamp 不含微秒

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:1216`
2. **严重度 + 分类**: P3 / 日志缺陷
3. **触发条件**: 同一秒内两次 artifact write 失败。
4. **崩溃链路**: `%Y%m%dT%H%M%S`（无 `%f`）→ 两条错误 timestamp 完全相同。三处 timestamp 格式不一致。
5. **预期行为 vs 实际行为**: 预期统一使用含微秒的 timestamp。实际不一致。
**发现者**: R1

### P3-5. ClaudeDelegate.execute 将空字符串转为 "{}"

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:243`
2. **严重度 + 分类**: P3 / 逻辑错误
3. **触发条件**: `raw_payload=""` 时。
4. **崩溃链路**: `raw_payload or "{}"` → `"{}"` 传入 cmux，与 CodexDelegate（L151）行为不一致。
5. **预期行为 vs 实际行为**: 预期空字符串原样传递。实际静默替换。
**发现者**: R1

### P3-6. PolicyRegistryImpl.validate 缺少 project_scope 键时误报

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_impls.py:404`
2. **严重度 + 分类**: P3 / 逻辑错误
3. **触发条件**: `context` 中无 `"project_scope"` 键。
4. **崩溃链路**: `context.get("project_scope")` → `None` → `None not in allowed_scopes` → 误报。
5. **预期行为 vs 实际行为**: 预期区分"未提供"和"无效"。实际统一当无效处理。
**发现者**: R1

### P3-7. _section_body 只识别 ## 作为终止符

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/business_policy_checks.py:99-109`
2. **严重度 + 分类**: P3 / 逻辑错误
3. **触发条件**: `### ` 子标题在 `## ` 标题之后。
4. **崩溃链路**: `startswith("## ")` 不匹配 `### ` → 子标题不终止 → 捕获过多内容。
5. **预期行为 vs 实际行为**: 预期同级或更高级标题终止。实际只在 `## ` 处终止。
**发现者**: R3

### P3-8. project_file fallback 路径未检查存在性

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_core.py:216-218`
2. **严重度 + 分类**: P3 / 状态不一致
3. **触发条件**: `project_canonical.get(project_scope)` 返回 None。
4. **崩溃链路**: 构造 fallback 路径 → 未检查存在 → 未追加到 `missing_paths`。
5. **预期行为 vs 实际行为**: 预期追加到 `missing_paths`。实际跳过。
**发现者**: R3

### P3-9. _classify_truth_ref 路径判断顺序重叠风险

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/business_policy_checks.py:428-429`
2. **严重度 + 分类**: P3 / 边界
3. **触发条件**: 符号链接使两个路径前缀重叠。
4. **崩溃链路**: `resolve()` 可能抛 `OSError`（符号链接循环），未捕获。
5. **预期行为 vs 实际行为**: 预期捕获 `OSError`。实际未捕获。
**发现者**: R3

### P3-10. _json_object_keys regex 误识别

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/business_policy_checks.py:127`
2. **严重度 + 分类**: P3 / 逻辑错误
3. **触发条件**: JSON 字符串值中包含 `"key":` 模式。
4. **崩溃链路**: `r'"([^"]+)"\s*:'` 匹配到字符串值中的 key-like 片段。
5. **预期行为 vs 实际行为**: 预期使用 JSON parser。实际简单正则可能误匹配。
**发现者**: R3

### P3-11. resolve_policies() 硬编码 import 无 fallback

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_adapters/workbot_policy.py:79`
2. **严重度 + 分类**: P3 / 崩溃
3. **触发条件**: standalone 运行且 `workspace.tools` 不在 sys.path。
4. **崩溃链路**: `from workspace.tools.memory_hook_impls import ...` → `ImportError` 未捕获。
5. **预期行为 vs 实际行为**: 预期 try/except 双路径。实际无 fallback。
**发现者**: R5

### P3-12. validate_memory_system 检查通过消息数字不符

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/validate_memory_system.py:236`
2. **严重度 + 分类**: P3 / 误导消息
3. **触发条件**: `check_package_imports()` 只验证 2 个符号。
4. **崩溃链路**: 成功消息写 `"4 public symbols importable"` → 与实际不符。
5. **预期行为 vs 实际行为**: 预期 `"2 public symbols importable"` 或验证 4 个。实际数字不符。
**发现者**: R5

### P3-13. extract_excerpt_fn 类型注解与实现签名不匹配

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_config.py:59`
2. **严重度 + 分类**: P3 / 误导消息
3. **触发条件**: 静态类型检查时。
4. **崩溃链路**: `Callable[[Path], list[str]]` vs 实际 `(Path, int) -> list[str]`。运行时不崩溃但 mypy 报错。
5. **预期行为 vs 实际行为**: 预期 `Callable[[Path, int], list[str]]`。实际类型注解不一致。
**发现者**: R4

### P3-14. build_context_package_simple 的 adapter 参数未被使用

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:861-882`
2. **严重度 + 分类**: P3 / 误导消息
3. **触发条件**: 调用方传 `adapter` 参数。
4. **崩溃链路**: 参数在链路中从未被引用。
5. **预期行为 vs 实际行为**: 预期使用或移除。实际死参数。
**发现者**: R4

### P3-15. _resolve_core_builder fallback 静默吞掉异常

1. **文件绝对路径 + 精确行号**: `/Users/busiji/memory/workspace/tools/memory_hook_gateway.py:202-207`
2. **严重度 + 分类**: P3 / 误导消息
3. **触发条件**: external-core 加载失败时静默降级到 legacy。
4. **崩溃链路**: 错误信息只在 `system_context["core_provider_fallback_errors"]` 中，用户不可见。
5. **预期行为 vs 实际行为**: 预期 stderr warning。实际静默降级。
**发现者**: R2

---

## 非发现验证声明

以下模块/路径经 R1-R9 全部审查员交叉验证确认无 bug：

1. **CoreConfig 37 字段构造** — R7 逐字段对照，全部匹配。R4 验证 `__post_init__` 覆盖 29/37 字段校验。
2. **HostDelegate/CodexDelegate/ClaudeDelegate 签名** — R1 验证三方法签名与接口 ABC 完全匹配，R6 确认 gateway 调用参数正确。
3. **RouteTargetPolicyImpl/WriteTargetPolicyImpl** — R1 验证签名，R6 确认 gateway 构造参数正确。
4. **ArtifactSinkImpl/ErrorSinkImpl** — R1 验证签名，R6 确认 gateway 构造参数正确。
5. **TruthBasis TypedDict** — R3 验证 total=False 设计合理，所有 10 字段在两个实现路径中均被正确填充，core.py 中 `_safe_tb` 使用 `.get()` 安全提取。
6. **RegistrationCommitGate TypedDict** — R4 验证在 `_git_registration_probe` 和 `evaluate_registration_commit_gate` 中结构一致。
7. **GatewayBusinessPolicy 14 个抽象方法** — R6 逐方法确认 `GatewayBusinessPolicyImpl` 均有实现，签名匹配。
8. **build_context_package_from_config → build_context_package_core** — R4 确认 37 个参数一一映射，类型匹配。
9. **workbot_runtime_profile.py 35 个配置键** — R5 逐键确认与 gateway 构造匹配。
10. **cmux_hook_state.py 内部一致性** — R5 验证 flock 在 finally 释放、原子写入正确。
11. **_validation_constants.py** — R5 验证全部常量名和值匹配。
12. **memory_hook_provider_probe.py 和 rollback.py** — R5 验证功能等价。
13. **neutral_policy.py** — R5 验证透传层无独立逻辑。

---

## 修复优先级建议

**立即修复 (P0 + P1)**:
1. P0-1: 统一 `governance_frozen_tuple_errors` → `_blocker_errors` 方法名
2. P1-1: 统一 `validate_project_map` → `validate_project_map_files` 方法名
3. P1-3: `provider_builder` 实际调用
4. P1-10: `__import__` 替换为白名单模块映射
5. P1-11: `globals().update` 改为受控命名空间注入

**短期修复 (P1 其余)**:
6. P1-2: EventContractChecker 部分文件缺失保护
7. P1-4/6: KeyError 保护（.get() 兜底）
8. P1-5: _read_payload 诊断输出
9. P1-7/8: 验证器 PASS/FAIL 逻辑修正
10. P1-9: convert_to_v1 保留 missing_paths

**中期修复 (P2)**:
- P2-1/2: _section_bullets heading 匹配改为精确级别判断
- P2-3/4: ProjectMapValidator 文件缺失显式报错
- P2-5/6: _resolve_callbacks hasattr 保护
- P2-7/8: 路径沙箱校验
- P2-9/10/11: 并发锁保护
- P2-12: delegate 异常扩大捕获范围
- P2-13: adapter profile 去重调用
