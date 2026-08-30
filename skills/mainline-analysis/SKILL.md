---
name: mainline-analysis
description: A股市场主线识别系统。自动拉取指数行情、行业涨跌、个股行情等数据，经结构化分析后生成六段式主线识别报告。仅处理"A股市场整体主线结构"分析（板块/主线/情绪周期），不处理个股分析、单一板块分析、其他市场。触发词：今日主线、市场主线、主线识别、主线分析、每日主线、A股主线。
---

# 🎯 适用边界（路由判断必读）

**本 Skill 仅处理**：用户明确要求分析 **A股市场整体的主线结构 / 市场情绪周期 / 板块强弱对比**。

**以下场景必须由其他 Agent/Skill 处理，本 Skill 不得接管**：

| 用户意图 | 正确路由 |
|---|---|
| 分析某只个股（基本面/财报/估值）| → cxdata-stock-analysis-agent |
| 查询单只股票最新行情/K线 | → Wind / 行情查询 agent |
| 分析单一板块（如"电子板块分析"）| → 板块分析 agent |
| 港股/美股/期货/加密货币 | → 对应市场 agent |
| 回测 / 选股 / 交易策略 | → 策略类 agent |

**当用户指令模糊时**（如"分析下今天市场"、"看看大盘"、"今天怎么样"），**禁止自行选其他 agent 执行**，必须先反问用户：

> 您是想分析今日 **A股市场主线结构**（板块/情绪/锚点）吗？如果是，请回复"今日主线"或"主线识别 YYYY-MM-DD"，我将调用市场主线分析 agent。如果是其他需求（个股分析、单板块、其他市场），请明确告知。

---

# 执行标准程序 (Recommended Workflow)

当用户要求分析市场主线时，按以下步骤执行：

## Step 1: 数据获取

运行数据获取脚本：

```bash
cd <Agent目录>/skills/mainline-analysis/scripts && python3 fetch_data.py <日期>
```

> `<Agent目录>` 为本 Agent 解压后的根目录路径。

日期格式 YYYY-MM-DD，不传则默认最近一个交易日。脚本会自动拉取全部所需数据到 `scripts/data/<日期>/` 目录（约 10-30 秒，进程内取数 + 连接复用）。同一交易日重复运行命中缓存近乎秒回。

## Step 2: 数据分析

```bash
cd <Agent目录>/skills/mainline-analysis/scripts && python3 analyze_data.py <日期>
```

生成结构化分析结果 `scripts/data/analysis.json`。

## Step 3: 你（Agent LLM）生成报告

基于 analysis.json 的数据，按照六段式模板生成 Markdown 报告。

### ⛔ 绝对禁止事项

1. **禁止篡改 Python 计算的数值**：`composite_score`、涨幅数据、涨停股数量、`line_type`、市场状态、情绪阶段、锚点个股列表等必须 100% 原样使用
2. **禁止自行选取或增减锚点个股**：必须直接使用 `anchors` 列表，不得添加、删除或替换
3. **禁止自行判断主线排序**：核心主线 = `main_lines[0]`，第二主线 = `main_lines[1]`，严格按 `composite_score` 降序
4. **报告不得包含催化/舆情段落**：舆情数据源已移除，不得自行推测编造催化原因
5. **禁止编造个股名称或数据**：每只股票必须存在于 `limit_up_details` 或 `anchors` 中
6. **禁止展示情绪评分计算过程**：只输出 `emotion.phase` + 一句话定性
7. **禁止自创关键判断/观察点/总结句**：以下 Python 结构化字段必须严格引用，不得修改/编造/遗漏：
   - `market_summary.one_line`：「一句话 AI 结论」必须以此句开头
   - `observation_points`：「明日观察重点」必须逐条涵盖全部
   - `key_judgments`：必须在报告相应段落引用
8. **禁止自创历史对比**：不得写"较前日翻倍"等跨日对比描述（Python 不做历史对比）
9. **次级热点表格不得漏填字段**：`secondary_hot` 的 day/week/month_change 必须全部填入表格，不得用 "—" 占位

### 你需要完成的分析：

1. **市场环境**：指数行情表格数值来自 `index_quotes`；环境判断使用 `environment.status`；AI结论使用 `environment.action`；撰写环境解读文字（含 `key_judgments` 中相关判断）
2. **当前主线**：核心主线 = `main_lines[0]`，第二主线 = `main_lines[1]`，数值直接引用；撰写资金态度和板块点评
3. **次级热点**：从 `secondary_hot` 优先选"资金攻击型"；**day/week/month_change 全部填表**，不得漏填
4. **核心锚点个股**：直接使用 `anchors` 列表输出表格，不得修改
5. **情绪周期**：只输出 `emotion.phase` + 一句话定性
6. **明日观察重点**：基于 `observation_points` 全部条目展开（措辞可润色），不得遗漏或添加
7. **一句话AI结论**：**以 `market_summary.one_line` 开头**，可补充环境含义解读

### 综合评分公式（v3.1）

综合得分 = 日涨幅排名分(30%) + 涨停集中度得分(30%) + 周涨幅趋势分(20%) + 月涨幅趋势分(20%)

---

# 配置说明

## 数据源
本技能已内置 4 个数据源 skill，无需额外安装：

| Skill | 用途 |
|-------|------|
| stock-market-information | 行情、行业涨跌、情绪温度、异动、市值 |
| stock-basic-information | 个股申万行业分类 |
| industry-classification-company | 行业代码表（申万三级→二级映射） |
| index-market-date | 三大指数日线行情 |

**火山部署版**：仅需配置环境变量 `CXDA_USER_KEY`（财新数据平台用户密钥），脚本自动认证，无需 SMS 登录或 `.env` 文件。所有内置数据源 skill 共用此密钥，通过环境变量自动传递。

- `CXDA_USER_KEY`：16-128 位字母数字下划线连字符，通过环境变量传入
- `BASE_URL`：API 基础地址（默认 `https://cxapi.ccxe.com.cn/cxda`）

---

# 故障排除

- **数据源未配置**: 检查环境变量 `CXDA_USER_KEY` 是否已设置
- **ModuleNotFoundError**: 需要安装依赖 → `pip install python-dotenv cryptography`
- **数据获取失败**: 确认网络连接正常，检查 CXDA_USER_KEY 是否有效

---

# 输出结构（六段式）

1. **市场环境** — 指数强弱、涨跌家数、成交额变化、情绪判断
2. **当前主线** — 核心主线 + 第二主线，区分资金攻击型/趋势防御型
3. **次级热点** — 1个次级方向
4. **核心锚点个股** — 5-8只，标注情绪标的/趋势中军/补涨标的
5. **当前情绪** — 冰点/调整/修复/主升/高潮
6. **一句话交易结论** — 核心操作建议
