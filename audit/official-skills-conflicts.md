# 官方 Skills 冲突清单（仅官方视角）
> 生成时间: 2026-05-30
> 视角：仅关注官方内置 skill 的冲突

## 冲突总览

| 指标 | 数值 |
|------|------|
| 涉及官方 skill 的冲突 | 10 |
| 官方 × 官方 | 4 |
| 官方 × 个人（重名覆盖） | 4 |
| 官方 × 第三方 | 2 |

## 冲突明细

### 官方 × 官方（4 条）

| # | 官方 Skill A | 官方 Skill B | 重叠关键词 | 处理状态 |
|---|-------------|-------------|-----------|---------|
| OF-01 | O-018 review | O-021 simplify | review code、quality | ✅ 已中英覆盖 |
| OF-02 | O-019 security-review | O-007 deep-security-review | security review、audit | ✅ 已中英覆盖 |
| OF-03 | O-001 agent-browser | O-028 webapp-testing | browser、testing、screenshot | ✅ 已中英覆盖 |
| OF-04 | O-003 browse-wiki | O-011 wiki | wiki、文档 | ✅ 已中英覆盖 |

### 官方 × 个人重名（4 条）

| # | 官方 Skill | 个人 Skill（同名覆盖） | 处理状态 |
|---|-----------|---------------------|---------|
| OF-05 | O-018 review | ~/.factory/skills/review | ✅ 中英双语覆盖 |
| OF-06 | O-016 pdf → docx 同类 | U-009 docx | ✅ 中英双语覆盖 |
| OF-07 | O-011 wiki | U-019 wiki | ✅ 中英双语覆盖 |
| OF-08 | O-003 browse-wiki | U-019 wiki（重叠） | ✅ 中英双语覆盖 |

### 官方 × 第三方（2 条）

| # | 官方 Skill | 第三方 Skill | 重叠关键词 | 处理状态 |
|---|-----------|-------------|-----------|---------|
| OF-09 | O-018 review | X-005 code-review-specialist | review code、PR | ⚠️ 无法删除第三方 |
| OF-10 | O-027 web-artifacts-builder | X-011 frontend-design | React、frontend | ⚠️ 无法删除第三方 |

## 处理汇总

| 处理方式 | 数量 | 说明 |
|----------|------|------|
| ✅ 中英双语覆盖 | 8 | 已创建本地同名 skill |
| ⚠️ 第三方冲突 | 2 | 来自插件，无法删除 |
| 官方间冲突（已覆盖） | 4 | review/simplify, security, browser, wiki |
