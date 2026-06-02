# 官方内置 Skills 编号存档
> 生成时间: 2026-05-30
> 总数: 30
> 来源: Factory Droid system-reminder Available skills 列表
> 排除规则: lark-* (26) + 个人 skill (15) + 第三方/越南语 (11) + 占位符 (4) = 56 已排除

## 官方内置 Skill 清单

| 编号 | Skill Name | 分类 | Description (英文原文) |
|------|-----------|------|----------------------|
| O-001 | agent-browser | 浏览器自动化 | Automates browsers and Electron desktop apps (VS Code, Slack, Discord, Figma, Notion, Spotify, etc.) for testing, form filling, screenshots, and data extraction. Use when the user needs to navigate, interact with, test, or extract data from any website or Electron desktop app. |
| O-002 | antigravity | 开发工具 | How to automate Antigravity using OpenCLI. Use when you want to send prompts, read replies, extract code, switch models, stream updates, or expose Antigravity through an Anthropic-compatible local proxy. |
| O-003 | browse-wiki | 文档/知识管理 | Search and read wiki documentation for a repository. |
| O-004 | claude-api | 开发工具 | Build apps with the Claude API or Anthropic SDK. TRIGGER when: code imports `anthropic`/`@anthropic-ai/sdk`/`claude_agent_sdk`, or user asks to use Claude API, Anthropic SDKs, or Agent SDK. DO NOT TRIGGER when: code imports `openai`/other AI SDKs, general programming, or ML/data-science tasks. |
| O-005 | cmux | 开发工具 | Build and operate a cmux-native multi-agent runtime on macOS. Use when the user wants to create or reconcile a formal cmux workspace, split panes, label primary terminal surfaces, launch Claude/Codex inside those surfaces, inspect or continue blocked runs, or use browser surfaces as auxiliary panels without falling back to tmux semantics. |
| O-006 | cross-project-adapter-migration | 开发工具 | Cross-project CLI command migration workflow for opencli. Use when importing commands from external CLI projects (python/node) like rdt-cli, twitter-cli, etc. Covers: source analysis → gap matrix → batch migration → README/SKILL.md update. |
| O-007 | deep-security-review | 安全审查 | Correctness-first, depth-first security audit of a single repository. Invoked by /security-review when the user opts into "thorough" mode. Uses a heterogeneous multi-model jury (latest Opus + latest GPT + latest Gemini). A mandatory 3-pass floor runs against every Pass 0 lieutenant-seeded candidate; a conditional escalation tier fires on per-finding triggers. Produces FINDINGS.md, JUDGE.md, STATUS.md, severity-sorted master list, and optional PoC + evidence artifacts for that repo. Never uploads or submits anything; all outputs local. |
| O-008 | doc-coauthoring | 文档/知识管理 | Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This workflow helps users efficiently transfer context, refine content through iteration, and verify the doc works for readers. Trigger when user mentions writing docs, creating proposals, drafting specs, or similar documentation tasks. |
| O-009 | figma-mcp-helper | 前端/UI | Promote and assist with Figma MCP integration. ACTIVATE when the user shares a Figma URL (figma.com), mentions Figma designs or components, shares PNG images that may originate from Figma, or when Figma MCP tools are already connected and being used. Handles installation encouragement, conversational promotion, and push-back-to-Figma flows. |
| O-010 | incident | 运维/故障排查 | RCA runbook for alerts. Given an alert link (or prompted to provide one), identifies the alert type, verifies tooling/auth, and walks through root cause analysis using deep research. Persists learnings to incident-guidelines for future reuse. |
| O-011 | install-code-review | 代码审查 | Install and configure Factory Droid for automated code review on GitHub or GitLab. Supports single-repo setup or org/group-wide rollout across hundreds of repos. Use when a user wants to set up Droid review on their repositories. |
| O-012 | install-qa | 测试/质量 | Set up automated QA testing for this project. Performs deep codebase analysis, asks targeted questions, and generates a modular QA skill with sub-skills per app, a GitHub Actions workflow, and a report template. This is a complex, multi-phase process -- quality assurance is foundational and we take the time to get it right. |
| O-013 | install-wiki | 文档/知识管理 | Install a CI action that automatically refreshes the Factory Wiki on each push to the default branch. Use when the user wants to set up automated wiki generation, install wiki CI, or configure wiki refresh. |
| O-014 | internal-comms | 通讯/协作 | A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.). |
| O-015 | mcp-builder | 开发工具 | Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK). |
| O-016 | pdf | 文档/知识管理 | Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rotating pages, adding watermarks, creating new PDFs, filling PDF forms, encrypting/decrypting PDFs, extracting images, and OCR on scanned PDFs to make them searchable. |
| O-017 | pptx | 文档/知识管理 | Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file; editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates, layouts, speaker notes, or comments. |
| O-018 | review | 代码审查 | Review code changes and identify high-confidence, actionable bugs. Use when the user wants to: Review a pull request or branch diff, Find bugs, security issues, or correctness problems in code changes, Get a structured summary of review findings. |
| O-019 | security-review | 安全审查 | Security-focused code review using STRIDE, OWASP Top 10, OWASP LLM Top 10, and supply chain analysis. Use when: Reviewing a PR for security vulnerabilities, Performing a security audit of code changes, Identifying injection, auth, data exposure, and other security issues, Running a full-project security audit reviewing every source file. |
| O-020 | session-navigation | 会话管理 | Navigate, search, and manage Droid sessions. Use when the user wants to: List recent sessions, Search session history for specific topics or patterns, Resume a previous session, Get details about what was accomplished in a session, Find sessions by project, date, or content. |
| O-021 | simplify | 代码审查 | Review changed code for reuse, quality, and efficiency, then fix any issues found. |
| O-022 | skill-creator | 开发工具 | Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy. |
| O-023 | slack-gif-creator | 前端/UI | Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack. |
| O-024 | theme-factory | 前端/UI | Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact that has been creating, or can generate a new theme on-the-fly. |
| O-025 | tuistory | 测试/质量 | Automates terminal user interface (TUI) testing. Use when you need to launch, interact with, test, or debug terminal applications, capture TUI snapshots, or automate terminal inputs. |
| O-026 | vercel-deploy | 部署/运维 | Deploy applications and websites to Vercel. Use this skill when the user requests deployment actions such as "Deploy my app", "Deploy this to production", "Create a preview deployment", "Deploy and give me the link", or "Push this live". No authentication required - returns preview URL and claimable deployment link. |
| O-027 | web-artifacts-builder | 前端/UI | Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state management, routing, or shadcn/ui components - not for simple single-file HTML/JSX artifacts. |
| O-028 | webapp-testing | 测试/质量 | Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs. |
| O-029 | xlsx | 文档/知识管理 | Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix existing .xlsx, .xlsm, .csv, or .tsv file; create a new spreadsheet from scratch or from other data sources; or convert between tabular file formats. |
| O-030 | brand-guidelines | 前端/UI | Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply. |

