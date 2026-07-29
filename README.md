# A股市场主线识别 Agent

面向 A 股市场的结构分析智能分身，用户只需说"今日主线"即可获得完整的六段式市场分析报告。

## 功能

- 自动拉取三大指数行情、行业涨跌、个股行情等数据（通过财新数据平台）
- 基于涨停集中度 + 行业涨幅 + 周月趋势的四维综合评分识别主线
- 判断情绪周期（冰点/调整/修复/主升/高潮）
- 识别核心锚点个股（情绪标的/趋势中军/补涨标的）
- Agent LLM 亲自生成六段式交易报告

## 使用方式

### ✅ 规范指令（推荐使用，AI 稳定路由到本 Agent）

| 指令 | 说明 |
|---|---|
| `今日主线` | 分析最近一个交易日 |
| `主线识别 2026-06-17` | 指定日期分析 |
| `分析今天A股市场主线` | 完整描述 |
| `每日主线` | 同义词触发 |
| `调用主线分析agent` | 直接点名 |

**关键词**：指令中包含 **"主线"** 二字，AI 即可稳定识别意图并调用本 agent。

Agent 会自动：鉴权 → 拉取数据 → 结构化分析 → AI 生成六段式报告（约 5 分钟）。

### ❌ 容易误路由的指令（请避免使用）

以下指令会**触发其他 agent 或导致 AI 不知该调用谁**，**不要这样调用本 agent**：

| ❌ 模糊指令 | ⚠️ AI 可能误调用的对象 |
|---|---|
| `分析下今天市场` | Wind / 通用行情 agent |
| `看看大盘` | 行情查询 agent |
| `今天股票怎么样` | 个股分析 agent |
| `市场行情` | 通用行情接口 |
| `今天该不该买` | 投资建议类（无对应 agent，会乱答） |
| `分析下XX股票` | cxdata-stock-analysis-agent |
| `电子板块怎么样` | 板块分析 agent |

> 如果使用了上述模糊指令，AI 会主动反问澄清，但会多一次交互——建议直接用规范指令。

### 🔀 与其他 agent 的边界（避免重复调用）

| 用户需求 | 应调用 |
|---|---|
| **A股市场整体主线 / 板块强弱对比 / 情绪周期** | **本 agent**（主线识别） |
| 单只个股的基本面/财报/估值分析 | cxdata-stock-analysis-agent |
| 单一板块的深度分析（如只看电子） | 板块分析 agent |
| 单只股票的最新价 / K线 / 分钟行情 | Wind / 通用行情 agent |
| 港股 / 美股 / 期货 / 加密货币 | 对应市场 agent |
| 回测 / 选股 / 策略 | 策略类 agent |

## 前置依赖

1. 安装 Python 依赖：`pip install python-dotenv requests cryptography`
2. 鉴权配置（**火山部署版：环境变量 CXDA_USER_KEY**）：
   - 通过火山平台环境变量面板设置 `CXDA_USER_KEY`，无需 SMS 登录或 `.env` 文件
   - 鉴权优先级：环境变量 `CXDA_USER_KEY` → `~/.cxda-cache/.shared/cxda_auth.json` 共享缓存 → SMS 验证码登录（兜底）
   - 调用 `skills/mainline-analysis/scripts/auth.py status` 检查认证状态
   - 数据源 Skill 已内置在 Agent 中，无需额外下载

## 目录结构

```
cxdata-mainline-analysis-agent/
├── AGENT.md                                       # Agent 整体人设与执行逻辑
├── SOUL.md                                        # 身份、性格、能力边界
├── rules.md                                       # 硬性规则
├── config.json                                    # 元数据配置
├── skills/
│   ├── mainline-analysis/                         # 主线识别分析 Skill
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── fetch_data.py                      # 数据获取（subprocess 调 query.py）
│   │       ├── analyze_data.py                    # 结构化分析（综合评分 + 情绪周期）
│   │       ├── auth.py / common.py /              # cxdata 官方鉴权四件套（拷自新版 skill）
│   │       ├── cxda_cache_cli.py / query.py
│   │       ├── requirements.txt
│   │       └── data/                              # 中间数据（自动生成，.gitignore 排除）
│   ├── cxdata-stock-market-information/           # 内置数据源（空壳：SKILL.md + references）
│   ├── cxdata-stock-basic-information/            # 内置数据源（空壳）
│   └── cxdata-industry-classification-company/   # 内置数据源（空壳：行业代码表）
└── README.md
```

## 变更历史

### 2026-07-29 火山部署版二次精简——移除手机号鉴权、session积分计费残留、16:10数据时效约束、行内{}替换

**核心变更：彻底移除手机号鉴权 + session积分计费残留 + 主线分析增强**
- `auth.py`：移除 send-code/verify 手机号鉴权子命令及相关函数，补 CXDA_USER_KEY 环境变量短路（622行→~280行）
- `query.py`：移除 session 积分计费逻辑（start/confirm/summary/reset、50次确认守卫、计费记录），保留 api/page-size/package（809行→~250行）
- `analyze_data.py`：composite_score 权重调整（日涨幅 0.3→0.4，涨停集中度 0.3→0.2）
- `analyze_data.py`：市场环境涨跌行业改用二级行业口径（industry_l2_quotes）
- `fetch_data.py`：新增 16:10 数据时效性校验（今日数据4:10后更新，此前退出；--force 可跳过）
- `AGENT.md`：删除 session 步骤，加 16:10 数据时效性约束说明
- `SKILL.md(cxdata-stock-market-information)`：删除积分消耗提示整节、套餐额度查询整节、session/confirmation_required 引用
- `SKILL.md(cxdata-stock-basic-information)`：删除 session 引用，精简鉴权说明
- `auth-flow.md(两个references)`：删除 SMS 登录全段，仅保留环境变量鉴权
- `SKILL.md(mainline-analysis)`：行内 {} → <>（代码块内不变，避免影响打镜像）

