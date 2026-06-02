# 用户自定义 Skills 编号建档
> 生成时间: 2026-05-30
> 总数: 45
> 来源: ~/.factory/skills/ (19 实体目录 + 25 符号链接) + /Users/busiji/memory/.factory/skills/ (1 项目级)

| 编号 | Skill Name | 分类 | 来源 | Description |
|------|-----------|------|------|------------|
| U-001 | 1password-secret-resolver | 安全凭证 | 个人 | 当需要密码、API key、token、凭证、secret 等敏感信息时，优先使用 1password-connect MCP 工具查找。 |
| U-002 | apisix-gateway | 基础设施 | 个人 | APISIX 网关维护：路由管理、插件配置、Stream 服务、消费者管理。 |
| U-003 | backend-services | 基础设施 | 个人 | 后端服务入口认知：所有后端服务必须通过 APISIX 网关 (192.168.88.11) 访问。 |
| U-004 | cf-ip-optimizer | 网络工具 | 个人 | Cloudflare Worker 优选 IP 管理、订阅节点 IP 列表更新、CF IP 连通性测试。 |
| U-005 | doc-constitution | 文档治理 | 个人 | 文档治理核心规则。3 条铁律：权威源、安全子集、同步方向。 |
| U-006 | doc-governance | 文档治理 | 个人 | 文档治理：版本号同步、发布清单、一致性检查。 |
| U-007 | doc-management | 文档治理 | 个人 | 全局文档管理技能（已拆分为 doc-governance + showdoc-platform-rules + doc-sync-policy）。 |
| U-008 | doc-sync-policy | 文档治理 | 个人 | 跨平台文档同步策略：Git→ShowDoc→飞书单向数据流、格式转换规则、失败处理。 |
| U-009 | docx | 文档工具 | 个人 | 本地 Word (.docx) 文档操作：创建、读取、编辑、格式化 .docx 文件。 |
| U-010 | feishu-platform-rules | 飞书通讯 | 个人 | 飞书文档操作规则：lark-cli docs 命令集、知识空间管理、文档创建/更新模式、认证检查。 |
| U-011 | internal-service-rules | 文档治理 | 个人 | 内部服务规则：约束内部 skill 只能被编排器调用，不能直接暴露给用户。 |
| U-012 | showdoc-feishu-sync | 文档治理 | 个人 | ShowDoc 与飞书文档同步：跨平台文档一致性扫描和同步。 |
| U-013 | showdoc-markdown-compat | 文档治理 | 个人 | ShowDoc↔飞书 Markdown 安全子集（19项，实测确认）。 |
| U-014 | showdoc-platform-rules | 文档治理 | 个人 | ShowDoc 平台操作规则：MCP 路由表、API/数据字典模板、RunApi/看板规则、写入后验证。 |
| U-015 | skill-droid-collab-chain | 架构设计 | 个人 | Skill 与 Droid 的协作链：定义 Skill 如何编排 Droid 执行任务。 |
| U-016 | skill-isolation-architecture | 架构设计 | 个人 | Skill 隔离架构设计：定义 skill 的访问控制和隔离规则（3-Layer Gateway Pattern）。 |
| U-017 | skills-tree | 架构设计 | 个人 | Skill 树结构和层级关系：维护 skill 的层级和依赖关系。 |
| U-018 | ssh-server-manager | 服务器管理 | 个人 | SSH 服务器管理：1Password SSH Agent + ~/.ssh/config + Ansible 三层架构。 |
| U-019 | wiki | 文档工具 | 个人 | 为仓库生成 Factory Wiki 文档。 |
| U-020 | lark-approval | 飞书通讯 | lark-cli符号链接 | 飞书审批 API：审批实例、审批任务管理。 |
| U-021 | lark-apps | 飞书通讯 | lark-cli符号链接 | 把本地 HTML 文件或目录部署到飞书妙搭（Miaoda），生成公网可访问的应用链接。 |
| U-022 | lark-attendance | 飞书通讯 | lark-cli符号链接 | 飞书考勤打卡：查询自己的考勤打卡记录。 |
| U-023 | lark-base | 飞书通讯 | lark-cli符号链接 | 飞书多维表格（Base）操作：搜索 Base、建表、字段管理、记录读写、视图配置。 |
| U-024 | lark-calendar | 飞书通讯 | lark-cli符号链接 | 飞书日历：日历与日程管理、参会人管理、忙闲查询、会议室预定。 |
| U-025 | lark-contact | 飞书通讯 | lark-cli符号链接 | 飞书通讯录：按姓名/邮箱解析 open_id，按 open_id 反查员工信息。 |
| U-026 | lark-doc | 飞书通讯 | lark-cli符号链接 | 飞书云文档/Docx/知识库 Wiki 文档（v2）：创建、读取、编辑飞书文档内容。 |
| U-027 | lark-drive | 飞书通讯 | lark-cli符号链接 | 飞书云空间（云盘/云存储）：文件上传下载、文件夹管理、文档权限、本地文件导入。 |
| U-028 | lark-event | 飞书通讯 | lark-cli符号链接 | 飞书实时事件监听/订阅/消费：流式 NDJSON 事件消费。 |
| U-029 | lark-im | 飞书通讯 | lark-cli符号链接 | 飞书即时通讯：收发消息和管理群聊、搜索聊天记录、管理群成员。 |
| U-030 | lark-mail | 飞书通讯 | lark-cli符号链接 | 飞书邮箱：起草/发送/回复/转发/搜索邮件、管理草稿/文件夹/标签/附件。 |
| U-031 | lark-markdown | 飞书通讯 | lark-cli符号链接 | 飞书 Markdown：查看、创建、上传、编辑和比较 Markdown 文件。 |
| U-032 | lark-minutes | 飞书通讯 | lark-cli符号链接 | 飞书妙记：妙记列表查询、AI 产物获取、音视频上传生成妙记、说话人替换。 |
| U-033 | lark-okr | 飞书通讯 | lark-cli符号链接 | 飞书 OKR：管理目标与关键结果、对齐关系、量化指标和进展记录。 |
| U-034 | lark-openapi-explorer | 飞书通讯 | lark-cli符号链接 | 飞书原生 OpenAPI 探索：从官方文档库挖掘未经 CLI 封装的原生 OpenAPI 接口。 |
| U-035 | lark-shared | 飞书通讯 | lark-cli符号链接 | lark-cli 共享规则：认证登录、身份切换、权限错误处理、更新 lark-cli。 |
| U-036 | lark-sheets | 飞书通讯 | lark-cli符号链接 | 飞书电子表格：创建/管理工作表、读写单元格、追加行数据、导出文件。 |
| U-037 | lark-skill-maker | 飞书通讯 | lark-cli符号链接 | 创建 lark-cli 的自定义 Skill：封装飞书 API 操作为可复用 Skill。 |
| U-038 | lark-slides | 飞书通讯 | lark-cli符号链接 | 飞书幻灯片：创建和编辑幻灯片，XML 协议通信。 |
| U-039 | lark-task | 飞书通讯 | lark-cli符号链接 | 飞书任务：创建/更新任务、拆分子任务、管理清单、分配协作成员。 |
| U-040 | lark-vc | 飞书通讯 | lark-cli符号链接 | 飞书视频会议（历史）：搜索历史会议、查询纪要产物、参会人快照。 |
| U-041 | lark-vc-agent | 飞书通讯 | lark-cli符号链接 | 飞书视频会议（实时）：代用户入会/离会、读取会议实时事件。 |
| U-042 | lark-whiteboard | 飞书通讯 | lark-cli符号链接 | 飞书画板：查询和编辑画板、DSL/PlantUML/Mermaid 格式更新画板内容。 |
| U-043 | lark-wiki | 飞书通讯 | lark-cli符号链接 | 飞书知识库：管理知识空间、空间成员和文档节点。 |
| U-044 | lark-workflow-meeting-summary | 飞书通讯 | lark-cli符号链接 | 会议纪要整理工作流：汇总指定时间范围内的会议纪要并生成结构化报告。 |
| U-045 | lark-workflow-standup-report | 飞书通讯 | lark-cli符号链接 | 日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成日程与任务摘要。 |

