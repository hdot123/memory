# Skills 冲突清单
> 生成时间: 2026-05-30
> 对比: audit/official-skills-registry.md (O-001~O-030) vs audit/user-skills-registry.md (U-001~U-045)

## 冲突总览

| 指标 | 数值 |
|------|------|
| 冲突总数 | 18 |
| 🔴 HIGH（关键词高度重叠/重名） | 9 |
| 🟡 MEDIUM（边界模糊） | 9 |

---

## 冲突明细

### 🔴 HIGH 冲突（9 条）

| # | 分类 | Skill A | Skill B | 重叠关键词 | 来源 |
|---|------|---------|---------|-----------|------|
| C-01 | 文档治理 | U-007 doc-management | U-005 doc-constitution | 文档治理、文档合规 | 个人 × 个人 |
| C-02 | 文档治理 | U-007 doc-management | U-006 doc-governance | 文档治理、一致性检查 | 个人 × 个人 |
| C-03 | 文档治理 | U-005 doc-constitution | U-006 doc-governance | 文档治理 | 个人 × 个人 |
| C-04 | 文档治理 | U-008 doc-sync-policy | U-012 showdoc-feishu-sync | 文档同步、跨平台同步 | 个人 × 个人 |
| C-05 | ShowDoc同步 | U-012 showdoc-feishu-sync | U-013 showdoc-markdown-compat | 文档同步、ShowDoc→飞书 | 个人 × 个人 |
| C-06 | 飞书文档 | U-026 lark-doc | U-043 lark-wiki | /wiki/ URL、飞书文档 | lark × lark |
| C-07 | 飞书文档 | U-026 lark-doc | U-010 feishu-platform-rules | 飞书文档、lark-cli docs | lark × 个人 |
| C-08 | Word文档(重名) | U-009 docx (个人) | O-030 docx (官方) | .docx、Word文档、创建文档 | 个人 × 官方 |
| C-09 | Wiki(重名) | U-019 wiki (个人) | O-011 wiki (官方) | wiki、生成文档 | 个人 × 官方 |

### 🟡 MEDIUM 冲突（9 条）

| # | 分类 | Skill A | Skill B | 重叠关键词 | 来源 |
|---|------|---------|---------|-----------|------|
| C-10 | ShowDoc同步 | U-014 showdoc-platform-rules | U-013 showdoc-markdown-compat | ShowDoc | 个人 × 个人 |
| C-11 | Wiki(重名) | U-019 wiki (个人) | O-003 browse-wiki (官方) | wiki、文档 | 个人 × 官方 |
| C-12 | 代码Review | O-018 review (官方) | 第三方 code-review-specialist | review code、PR review | 官方 × 第三方 |
| C-13 | 代码Review | O-018 review (官方) | O-021 simplify (官方) | review code、quality | 官方 × 官方 |
| C-14 | 会议纪要 | U-040 lark-vc | U-044 lark-workflow-meeting-summary | 会议纪要 | lark × 个人 |
| C-15 | 后端服务 | U-003 backend-services | U-011 internal-service-rules | 后端服务、路由 | 个人 × 个人 |
| C-16 | 前端UI | 第三方 frontend-design | 第三方 web-artifacts-builder | React、HTML、frontend | 第三方 × 第三方 |
| C-17 | 安全审计 | O-019 security-review (官方) | O-007 deep-security-review (官方) | security review、audit | 官方 × 官方 |
| C-18 | 浏览器自动化 | O-001 agent-browser (官方) | 第三方 webapp-testing | browser、testing、screenshot | 官方 × 第三方 |

---

## 解决方案

### 方案 A：中英双语 description 覆盖（针对官方 skill）

在 `~/.factory/skills/` 下创建同名 skill，description 写中英双语：
- 影响范围：C-08(docx), C-09(wiki), C-11(browse-wiki), C-12(review), C-13(simplify), C-17(security-review), C-18(agent-browser)
- 不动官方文件，只添加本地覆盖

### 方案 B：description 精确化（针对用户 skill 间冲突）

修改用户 skill 的 description，消除歧义关键词：
- 影响范围：C-01~C-06, C-10, C-14, C-15
- 需要重写 description 的 skill：doc-management(删除), doc-constitution, doc-governance, doc-sync-policy, showdoc-feishu-sync, showdoc-markdown-compat, feishu-platform-rules, lark-vc, backend-services

### 方案 C：废弃冗余 skill

- U-007 doc-management → 已拆分，建议删除
- 第三方越南语 skill → 建议评估是否保留