### 2026-07-29 数据源配置与实际调用对齐（删舆情引用 + 补行业分类引用）

- **问题**：`SKILL.md` 数据源表声明引用了 `cxdata-public-opinion-stock-index`（舆情 skill），但 `fetch_data.py` 实际未调用其任何接口（舆情数据源已于 2026-06-23 移除）；反之，`fetch_data.py` 实际调用了 `cxdata-industry-classification-company` 的 `getPubInduCodeByCond-G`（申万三级→二级映射），但该 skill 未在数据源表体现，配置与实际调用不一致。同时该 skill 目录存在多余嵌套（双层），与规范结构不符。
- **方案**：
  - 删除 `skills/cxdata-public-opinion-stock-index/` skill 目录及其 references
  - 新增 `skills/cxdata-industry-classification-company/` skill（SKILL.md + references/getPubInduCodeByCond-G.md），拍平为单层结构
  - `SKILL.md` 数据源表：移除 public-opinion 行，新增 industry-classification-company 行；description 去掉"舆情"；第4条规则改为"报告不得包含催化/舆情段落"
  - `rules.md` 第4条同步；`README.md` 目录树与描述文字同步去除残留"舆情"
- **效果**：数据源配置清单与 `fetch_data.py` 实际调用 100% 一致，消除配置歧义；行业分类 skill 显式纳入依赖清单，便于维护与审计

### 2026-07-24 火山部署版：移除积分/session会话账本逻辑，统一CXDA_USER_KEY环境变量鉴权

本版为火山部署专用版本，与原版 `cxdata-mainline-analysis-agent` 分离为独立 repo（`cxdata-mainline-analysis-agent-huoshan`）。

**核心变更：移除积分/session机制**
- `query.py`：移除 uuid import、5 个共享存储函数（get/save_shared_json/text、append_shared_text）、SESSION_LEDGER/SESSION_CALLS_LOG/IDLE/50次阈值/CONFIRMATION_REQUIRED 常量、整个会话账本函数群（约20个函数，含 _record_call_if_billable/_guard_before_billable_api_call/session start/summary/confirm/reset 等）、_format_session_package、cmd_session 子命令、cmd_api 中的 confirmation guard 旁路；净删约 390 行
- `fetch_data.py`：移除 _session_start()/_session_summary()/_session_confirm() 定义和调用（约51行）、call_api 中 confirmation_required 自动确认重试旁路
- `auth.py`：新增 CXDA_USER_KEY 环境变量鉴权优先路径（env → cache → SMS）
- `common.py`：get_user_key 优先从环境变量 CXDA_USER_KEY 读取，auth.py status 返回 auth_source 字段（env_var/cache）

**鉴权流程（火山部署版）**
- 火山用户通过平台环境变量面板设置 CXDA_USER_KEY，无需 SMS 登录或 .env 文件
- 鉴权优先级：环境变量 CXDA_USER_KEY → ~/.cxda-cache 共享缓存 → SMS 验证码登录（兜底）
- 保留全部 22+1 安全加固（CRITICAL/HIGH/MEDIUM/LOW 全部 intact）

**前置依赖更新**
- README 前置依赖段改为火山部署版描述：通过环境变量 CXDA_USER_KEY 配置鉴权，无需 SMS 登录
- `pip install python-dotenv requests cryptography`（cryptography 为凭证加密硬依赖）

**与原版关系**
- 原版 `cxdata-mainline-analysis-agent` 保持不变（含积分机制）
- 本版 `cxdata-mainline-analysis-agent-huoshan` 为火山部署专用，积分逻辑移除后不可回退合并

### 2026-07-17 火山终版安全加固（对齐 stock agent 审计通过版本）

参照火山客户提供的 stock-analysis-agent 终版安全加固，完整同步所有安全修复至 mainline agent。4 个核心共享脚本从已通过审计的 stock agent 直接复制，query.py 和 requirements.txt 同步修改。

| 修改项 | 说明 |
|--------|------|
| auth.py | 审计日志系统 + terms_decline 确认机制 + 手机号短号码保护 |
| common.py | authtoken 加密存储 + http_post_form + SSRF 防护重构 + gzip 炸弹防护 + CXDA_CACHE_PYTHON 白名单 + _is_valid_user_key + 纯点文件名拒绝 |
| cred_crypto.py | pepper 文件密钥派生 + _get_effective_username + JSON 序列化防碰撞 |
| cxda_cache_cli.py | symlink 攻击防护 + O_NOFOLLOW 读写 + 词法路径 delete + 纯点名拒绝 + /root 黑名单移除 |
| query.py | userKey POST 替代 GET + http_post_form |
| requirements.txt | cryptography 锁版本 + requests 加下限 |

**详细报告**：见 `火山安全加固修改报告.md`

### 2026-07-09 火山安全扫描 4 条风险修复

