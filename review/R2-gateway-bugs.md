## Bug #1: Requested external core provider is ignored
- 文件: gateway.py
- 行号: L818-L820
- 严重度: P1
- 触发条件: 设置 `MEMORY_HOOK_CORE_PROVIDER=external-core`，并通过 `MEMORY_HOOK_EXTERNAL_CORE_MODULE` / `MEMORY_HOOK_EXTERNAL_CORE_FUNC` 指向一个可加载的外部 core builder。
- 预期行为: `_resolve_core_builder()` 返回的 `provider_builder` 应该被用于构建 context package，使请求的 external-core 路径真正生效。
- 实际行为: 代码解析并保存了 `provider_builder`，但随后固定调用 `build_context_package_from_config(config)`；external-core builder 从未被调用，产物仍由 legacy/config builder 生成，同时 `system_context["core_provider"]` 被标记为 `external-core`，产生错误的 provider 状态。

## Bug #2: Shadow run compares the same builder instead of the alternate provider
- 文件: gateway.py
- 行号: L836-L846
- 严重度: P2
- 触发条件: 设置 `MEMORY_HOOK_SHADOW_RUN=1`，并让当前 provider 与 shadow provider 可分别解析到不同 builder。
- 预期行为: shadow run 应调用 L840 解析出的 `shadow_builder`，用 alternate provider 构建 shadow package，才能比较当前 provider 和备用 provider 的结果。
- 实际行为: `shadow_builder` 被解析后没有使用；L841 仍固定调用 `build_context_package_from_config(config)`，因此 shadow 结果来自同一条 legacy/config 构建路径，无法检测 alternate provider 的异常或结果差异。

## Bug #3: Adapter config fallback order lets stale globals override newer adapter config
- 文件: gateway.py
- 行号: L103-L119, L178-L179, L756-L760
- 严重度: P1
- 触发条件: 运行时调用 `load_adapter_config(new_profile)` 或测试/宿主重新注入 `_adapter_config`，且模块 globals 中已存在旧的 `GATEWAY_POLICY_CLASS` 或 `ARTIFACT_COMPACTION` 值。
- 预期行为: 新加载的 `_adapter_config` 应作为当前 adapter 配置来源；legacy globals 只应在 `_adapter_config` 缺失对应键时作为兼容 fallback。
- 实际行为: `_build_gateway_business_policy()` 和 `_apply_artifact_compaction()` 都先读取 `globals()`，再读取 `_adapter_config`。旧 global 值会压过新 adapter config，导致策略类或 artifact compaction 使用过期配置。

## Bug #4: Unknown MEMORY_HOOK_ADAPTER crashes at import time
- 文件: gateway.py
- 行号: L87-L93
- 严重度: P2
- 触发条件: 环境变量 `MEMORY_HOOK_ADAPTER` 被设置为未注册名称，例如 `nonexistent_adapter_xyz`。
- 预期行为: gateway 应将未知 adapter 当作配置错误处理，至少回退到默认 adapter 或输出受控错误。
- 实际行为: L92 直接索引 `_ADAPTER_REGISTRY[_ADAPTER_NAME]`，未处理 `KeyError`；模块导入阶段即崩溃，`main()` 无法进入，也不会写入 gateway 错误日志。

## Bug #5: Delegate subprocess OS errors are not caught by main()
- 文件: gateway.py
- 行号: L1010-L1019
- 严重度: P2
- 触发条件: delegate preflight 通过后，`subprocess.run()` 本身抛出 `OSError` / `FileNotFoundError` / `PermissionError`，例如 `cmux` 在 `shutil.which()` 检查后被移除、不可执行，或执行时发生 OS 级错误。
- 预期行为: gateway 应像处理 `RuntimeError` 一样记录 delegate 执行失败并返回非零退出码。
- 实际行为: `main()` 只捕获 `RuntimeError`。`subprocess.run()` 抛出的 OS 级异常不会被捕获，进程会带 traceback 崩溃，无法写入预期的 gateway 错误上下文。
