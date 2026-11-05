# 阿里云 Agent Skill 开发标准

依据（2026-10-26 阅读）：阿里云帮助中心「云 Agent 服务目录（CSP）」全部文档、智能体安全中心「Skills 检测」、Agent Skills 开放规范、阿里官方仓库 `aliyun/alibabacloud-aiops-skills`（387 个 Skill 的实际写法）。

适用：用户说「开发阿里 skill」「按阿里标准」「上阿里云 Agent 服务目录」时，按本标准开发。付费、欢迎句、面向用户文字等规则仍按对应的生图类或频次类 SOP；两者冲突时见第八节。

---

## 一、平台事实（先知道再动手）

1. 平台叫「云 Agent 服务目录」（agentcatalog.aliyun.com），分发四类资产：Agents、Skills、Plugins、Tools。
2. **目录里的 Skills 目前都是阿里云官方 Skill，全部免费**；文档没有第三方上架、提交或审核流程，也没有付费机制。要上架第三方或付费 Skill，先向阿里确认渠道，不得自行假设。
3. 详情页展示：能力说明、质量徽章（「通过业务测试」「通过安全检测」）、下载量、更新时间、SKILL.md 全文（含 Prerequisites）、源码链接；部分支持在线试用（OAuth 授权，操作真实云资源）。
4. 遵循 Agent Skills 开放规范，兼容 Claude Code、Cursor、Qoder、Qwen Code、Codex、Gemini CLI、GitHub Copilot、OpenClaw。
5. 安装：`npx skills add <仓库> --skill <name> --agent <客户端>`（Node.js 22+），或让 Agent 访问 `https://agentcatalog.aliyun.com/api/public/skills/{name}/download` 自主安装。安装路径：项目级 `.<客户端>/skills/`，全局 `~/.<客户端>/skills/`，**同名时项目级优先**。
6. 加载方式（渐进式披露）：发现阶段只读 name 和 description → 匹配后加载完整 SKILL.md → 执行时按需读 references、运行脚本。
7. Skill 只是指导，不替代运行环境和权限策略；能不能执行由平台身份、权限和流程决定。

---

## 二、目录结构

```
<skill-name>/                  # 目录名必须与 name 一致
├── SKILL.md                   # 必需
├── references/                # 字段说明、决策表、权限清单、验收标准等
│   ├── README.md              # 知识来源与「最后更新」日期、时效声明
│   ├── acceptance-criteria.md # 验收标准：正确 / 错误写法对照
│   ├── verification-method.md # 每一步的成功判定方法
│   └── ram-policies.md        # 调用阿里云 API 时必需
├── scripts/                   # 可执行脚本（官方帮助文档写作 tools/，官方仓库实际用 scripts/，以 scripts/ 为准）
└── assets/                    # 模板、示意图、CSV 等静态文件
```

- 引用文件用相对路径，**只引用一层**，不做多层嵌套引用。
- references 单个文件聚焦一个主题，越小越好。

---

## 三、SKILL.md frontmatter

| 字段 | 必填 | 规则 |
|---|---|---|
| `name` | 是 | 1–64 字符；只用小写字母、数字、连字符；不以连字符开头或结尾，不含 `--`；**与目录名一致** |
| `description` | 是 | 1–1024 字符；写清「做什么 + 什么时候用」，带触发词，并写「Do NOT use for: …」排除场景 |
| `license` | 否 | 官方常用 `Apache-2.0` 或 `MIT` |
| `compatibility` | 否 | ≤500 字符；只在有环境要求时写，例如 `aliyun-cli >= 3.3.3`、需要 AccessKey |
| `metadata` | 否 | 字符串键值对。官方常用：`domain`、`owner`、`contact`、`version`、`ram_policies` |
| `allowed-tools` | 否 | 实验字段，各客户端支持不一，一般不写 |

**命名**：`alibabacloud-` 前缀是阿里官方 Skill 的命名空间，**我们的 Skill 不得使用**，否则构成冒充官方；继续用 `mps-` 前缀。

description 写法（官方范式）：

```
description: |
  <一句话：做什么>。
  Triggers when users <描述场景>.
  Trigger phrases: "…", "…", "…".
  Do NOT use for: <相邻但不该触发的场景>.
```

中英文都可以：官方 387 个 Skill 中约 43% 的 frontmatter 含中文。面向国内用户时中文为主，触发词中英都写。

---

## 四、SKILL.md 正文结构

篇幅：**不超过 500 行、约 5000 token**；超出的细节移到 references。

官方高频章节，按以下顺序组织（不调用阿里云 API 的 Skill 跳过标「云」的章节）：

1. **标题 + 一段场景说明**（Scenario Description）：解决什么问题；可加一行 Architecture。
2. **Prerequisites**：运行前提（语言版本、CLI 版本、服务开通、账号），每项给检查命令和不满足时的处理。
3. **Authentication**（云）：凭证规则见第五节。
4. **Observability**（云）：见第五节。
5. **RAM Policy**（云）：列出每个 API 及对应权限，完整清单放 `references/ram-policies.md`；权限失败时停下，引导用户申请权限，等确认后再继续。
6. **Parameter Confirmation**：表格列出所有用户可定制参数（必填/可选、说明、默认值）。**执行前所有可定制参数必须经用户确认，不得未经同意使用默认值。**
7. **Core Workflow**：先写 **Hard Rules**（绝对规则，如「只读」「严禁…」），再分 Step 1、2、3…；每步写命令、要提取的字段、分支判断、引用哪份 references。
8. **输出格式**：给出结构化输出模板（报告用 markdown 模板）。
9. **Success Verification**：成功判定，细节放 `references/verification-method.md`。
10. **Error Handling**：常见错误 → 原因 → 处理。
11. **Cleanup**：创建过的资源如何清理；只读 Skill 写明「不创建、不修改任何资源，无需清理」。
12. **Command Tables**：用到的全部命令，可放 references。
13. **Best Practices**：经验和注意事项。
14. **Reference Links**：references 文件索引表（文件 + 说明）。