| # | 风险 | 修复 |
|---|---|---|
| 1 | `_cli_call` 环境变量全量传递导致 RCE（PYTHONPATH/LD_PRELOAD）| `common.py` `_cli_call` 改为环境变量白名单传递，只传 PATH/HOME/USER/LANG/CXDA_CACHE_* 等必需变量，黑名单拦截 PYTHONPATH/PYTHONHOME/LD_PRELOAD/LD_LIBRARY_PATH/DYLD_* 等 |
| 2 | `_cli_call` 子进程继承敏感环境变量（AWS_*/DATABASE_URL 等）| 同风险1 白名单方案，非白名单变量一律不传 |
| 3 | `cred_crypto` 密钥仅由 hostname+username 派生，易被离线破解 | `cred_crypto.py` 新增 `_get_machine_id()`（macOS IOPlatformUUID / Linux machine-id / Windows MachineGuid），密钥派生材料加入 machine-id，增加攻击者获取密钥材料难度 |
| 4 | `analyze_data.py` meta 字段缺类型校验，恶意 JSON 导致 TypeError 崩溃 | 新增 `safe_int()` 函数，所有 meta 数值字段（limit_up_count/limit_down_count/total_stocks/sealed_count/broken_count）统一经 `safe_int()` 转换 |

**改动文件**：`common.py`、`cred_crypto.py`、`analyze_data.py`（主线 agent）；`common.py`、`cred_crypto.py`（股票 agent 同步）

**验证**：5 文件语法编译通过；风险1+2（白名单放行+黑名单拦截+敏感变量阻断）、风险3（machine-id 获取+加解密往返+派生材料验证）、风险4（safe_int 基础+正常值+恶意值不崩溃）全部通过

**注意**：风险3 修改了密钥派生材料（新增 machine-id），升级后旧密文将无法解密（换机器/升级后需重新鉴权一次，与此前 host/user 变化行为一致）

### 2026-06-29 硬编码凭证：cred_crypto 密钥派生退化检测

火山扫描报出 `cred_crypto.py` 的 `_derive_key()`：当 `socket.gethostname()` 返回空且所有用户标识源（`getpass.getuser()`/`USER`/`USERNAME`）均为空时（典型容器环境），派生 material 退化成固定 `b"|"`，密钥可预测，攻击者可解密所有凭证。

- `_derive_key()` 新增退化检测：host 与 user 均空时 `raise RuntimeError` 拒绝生成弱密钥，强制环境配置 hostname/user
- 三 agent（主线/股票/质地）cred_crypto.py 同源同步修复

**验证**：退化场景（host/user 全空）拒绝生成密钥；正常场景正常派生；加解密往返不受影响；换机器特征后老密文解不开（密钥仍正确绑定机器特征）

**教训**：前几轮 checklist 偏重输入注入类，缺"依赖的外部数据源（gethostname/getuser）退化成弱状态"这一类，已补进 [[feedback_security_fix_methodology]] 的 checklist

### 2026-06-29 路径遍历补漏：list_files / _get_skill_path 的 skill_name 校验

火山扫描报出 `cxda_cache_cli.py` 两个此前未加固的方法：`list_files()` 和 `_get_skill_path()` 都未校验 `skill_name`，`../etc` 可列出/创建任意目录。此前只加固了 `_get_file_path`（read/write 入口），没往上追溯到同样接收 skill_name 的这两个方法——典型的"堵了 payload 没堵攻击向量"。

- 新增类级 `_SAFE_NAME_RE` 白名单 + `_validate_skill_name()` 方法
- `_get_skill_path`、`list_files`、`_get_file_path` 三个接收 skill_name 的入口统一调用校验
- `list_files` 的 subdir 分支改为直接拼路径（列表操作不应 mkdir，消除副作用）
- 三 agent（主线/股票/质地）同源同步修复

**验证**：三 agent 语法通过；`_validate_skill_name` 覆盖三入口；8 个路径遍历变体（`../etc`/`..`/`a/b`/`..%2f`）全拦截，合法名不误伤

### 2026-06-27 0627 预演补漏 + 对照火山清单包体整洁

**预演补漏**（0626 改完后做变体自测，主动发现并修复）：`CXDA_CACHE_PYTHON` 仍能指向任意可执行文件（`/tmp/evil.py`）。`_safe_env_executable` 新增 `name_pattern` 参数，`_get_python_exe` 要求文件名匹配 `^python(\d+(\.\d+)*)?$`——合法 python（系统/homebrew/venv）放行，`evil.py`/`sh`/`bash` 拒绝。

**对照火山清单【1001 包体合规性】**：1 个历史报告样本（`A股市场主线识别报告-2026-06-08.md`）被 git 跟踪会进交付 zip。`git rm --cached` 移除（本地保留）+ `.gitignore` 扩大排除模式（`A股市场主线识别报告*.md`）。

### 2026-06-26 安全扫描 5 条风险修复（攻击向量变体根治 + 同源补漏）

前几轮修复暴露方法论问题：消除扫描器“看得见的写法”，但没堵“同一攻击向量的其他变体”。本轮针对变体绕过根治，并同步修复 stock agent 同源问题：

| # | 风险 | 修复 |
|---|---|---|
| 1 | env RCE：放行 ../ 和绝对路径 | `common.py` 新增 `_safe_env_executable`：拒 `..`、必须绝对路径；CLI_PATH 限定 scripts 目录 + 文件名 `cxda_cache_cli.py` |
| 2 | SSRF：未规范化 path | `http_get` path 校验加 `unquote`+`posixpath.normpath`，防 `/cxda/../admin` 和 `%2e%2e` 绕过 |
| 3 | phone 走 GET 查询参数 | `auth.py` send-code 改 POST form data，phone 不进 query string（已验证后端支持 POST） |
| 4 | code 走 GET 查询参数 | `auth.py` verify 改 POST form data |
| 5 | parse_params 黑名单大小写敏感 | 黑名单全小写 + `k.lower()` 归一化比较，防 `Authtoken`/`USERKEY` 绕过 |

