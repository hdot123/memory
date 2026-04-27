## Bug #1: Policy pack generation can crash when the default conflict strategy is absent
- 文件: impls.py
- 行号: L374-L380
- 严重度: P2 (edge case)
- 触发条件: 调用 `PolicyRegistryImpl(conflict_strategies=...)` 时传入的字典不包含 `"default"`，或动态 policy pack/测试注入让 `_conflict_strategies` 没有 `"default"`，随后调用 `get_policy_pack(scope)`。
- 预期行为: 返回 policy pack，或对缺失的默认策略给出受控的校验错误/回退策略。
- 实际行为: `self._conflict_strategies["default"]` 直接索引缺失键，抛出 `KeyError`，导致调用方崩溃。

## Bug #2: Conflict resolution can crash for unknown policy keys when the default strategy is absent
- 文件: impls.py
- 行号: L407-L409
- 严重度: P2 (edge case)
- 触发条件: `_conflict_strategies` 不包含 `"default"`，调用 `resolve_conflict(policy_key, values, strategy)` 时 `strategy` 为空字符串/假值，且 `policy_key` 不在 `_conflict_strategies` 中。
- 预期行为: 使用受控回退策略，或返回明确的 `ValueError` 表示策略配置无效。
- 实际行为: `self._conflict_strategies["default"]` 在 `dict.get()` 默认参数求值时先触发 `KeyError`，调用方拿不到声明的冲突解析错误。

## Bug #3: Project-map validation assumes at least three project map files
- 文件: impls.py
- 行号: L839-L841
- 严重度: P2 (edge case)
- 触发条件: `GatewayBusinessPolicyConfig.project_map_files` 少于 3 个元素时调用 `validate_project_map_files()`，例如配置遗漏了 `legal-core-map.md` 或 `ingestion-registry-map.md`。
- 预期行为: 返回校验错误，指出缺少必需的 project-map 文件配置。
- 实际行为: 直接访问 `cfg.project_map_files[0]`、`[1]`、`[2]`，列表长度不足时抛出 `IndexError`，整个校验流程崩溃。

## Bug #4: Unique legal-system validation assumes project_map_files has required indexes
- 文件: impls.py
- 行号: L877-L883
- 严重度: P2 (edge case)
- 触发条件: `GatewayBusinessPolicyConfig.project_map_files` 少于 3 个元素时调用 `validate_unique_legal_system_contract()`。
- 预期行为: 返回校验错误，说明缺少用于读取 legal-core 或 ingestion-registry 的 project-map 文件配置。
- 实际行为: 直接读取 `cfg.project_map_files[1]` 和 `cfg.project_map_files[2]`，配置长度不足时抛出 `IndexError`，后续契约校验无法执行。

## Bug #5: Event contract validation crashes when required map keys are absent
- 文件: impls.py
- 行号: L947-L959
- 严重度: P2 (edge case)
- 触发条件: `GatewayBusinessPolicyConfig.event_contract_files` 字典缺少 `"upstream_standard"`、`"upstream_mapping"`、`"formal_contract"`、`"upstream_samples"` 或 `"downstream_samples"` 中任意一个键，但已提供的文件都存在。
- 预期行为: 返回校验错误，指出缺少必需的 event contract 配置项。
- 实际行为: 缺失键不会进入 `missing_files`，随后 `texts["..."]` 直接索引缺失键并抛出 `KeyError`。

## Bug #6: Artifact sink can partially write artifacts and then fail when event log directory is missing
- 文件: impls.py
- 行号: L1114-L1137
- 严重度: P1 (wrong result)
- 触发条件: `ArtifactSinkImpl` 使用的 `event_log` 位于不存在的目录中，且调用 `write(package)`；例如直接构造 `ArtifactSinkImpl(context_root, Path("missing/events.jsonl"))`。
- 预期行为: 写入前确保 snapshot、latest 和 event log 的父目录都存在，或在写入任何 artifact 前以受控方式失败。
- 实际行为: `ensure_dirs()` 只创建 `_context_root`，先成功写入 snapshot/latest，然后 `self._event_log.open("a")` 因父目录不存在抛出 `FileNotFoundError`，留下部分写入的 artifact，调用方收到失败但磁盘状态已被改变。