---

## 五、安全要求（对应「通过安全检测」徽章）

阿里安全检测：恶意文件、敏感信息、提示词投毒、LLM 意图分析（46 项，分 6 类）。上传包须是 zip 或 tar.gz，**单文件不超过 10MB**。开发时逐项避开：

1. **不硬编码任何凭证**：`sk-`、`AKIA`、`LTAI`、`ghp_`、JWT、私钥、数据库连接串都会被识别。示例配置只用占位符（如 `.env.example`）。
2. **凭证处理规则**（官方 Authentication 原文要求）：
   - 不读取、不回显、不打印 AK/SK；
   - 不在对话或命令行里让用户输入 AK/SK；
   - 不用字面量凭证执行 `aliyun configure set`；
   - 只用 `aliyun configure list` 检查凭证状态；没有有效凭证就停下，请用户在会话外配置后再回来。
3. **不含危险命令**：`rm -rf`、`mkfs`、`DROP DATABASE`、`git reset --hard`、关机、反弹 Shell、写 crontab / shell profile / `authorized_keys` 等持久化操作。
4. **不外泄数据**：不读取 `.env`、凭证文件、SSH 私钥后外发；不外传环境变量、剪贴板、截图、Agent 上下文。
5. **不写提示词注入**：指令和工具描述里不出现「忽略之前的指令」、角色切换、诱导绕过确认、隐藏指令；不用 Base64、零宽字符、同形字符混淆。
6. **不提权、不放宽配置**：不用 `sudo`、`chmod 777`、`--no-sandbox`；不写 `alwaysAllow`、`require_confirmation: false`、`tools: ["*"]`。
7. **危险操作必须确认**：创建、删除、释放资源和修改配置前必须让用户确认（与阿里 HITL 机制一致）；能只读的 Skill 在 Hard Rules 里写明「只读，严禁调用写操作 API」。
8. 安装脚本用 `curl | bash` 时，附「先下载、检查、再执行」的安全替代流程，并注明不要用 root 执行。

**Observability（调用阿里云 API 时）**：加载 Skill 时生成一次 32 位小写十六进制 session ID；每条调用云 API 的 `aliyun` 命令都加
`--user-agent AlibabaCloud-Agent-Skills/<skill-name>/{session-id}`；脚本通过环境变量 `SKILL_SESSION_ID` 读取。本地命令（configure、plugin、version）不加。

---

## 六、调用阿里云 API 的额外要求（云）

- Aliyun CLI **≥ 3.3.3**；执行 `aliyun configure set --auto-plugin-install true` 和 `aliyun plugin update`。
- 使用插件模式命令格式：`aliyun <产品> <kebab-case 命令> --kebab-case-参数`，不用 `aliyun ecs DescribeInstances --RegionId` 这种旧格式；插件模式下地域同时传 `--biz-region-id` 和 `--region`。
- 云上环境推荐 EcsRamRole 凭证；AK 明文只用于本地测试。
- 遵循最小权限原则，在 `ram-policies.md` 列全权限。

---

## 七、测试与交付

1. **验收标准** `references/acceptance-criteria.md`：按「✅ CORRECT / ❌ INCORRECT」对照写正确与错误的命令、参数、用法。
2. **知识时效** `references/README.md`：写「最后更新」日期、来源链接，并声明「与最新官方文档或接口实际返回冲突时，以官方和实际返回为准」。
3. 用 `skills-ref validate ./<skill-name>` 校验 frontmatter 和命名。
4. 安装后用一句自然语言验证能否正确匹配并执行，例如「帮我搜索当前账号下有哪些 ECS 实例」。
5. 上线前自查第五节 8 条安全要求。
6. 版本：官方仓库用分支 / 标签管理版本，`<skill-name>-<version>` 可回退；更新即重新安装。

---

## 八、与我们 SOP 的对应和冲突

| 事项 | 阿里标准 | 我们的 SOP | 处理 |
|---|---|---|---|
| 技能标识前缀 | 官方用 `alibabacloud-` | `mps-` | 用 `mps-`，不得用官方前缀 |
| 付费 | 目录内 Skill 全部免费，无付费机制 | myplanestore.com 付费 | 上架阿里目录前先向阿里确认渠道和是否允许付费，⛔ 负责人决定 |
| 篇幅 | ≤500 行 / 约 5000 token | ≤15KB | 两条都满足 |
| 遥测 | 云 API 命令强制带 user-agent + session ID | 第 12 条：不擅自遥测 | 只有调用阿里云 API 的 Skill 按官方要求加，并在 SKILL.md 说明；其他统计仍须负责人确认 |
| 参数确认 | 所有可定制参数执行前确认 | 两次确认 | 合并：方案确认时覆盖全部可定制参数 |
| 目录名 | 文档写 `tools/`，仓库用 `scripts/` | `scripts/` | 用 `scripts/` |
| description | 中英都可，写 Do NOT use for | Skill-SEO 规范 | 按 SEO 规范写，末尾加排除场景 |