**同源补漏（stock 反馈未报，但代码同源，一并修复避免下轮）**：
- `cxda_cache_cli.py` 私域 write 改 0o600 权限 + `O_NOFOLLOW`（缓解默认 0o644 与 TOCTOU 符号链接替换）
- `cxda_cache_cli.py` shared/private write 的 content 改 stdin 传递（不进命令行）；`common.py` 调用同步

**改动文件**：`auth.py`、`common.py`、`query.py`、`cxda_cache_cli.py`

**验证**：两 agent 全部语法通过；POST send-code 端到端正常（后端返回成功）；parse_params 5 变体拦截、env 拒 ../、SSRF 拒 ../admin、私域 write 0o600、符号链接 TOCTOU 拒绝、content stdin 读写往返 全部通过

### 2026-06-25 风险 1/4 终极加固：cred_crypto 改硬依赖，彻底消除“无加密分支”

风险 1/4（缺 cryptography 则明文存储）此前用 `try/except ImportError` + `save_auth` 内 raise 拦截。但静态扫描器（如火山）若按模式匹配判定，看到 `except ImportError` 分支存在仍会报，不深入分析 raise 是否覆盖所有路径。为对“数据流分析”和“模式匹配”两种扫描规则都免疫，改为硬依赖：

- `common.py` 删除 `try/except ImportError` 块，直接 `import cred_crypto`；缺失 cryptography 库时 `ModuleNotFoundError` 直接终止，**代码里不存在任何“无加密执行”分支**
- 清理 `_HAS_CRYPTO` 变量及其所有死分支（save_auth / get_user_key）
- 老明文数据读取兼容不丢：`cred_crypto.decrypt` 对无 `ENCv1:` 前缀的数据原样返回并标记迁移

**改动文件**：`common.py`

**验证**：`_HAS_CRYPTO`/`except ImportError` 残留为 0；新 key 加密写入、读回透明解密、老明文读取兼容 3 项回归通过

**连带影响**：运行环境须 `pip install cryptography`（requirements.txt 已声明，.venv 已装）

### 2026-06-25 安全扫描第 8 条修复：私域 read/write 路径遍历（补漏）

上一批已根治风险 1-7，第 8 条（cxda_cache_cli 私域 read/write 的 skill/file 参数缺路径遍历校验）当时未触及，本次补上：

- `cxda_cache_cli.py` `_get_file_path` 新增**双重防护**：
  1. 入口白名单：`skill_name`/`filename` 只允许字母数字下划线连字符点，从源头拒绝 `../`、`/`、URL 编码（`%2f`/`%5c`）等逃逸字符
  2. resolve 校验：目标路径 resolve 后必须仍位于 skill 子目录内（`relative_to`）
- 公域 `_get_shared_path` 原有 resolve 校验保留；`subdir` 原有 `SUBDIR_TYPES` 白名单保留

**改动文件**：`cxda_cache_cli.py`

**验证**：11/11 逃逸变体（`../evil`、`..%2f`、`..%5c`、`a/b`、`..` 等）全部拦截；合法名（`my-skill`/`my_skill`/`skill.v2`/`data_file-1.json`）不误伤

### 2026-06-25 安全扫描 8 条风险根治（改到发源地 + 消除危险模式，含 subprocess 凭证传递）

前两批（c828e5f、502309a）虽标注修复，但经核实 `save_auth`→`_cli_call`→`subprocess` 链路一直把 CXDA_USER_KEY 经命令行参数传递（ps aux 可见），风险 2/3 从未被触及；风险 1/4/5/6/7 的发源地也未真正改到位。本轮针对根因重做，并新增对 subprocess 凭证传递的处理。

| # | 风险 | 本轮修复（改到发源地） |
|---|---|---|
| 1/4 | 缺 cryptography 则明文 | `common.py` `save_auth` 在 `_HAS_CRYPTO=False` 时**拒绝写入** CXDA_USER_KEY，消除明文落盘代码路径 |
| 2 | 凭证经命令行传 subprocess | `cxda_cache_cli.py` `auth set --data` 改可选、缺省从 **stdin** 读；`common.py` `save_auth` 改用 `stdin_input` 传，密钥不再进 argv（ps aux 不可见） |
| 3 | 异常消息含完整命令行 | `common.py` `_cli_call` except 分支脱敏，按异常类型返回（TimeoutExpired/FileNotFoundError/类型名），不再把含敏感参数的 cmd 放入 error |
| 5 | 环境变量 RCE | `common.py` 新增 `_safe_env_path`，`CXDA_CACHE_PYTHON`/`CLI_PATH`/`WORKSPACE`/`CLAUDE_WORKSPACE` 取值过滤 shell 元字符 |
| 6 | SSRF 仅 startswith 可绕 path | `common.py` `http_get` URL 校验改为 scheme/host/path 三重校验，path 必须以 `/cxda/` 开头，拒绝 `/cxdaevil/` 等同域跨 path |
| 7 | http_get 异常堆栈泄漏 | `common.py` `http_get` 内部 catch，网络/解析异常转 RuntimeError 脱敏，不抛含 url 的原始异常 |
| — | phone/code 命令行可见 + 输入校验 | `auth.py` send-code/verify 去掉 `--phone`/`--code` 改 stdin(JSON)；`query.py` `parse_params` 加保留字段黑名单、新增 `_validate_api_id` 白名单（cmd_api/page_size/package 入口） |

