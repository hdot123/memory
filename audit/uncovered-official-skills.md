# 未覆盖的官方 Skill 列表
> 总数: 33
> 生成时间: 2026-05-30
> 数据来源: ~/.factory/skills/ 目录对比系统 Available Skills 列表

## 排除规则
- ✅ 已在 ~/.factory/skills/ 下有同名目录 → 已覆盖，排除
- ✅ lark-* 开头 → 飞书系列，排除
- ✅ 第三方越南语（brand-voice-consistency, blog-draft, claude-md, code-refactor, code-review-specialist, lesson-quiz, self-assessment）→ 排除
- ✅ 占位符（template-skill, good-skill*）→ 排除
- ✅ memory-core-development → 项目级 skill，排除
- ✅ api-documentation-generator → 第三方，排除

## 未覆盖列表

| # | Skill Name | Description (英文原文) |
|---|-----------|----------------------|
| 1 | mission-planning | (不在当前 session Available Skills 列表中，可能已下线或尚未发布) |
| 2 | define-mission-skills | (不在当前 session Available Skills 列表中，可能已下线或尚未发布) |
| 3 | refactoring-playbook | (不在当前 session Available Skills 列表中，可能已下线或尚未发布) |
| 4 | tui-application-playbook | (不在当前 session Available Skills 列表中，可能已下线或尚未发布) |
| 5 | webapp-testing | Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs. |
| 6 | cmux-browser | Automate browser surfaces inside cmux. Use when the user wants to open a site in a cmux browser surface, wait for page state, snapshot interactive refs, click or fill elements, extract page data, or verify a web flow while keeping the runtime inside cmux. |
| 7 | image-enhancer | Improves the quality of images, especially screenshots, by enhancing resolution, sharpness, and clarity. Perfect for preparing images for presentations, documentation, or social media posts. |
| 8 | idea-refine | Refines ideas iteratively. Refine ideas through structured divergent and convergent thinking. |
| 9 | debugging-and-error-recovery | Guides systematic root-cause debugging. Use when tests fail, builds break, behavior doesn't match expectations, or you encounter any unexpected error. |
| 10 | using-agent-skills | Discovers and invokes agent skills. Use when starting a session or when you need to discover which skill applies to the current task. The meta-skill that governs how all other skills are discovered and invoked. |
| 11 | test-driven-development | Drives development with tests. Use when implementing any logic, fixing any bug, or changing any behavior. Use when you need to prove that code works. |
| 12 | planning-and-task-breakdown | Breaks work into ordered tasks. Use when you have a spec or clear requirements and need to break work into implementable tasks. |
| 13 | incremental-implementation | Delivers changes incrementally. Use when implementing any feature or change that touches more than one file. |
| 14 | api-and-interface-design | Guides stable API and interface design. Use when designing APIs, module boundaries, or any public interface. |
| 15 | ci-cd-and-automation | Automates CI/CD pipeline setup. Use when setting up or modifying build and deployment pipelines. |
| 16 | context-engineering | Optimizes agent context setup. Use when starting a new session, when agent output quality degrades, or when switching between tasks. |
| 17 | frontend-ui-engineering | Builds production-quality UIs. Use when building or modifying user-facing interfaces. |
| 18 | shipping-and-launch | Prepares production launches. Use when preparing to deploy to production. |
| 19 | spec-driven-development | Creates specs before coding. Use when starting a new project, feature, or significant change and no specification exists yet. |
| 20 | code-review-and-quality | Conducts multi-axis code review. Use before merging any change. |
| 21 | security-and-hardening | Hardens code against vulnerabilities. Use when handling user input, authentication, data storage, or external integrations. |
| 22 | deprecation-and-migration | Manages deprecation and migration. Use when removing old systems, APIs, or features. |
| 23 | code-simplification | Simplifies code for clarity. Use when refactoring code for clarity without changing behavior. |
| 24 | performance-optimization | Optimizes application performance. Use when performance requirements exist or when you suspect performance regressions. |
| 25 | browser-testing-with-devtools | Tests in real browsers. Use when building or debugging anything that runs in a browser via Chrome DevTools MCP. |
| 26 | git-workflow-and-versioning | Structures git workflow practices. Use when making any code change. |
| 27 | documentation-and-adrs | Records decisions and documentation. Use when making architectural decisions, changing public APIs, or shipping features. |
| 28 | adspower-browser | Runs AdsPower Local API operations via the adspower-browser CLI. Use when the user asks to create or manage AdsPower browsers, groups, proxies, or check status. |
| 29 | github | Operate GitHub via gh CLI - manage PRs, issues, repositories, Actions, and more. Requires gh CLI installed and authenticated. |
| 30 | cli-e2e-testcase-writer | Write scenario-based end-to-end Go testcases for the compiled `lark-cli` binary. Use when adding or updating a CLI testcase. |
| 31 | frontend-design | Create distinctive, production-grade frontend interfaces with high design quality. Use when the user asks to build web components, pages, artifacts, posters, or applications. |
| 32 | canvas-design | Create beautiful visual art in .png and .pdf documents using design philosophy. Use when the user asks to create a poster, piece of art, design, or other static piece. |
| 33 | algorithmic-art | Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use when users request creating art using code, generative art, flow fields, or particle systems. |

## 已覆盖的官方 Skill (30个)

agent-browser, antigravity, brand-guidelines, browse-wiki, claude-api, cmux, cross-project-adapter-migration, deep-security-review, doc-coauthoring, figma-mcp-helper, incident, install-code-review, install-qa, install-wiki, internal-comms, mcp-builder, pdf, pptx, review, security-review, session-navigation, simplify, skill-creator, slack-gif-creator, theme-factory, tuistory, vercel-deploy, web-artifacts-builder, wiki, xlsx

## 备注
- #1-4 (mission-planning, define-mission-skills, refactoring-playbook, tui-application-playbook) 不在当前 session 的 Available Skills 列表中，可能是历史 skill 或尚未发布，建议确认是否仍需覆盖
- #30 (cli-e2e-testcase-writer) 是 lark-cli 项目专用，可能不需要中英双语覆盖