## 分类统计

| 分类 | 数量 | Skills |
|------|------|--------|
| 开发工具 | 6 | antigravity, claude-api, cmux, cross-project-adapter-migration, mcp-builder, skill-creator |
| 前端/UI | 6 | figma-mcp-helper, slack-gif-creator, theme-factory, web-artifacts-builder, brand-guidelines, (部分 agent-browser) |
| 文档/知识管理 | 6 | browse-wiki, doc-coauthoring, install-wiki, pdf, pptx, xlsx |
| 代码审查 | 3 | install-code-review, review, simplify |
| 安全审查 | 2 | security-review, deep-security-review |
| 测试/质量 | 3 | install-qa, tuistory, webapp-testing |
| 浏览器自动化 | 1 | agent-browser |
| 运维/故障排查 | 1 | incident |
| 部署/运维 | 1 | vercel-deploy |
| 通讯/协作 | 1 | internal-comms |
| 会话管理 | 1 | session-navigation |

## 排除清单

| 排除类别 | 数量 | 说明 |
|----------|------|------|
| lark-* 系列 | 26 | lark-cli 符号链接安装的飞书相关 skill |
| 个人 skill | 15 | 用户自定义的业务/平台 skill |
| 第三方/越南语 skill | 11 | 非 Factory 官方的外部 skill |
| 占位符 skill | 4 | template-skill, good-skill, good-skill-minimal, good-skill-complex |
| **合计排除** | **56** | |
| **官方内置** | **30** | |