**改动文件**：`common.py`、`auth.py`、`query.py`、`cxda_cache_cli.py` + `AGENT.md`、3 个 skill 的 `SKILL.md`/`auth-flow.md`（共 7 处文档同步调用方式）

**验证**：5 文件语法编译通过；stdin 凭证传递（argv 不含 --data、input 收到数据）、异常脱敏（不含 secret）、SSRF host+path 双校验（合法 `/cxda/` 放行、`/cxdaevil/` 拒绝）、环境变量元字符过滤、api_id/parse_params 黑白名单、stdin phone/code 读取 7 项冒烟测试全过

**连带影响（需知悉）**：
- 风险 2 改了 CLI 接口：`cxda_cache_cli.py auth set` 现优先 stdin（`--data` 仍兼容）；`save_auth` 改用 stdin 传，上游若有直接拼 `auth set --data` 的地方需改 stdin
- 认证调用接口变更：send-code/verify 改 stdin 传 JSON，上层 Agent 须同步（文档已改）
- 风险 1/4 强约束：运行环境须 `pip install cryptography`，否则写 CXDA_USER_KEY 会 RuntimeError

### 2026-06-25 对齐同事官方积分机制（jsonl 追加日志）+ 保留全部安全加固

同事 6-24 提供官方最新四件套（query/common/cxda_cache_cli/auth），积分统计采用更优的 **jsonl 追加日志机制**（取代我们旧的 JSON 读改写 + _ledger_lock 文件锁）。本次对齐官方机制，同时保留我们之前做的全部安全加固。

**积分机制（对齐同事官方版）：**
- 记账改为 `append_shared_text` 追加到 `cxda_session_calls.jsonl`（每调用一行 JSON），天然并发安全，无需文件锁
- 会话隔离用 `session_id`（uuid），取代空闲超时判断
- 保留 `_record_call_if_billable`/`_guard_before_billable_api_call`/session start/summary/confirm/reset（与同事逐字节一致）
- 移除我们的 `_ledger_lock`（jsonl 追加无需锁）

**安全加固（全部保留，叠加在同事四件套上）：**
- SSRF：http_get url 白名单（BASE_URL）
- 路径遍历：_validate_shared_filename（入口）+ cli 侧 resolve/relative_to 校验
- 凭证加密：cred_crypto（CXDA_USER_KEY Fernet 加密，save_auth 加密 / get_user_key 解密 + 老明文迁移）
- 文件权限：_secure_write_text(0o600) + mkdir(0o700)
- 异常脱敏：_safe_net_error（auth 网络异常不泄露手机号/验证码）
- api_main 白名单、workspace 环境变量校验

**验证**：6-23 完整 fetch，jsonl 记账 389 次调用 / 5170 积分，session summary 准确；安全防护 11 项全在；query.py 积分记账函数与同事版逐字节一致

### 2026-06-24 安全扫描第二批 5 条风险加固（按客户要求）

客户第二轮扫描命中 5 条输入验证类风险，逐条核实后（多数为理论性/已部分加固）按客户要求全部追加防御：

| # | 风险 | 加固 |
|---|---|---|
| 1 | detect_workspace 环境变量路径遍历 | 新增 `_validate_workspace_path`：拒绝系统关键目录（/etc /bin /usr /var 等）、要求路径在用户家目录下，否则回退默认 ~/.cxda-cache |
| 2 | _get_cli_path RCE | 新增 `_is_path_trusted`：环境变量指向的 .py 必须在可信区域（脚本同目录/家目录/python安装目录），拒绝 /tmp 等临时目录 |
| 3 | _get_python_exe RCE | 同上，可执行文件必须落在可信区域，否则回退 sys.executable |
| 4 | http_get SSRF | url 白名单：必须以 BASE_URL 开头（官方 cxdata 域名），拒绝任何其他 host，防止请求导向内部/任意服务 |
| 5 | get/save_shared_json 路径遍历 | 新增 `_validate_shared_filename`：filename 只允许字母数字下划线连字符点，拒绝含 `/` `\\` `..` 的路径（CLI 侧 _safe_join 作兜底） |

**验证**：5 条防护端到端测试通过（/etc 回退、/tmp/evil.py 回退、evil.com 拒绝、../etc/passwd 拒绝且正常文件名不误伤）；完整 fetch+analyze 业务正常（记账完整、主线结论一致），加固对业务零影响

### 2026-06-24 排除 B 股（主线分析针对上证 A 股口径）

- **问题**：fetch 的 `valid_quotes` 过滤只剔除无涨幅数据的股票，**未排除 B 股**。B 股（上交所 900 开头、深交所 200 开头）也有涨跌停，若不排除会被计入全市场涨停/封板/炸板/主线统计，污染 A 股主线口径。当前数据恰好无 B 股涨停属运气，属隐患。
- **修复**：`fetch_data.py` 新增 `is_b_share(code)`（前2位为 90 或 20 即 B 股），`valid_quotes` 过滤增加 `not is_b_share(...)` 条件，使涨停/封板/炸板/主线统计全部基于 A 股口径
- **验证**：is_b_share 对 900901/200002 判定 B 股（排除），600000/000001/920083/688478 判定 A 股（保留）；过滤模拟 B 股被正确排除

### 2026-06-23 积分记账完整性修复 + pageSize 动态化

同事反馈两条积分相关问题，均已修复：