---

## 项目级 Skills

| 编号 | Skill Name | 分类 | 来源 | Description |
|------|-----------|------|------|------------|
| P-001 | memory-core-development | 项目开发 | 项目级 | memory-core 库开发指南：CLI 工具、Hook Gateway、所有权模型、项目记忆生命周期。 |

---

## 分类统计

| 分类 | 数量 | 编号 |
|------|------|------|
| 飞书通讯 | 26 | U-010, U-020 ~ U-045 |
| 文档治理 | 7 | U-005 ~ U-008, U-011 ~ U-014 |
| 文档工具 | 2 | U-009, U-019 |
| 架构设计 | 3 | U-015 ~ U-017 |
| 基础设施 | 2 | U-002, U-003 |
| 安全凭证 | 1 | U-001 |
| 服务器管理 | 1 | U-018 |
| 网络工具 | 1 | U-004 |
| 项目开发 | 1 | P-001 |
| **合计** | **45** | |

---

## 来源统计

| 来源 | 数量 |
|------|------|
| 个人 (~/.factory/skills/ 实体目录) | 19 |
| lark-cli 符号链接 (→ ~/.agents/skills/) | 25 |
| 项目级 (/Users/busiji/memory/.factory/skills/) | 1 |
| **合计** | **45** |

---

## 用户可调用性统计

| 状态 | 数量 | 说明 |
|------|------|------|
| user-invocable: true | 15 | 用户可直接触发 |
| user-invocable: false | 4 | 仅内部调用 (apisix-gateway, internal-service-rules, skill-droid-collab-chain, skill-isolation-architecture, skills-tree) |
| 未声明 (lark-*) | 25 | lark-cli 符号链接，默认可调用 |
| 项目级 | 1 | memory-core-development |

---

## 备注

- lark-* 符号链接指向 `~/.agents/skills/` 下的 lark-cli 安装目录
- doc-management (U-007) 已拆分为 3 个独立 skill，保留用于向后兼容
- internal-service-rules (U-011) 定义了 lark-doc/lark-wiki/lark-drive/wiki/docx 的访问控制约束
- apisix-gateway (U-002) 设为 `disable-model-invocation: true`，仅由 backend-services 升级引导触发