**1. 积分记账漏统计（根因：并发写覆盖）**
- **现象**：完整 fetch 实际调用上百次，账本只记几条；session summary 严重偏低
- **根因**：fetch_data 的市值/行业分类步骤用 ThreadPoolExecutor(max_workers=5) 并发调 query.py，5 个 subprocess 同时「读账本→追加→写账本」，flock 只锁了写瞬间没锁读-改-写整个临界区，后写覆盖先写
- **修复**：`query.py` 新增 `_ledger_lock()`（flock 排他锁），把 `_record_call_if_billable` 和 `_guard_before_billable_api_call` 的「读-改-写」整个包进临界区；并发记账不再丢失
- **规范对齐**：fetch_data 开头调 `session start`（重置账本），结尾调 `session summary` 输出消耗；积分消耗以 session summary 返回为准，不由 AI 自行统计

**2. pageSize 写死 10000 导致分页错误**
- **现象**：`fetch_all_pages` 写死 pageSize=10000，但各接口 maxPageSize 不同（如 getStkDayQuoByCond-G 实际 1000），客户端按写死值算分页数会错
- **修复**：`fetch_data.py` 新增 `_get_max_page_size(api_id)`，通过 `query.py page-size` 动态获取接口实际 maxPageSize；fetch_all_pages 和 fetch_industry_by_level 均改用动态值

**效果**（6-18 验证）：记账完整——9 个接口全部记录，58 次计费调用 / 630 积分（修复前因覆盖只记到 2-8 次）；分页正确——按接口实际 maxPageSize 分页

### 2026-06-23 移除舆情数据源（积分成本优化）

- **问题**：舆情接口（getIndexLyricalList1/2）单次消耗 100 积分，是所有接口里最贵的；每次完整 fetch 查 103只×2=206次，约占会话积分消耗 87%。但舆情在报告里仅用于「催化因素」一句话，性价比极低。
- **方案**：彻底移除舆情数据源——
  - `fetch_data.py`：删除两个舆情接口白名单 + query_stock_detail 里的舆情查询 + stock_detail 的 pos/neg 字段；fetch 耗时 122s→86s
  - `analyze_data.py`：删除持续性评估的舆情 reasons、opinion 字段、limit_up_by_industry 个股的 pos/neg 字段
  - `AGENT.md`：催化相关规则改为「不输出催化/舆情段落」
  - 报告：移除「催化因素」段落
- **效果**：单次 fetch 积分消耗降约 87%（省去 ~2万积分/次），fetch 提速约 30%；报告结论不受影响（主线/锚点/情绪均基于行情数据，不依赖舆情）

### 2026-06-23 报告措辞严谨性加固 + 观察点张冠李戴 bug 修复

- **问题**：复核 6-17 报告发现多处 LLM 措辞问题——封板「一般」被拔高为「中等偏强」（与数据矛盾）、「加速段/最陡峭」等无数据支撑断言、「封板率较前日回升」跨日编造、催化「均无」绝对化、玻纤带动股漏掉成交最大的中材科技。
- **代码修复**（影响所有报告）：
  - `analyze_data.py` 观察点生成逻辑修复张冠李戴——旧版 `anchors[0]/[1]` 取全局涨幅前二，可能属其他板块（如核心是玻璃玻纤却写出面板股长信科技/TCL科技）；改为先筛 `industry==core_name` 的主线锚点，不足2个才回退全局，三边界均安全
  - `analyze_data.py` 移除「加速段」措辞——周涨幅高只代表位置高不代表加速（数据无斜率对比），observation_points 和 key_judgments 改用「高位」
- **规则加固**（AGENT.md 新增第13-17条）：禁止无数据支撑的趋势性/强度断言（加速段/最陡峭/资金主攻）、封板定性必须沿用 key_judgments 原词不得拔高、禁止自创跨日对比、催化不得绝对化、板块成分股必须核对 limit_up_by_industry
- **效果**：6-17 报告逐项修正，措辞与数据一致；规则层面根治，避免后续报告重蹈

### 2026-06-23 安全扫描 6 条风险项修复

客户安全扫描命中 6 条风险，逐条核实后处置如下：

| # | 风险 | 真伪 | 处置 |
|---|---|---|---|
| 1/4 | cxda_cache_cli.py filename/skill_name 路径遍历（`../` 逃出 workspace 读写任意文件）| 真实 | `_safe_join` 统一做 resolve()+起始目录校验，逃逸即抛 ValueError；shared_read/write/delete、私域 read/write/delete/list_files 全部加捕获 |
| 6 | 凭证文件权限过松（默认 0o644/0o755，同机用户可读）| 真实 | `mkdir` 显式 `mode=0o700` + `os.chmod` 兜底；文件写改 `_secure_write_text`（`os.open` 指定 0o600）；workspace/.shared/各 skill 目录全部收紧 |
| 2 | CXDA_USER_KEY 明文存储 | 真实 | 新增 `cred_crypto.py`（Fernet 对称加密，PBKDF2 从机器特征派生密钥）；`save_auth` 落盘前统一加密 CXDA_USER_KEY，`get_user_key` 读取时透明解密；老明文数据首次读取自动迁移为密文；requirements 加 cryptography |
| 5 | common.py 环境变量 `_cli_call` RCE | 误报（能改环境变量=已有本地执行权）| 仍按客户要求加固：`CXDA_CACHE_PYTHON`/`CXDA_CACHE_CLI_PATH` 必须指向真实存在且合法的文件（python 可执行/cli 为 .py），否则回退默认 |
| 3 | query.py 参数 SQLi | 误报（参数走 HTTP GET，不碰 SQL）| 仍按客户要求加固：`parse_params` 对参数 key 做标识符白名单校验（`^[A-Za-z_][A-Za-z0-9_]*$`），value 长度上限，拒绝含特殊字符的参数名 |

**验证**：6 条防护端到端测试全部通过（路径遍历拦截、权限 0o600/0o700、加密往返+老明文迁移、恶意环境变量回退、非法参数名拒绝）；正常业务调用（合法参数、正常读写、鉴权取数）不受影响。

### 2026-06-23 修复申万二级行业归并 bug（14.6% 涨停股漏归）

- **问题**：个股→申万二级的归并用字符串包含匹配，6-18 实测漏归 14.6%（15/103 涨停股未归入任何板块，导致主线涨停数偏少）。根因：
  1. **取错数据源**：个股行业用 `getDPubComInfo1ByCond-G` 的 `INDU_CLASS_NAME_Q`，但那是 **GICS 口径**（如「金属与采矿」），与板块行情的申万二级（「小金属」）词面对不上
  2. **GICS vs 申万两套体系硬凑**：`_match_l2_from_industry_name` 拿 GICS 名做字符串包含匹配申万二级，命中率天然低
- **方案**（用对接口，根治口径错配）：
  - **fetch_data.py** 白名单加 `getPubInduCodeByCond-G`（行业代码表）。个股查询串联：先用 `INDU_CLASS_NAME_S`（申万三级名）查该表，从返回的多条记录（GICS/中证/申万各一条）里**筛选 `INDU_SYS_PAR` 含「申银万国」+ 2021 版**的那条，取 `INDU_NAME2`（申万二级名）+ `INDU_CODE2`
  - **analyze_data.py** 主线涨停集中度 + 锚点归并，改用 `sw_industry_l2` **精确匹配**板块行情的二级标准名，退役 `_match_l2_from_industry_name` + `SW_L3_TO_L2_KEYWORDS` 关键词表（删死代码）；加漏归自检告警
  - **关键坑**：`getPubInduCodeByCond-G` 同一行业名返回多条不同分类体系记录，必须筛选申万那条，否则取到 GICS 的二级名（「半导体产品与设备」≠ 申万「半导体」）
- **效果**（6-18 真实数据回归）：申万二级取到率 100%（103/103），**精确命中板块列表 100%**，漏归率 14.6%→0；主线结论修正为**小金属**（涨停6家，得分86.5），推翻此前因 GICS 错归导致的「通信设备」「半导体」误判
- **关联**：cxdata 接口套餐权限——`getPubInduCodeByCond-G` 需授权「股票库定制套餐(largeType-254)」，否则报 10201（服务端不回退到其他套餐）

### 2026-06-22 修复封板/炸板口径 bug（涨停 103 vs 封板 61 不一致）

- **问题**：6-18 报告出现「涨停 103 家、封板 61 家、炸板率 0%」自相矛盾的数字，且结论误判为「资金封板坚决」。根因有三：
  1. **取数源用错**：`analyze_data.py` 三处（主线识别/锚点选股/情绪周期）用 `stock_top_rise.json`（涨幅榜前 100）当全市场涨停股列表，里面只有 61 只涨停股，漏掉 42 只非涨幅靠前的涨停股
  2. **炸板口径错**：用 `收盘价 < 最高价 × 0.999` 判炸板，既非交易所口径，又在数据残缺时永远输出 0%
  3. **文案无脑**：`炸板率 == 0` 就输出「资金封板坚决」，但 0% 是数据缺失造成的假象
- **方案**：
  - **fetch_data.py** 新增 `_limit_up_price`（涨停价 = ROUND(昨收 × 板块限制, 2)）、`is_sealed`（封板 = 收盘封住涨停）、`is_broken`（炸板 = 盘中 `HIGH_PRICE ≥ 涨停价` 且收盘 < 涨停价，全市场行情反推，无额外接口调用）
  - **fetch_data.py** 新增输出 `limit_up_full.json`（涨停股全集）/ `limit_broken.json`（炸板股全集）/ `limit_down_full.json`（跌停股全集，与涨停对称），meta 补 `sealed_count` / `broken_count`
  - **analyze_data.py** 三处改用 `limit_up_full`（形参同步改名，消除「榜单当全集」误导）；封板/炸板数直接取 meta 里全市场校验值；新增数据一致性自检（全集数 ≠ meta.limit_up_count 时告警，不再静默生成矛盾报告）
  - **analyze_data.py** 文案按封板率分三档（≥80% 坚决 / 60-80% 一般 / <60% 追涨风险高），不再无脑「坚决」
- **关联代码质量修复**（排查同类隐患后顺带修）：
  - **fetch_data.py** `fetch_all_pages` 加 totalCount 一致性自检：实际拉取条数 ≠ API 声明 totalCount 时告警，防止 abnormal_trade 等数据被服务端限流/截断后静默当全集用
  - **analyze_data.py** `analyze_emotion_cycle` 删除死参数（`abnormal_trade` / `stock_top_rise` 传入但函数体不使用）
- **效果**（6-18 真实数据回归）：封板 103、炸板 **53**、封板率 **66%**（一般），情绪评分 2.7→2.35（如实下调）；主线排序修正为通信设备（涨停6家）取代旧的半导体（涨停5家，被涨幅榜高估）

### 2026-06-17 修复安全扫描命中的 SSRF 与 XSS 风险（commit 3fff527）

- **SSRF**（真实）：`query.py cmd_api` 中 `api_id` 直接拼接到 URL path，存在 path traversal 风险。加正则白名单 `^[A-Za-z0-9_-]+$` 拦截；`cmd_page_size` 同步加白名单（防御深度）
- **XSS**（误报处理）：删除历史残留脚本 `generate_report.py`（109 行，已不在执行链路），同步清理 README / analyze_data.py 中的引用，从源头消除扫描命中
- 验证：path traversal payload（`../../admin/users`）和命令注入 payload（`; rm -rf /`）均被拦截；正常 api_id 调用不受影响

### 2026-06-17 涨跌停口径改为交易所封板字段

- **问题**：旧逻辑用「涨幅 ≥ 阈值 × 0.99」近似判断涨停，因创业板/科创板涨停阈值是 20%、ST 折半等规则差异，导致统计数与行情软件不一致（旧：涨停 97 / 跌停 15；实际：涨停 98 / 跌停 21）
- **方案**：
  - **fetch_data.py** `is_limit_up` / `is_limit_down` 改为直接读接口字段 `PRICE_UPDOWN_TYPE_PAR == "涨停" / "跌停"`，删除 `_get_limit_threshold` 阈值计算逻辑
  - **analyze_data.py** 同步改为接口字段判定
- **效果**：统计口径与交易所/行情软件完全一致，不再因板块差异漏算或多算

### 2026-06-17 报告生成规则收紧（不暴露内部信息 + 强制免责声明）

- **问题**：生成的报告头部混入了积分消耗、接口调用次数等内部运行信息；末尾缺免责声明；AI 结论出现"操作建议观望 / 仓位控制在半仓以下"等变相买卖指令
- **方案**：
  - **AGENT.md** Step 4「⛔ 绝对禁止事项」新增第7条（禁止暴露积分/接口次数/API KEY/手机号等内部信息）和第8条（禁止买卖指令性措辞）；「✅ 你需要完成的分析」新增第7条（必带免责声明）
  - **AGENT.md** Step 5 补充报告必须结构 + 免责声明模板原文；报告头规则收紧为「仅标题，不要写总成交/涨停/跌停概览行，不得包含数据字段名、算法口径等内部实现细节」
  - 同步删除报告中的"涨跌停口径：使用接口 PRICE_UPDOWN_TYPE_PAR 字段"等实现细节标注

### 2026-06-17 新增 Agent 路由边界与用户使用指引

- **问题**：新设备测试时，AI 在用户指令模糊（如"分析下今天市场"）的情况下，会误调用 Wind / 通用行情 / 个股分析等其他 agent，导致主线分析 agent 失效
- **方案**（三层防御，覆盖 Claude Code 内调度与 OpenClaw 等中转平台调度两种场景）：
  - **AGENT.md** 顶部新增 Step 0「适用边界判定」：明确 ✅ 命中条件（含"主线/市场主线/今日主线"等关键词或点名 agent）/ ❌ 让出场景（个股分析、单一板块、其他市场、选股策略等路由表）/ ⚠️ 模糊指令强制反问（禁止自行路由到其他 agent，宁可多一次交互）
  - **SKILL.md** description 收紧为"仅处理 A股市场整体主线结构"，并在顶部加「适用边界（路由判断必读）」表，覆盖个股/单板块/其他市场等让出场景
  - **README.md** 使用方式段重写：✅ 规范指令表（关键词"主线"为稳定触发词）+ ❌ 误路由指令表（"看看大盘/分析下今天市场"等会误调 Wind/股票分析）+ 🔀 与其他 agent 边界表

### 2026-06-17 鉴权升级为 cxdata 官方 SMS+协议确认机制（commit 37c58a4）

- **fetch_data.py** 改为 subprocess 调用官方 `query.py`（内置 token 管理、gzip 解码、积分计数、50 次硬限制），不再自行实现 HTTP 鉴权
- 新增 `auth.py / common.py / cxda_cache_cli.py / query.py`（拷自新版 cxdata-stock-market-information skill）
- **AGENT.md** 加 Step 1.5 鉴权前置（terms-check + status + SMS 引导）+ Step 2/2.5 session start/summary
- **analyze_data.py** 修复行业名匹配 bug：L2 标准名映射（处理 "白酒Ⅲ" → "白酒Ⅱ" 等后缀变体）+ 锚点 `industry` 字段填充
- 删除 `index-market-date` skill 目录（新版已合并到 cxdata-stock-market-information）
- 数据源 skill 目录统一改名为 `cxdata-` 前缀，SKILL.md/references 同步新版（scripts 空壳，避免恢复通用 `api_query.py`）
- 删除老版 `.env` / `auth.sh` / `.env.example`（鉴权改为 `~/.cxda-cache/` 共享缓存）

### 2026-06-12 移除 4 个通用 api_query.py（commit 0692fed）

- **问题**：通过 OpenClaw 执行 agent 时，LLM 看到 4 个 skill 目录下的通用 `api_query.py`，自主调用额外接口拉数据
- **方案**：`fetch_data.py` 内嵌 token + HTTP 请求 + 接口白名单（10 个主线分析必需接口），删除 4 个 skill 目录下的通用 `api_query.py`

### 2026-06-11 约束 LLM 不得篡改数值（commit 5484e66）

- **问题**：两次生成的报告数值不一致，LLM 自行修改综合评分、主线排序、锚点个股等关键数值
- **方案**：rules.md 加约束，所有数值由 Python 脚本固定，LLM 只负责文字解读

### 2026-05-26 情绪周期评分 v2.2 修复

- 广度维度（40%）：涨停数/跌停数/上涨占比分别打分再加权（不再要求三条件同时满足）
- 强度维度（35%）：综合封板数量+炸板率（不再纯看炸板率）

## 免责声明

本 Agent 仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
