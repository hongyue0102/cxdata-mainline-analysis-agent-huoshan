---
name: cxdata-public-opinion-stock-index
description: 存储上交所、深交所、北交所上市公司舆情新闻指数、上市公司新闻热度榜等。包括股票代码，舆情统计时间，敏感舆情指数，中性舆情指数等信息。
metadata:
  version: "1.0.5"
  author: "财新数据"
  website: "guzhi.io"
  tags: ["positive-sentiment", "negative-sentiment", "neutral-sentiment", "public-opinion"]
---

# cxdata-public-opinion-stock-index

> 财新数据官方 Skill，提供接口数据查询与数据整合能力。

## 使用场景

- 用户查询上市公司每日敏感舆情指数信息。包含指数日期、股票代码、股票名称、新闻标题、今日指数、昨日指数、周平均指数、周波动、周市场平均、周市场波动、负面信息总数、主要负面信息总数、格式化后的标题、股票简称、更新日期、详情地址链接、业务分类、业务小分类等维度
- 用户查询上市公司每日正面舆情指数信息。包含指数日期、股票代码、股票名称、新闻标题、今日指数、昨日指数、周平均指数、周波动、周市场平均、周市场波动、负面信息总数、主要负面信息总数、格式化后的标题、股票简称、更新日期、详情地址链接、业务分类、业务小分类等维度

---

## 环境准备

本 Skill 的命令位于与本文件同级的 `scripts/` 目录，**无需配置任何环境变量**。
按下文命令执行即可完成认证、查询、分页、套餐额度查询与响应解析。

- **调用方式**：用你所在平台的 Python（`python` 或 `python3`）直接执行脚本路径即可。
  - macOS / Linux：`python3 ./scripts/query.py ...`
  - Windows PowerShell：`python .\scripts\query.py ...`
  - 路径含空格时加引号。
- **记法约定**：下文命令中的 `$PYTHON`、`$AUTH_SCRIPT`、`$QUERY_SCRIPT` 仅为占位记法，
  分别代表「你的 Python 解释器」「`scripts/auth.py`」「`scripts/query.py`」，请按你的平台等价替换。

---

## 鉴权说明

**火山部署版鉴权方式为环境变量**：运行环境中配置 `CXDA_USER_KEY` 环境变量即可自动认证，无需 SMS 验证码登录。

**鉴权检查（一条命令即可）：**

```bash
$PYTHON "$AUTH_SCRIPT" status
```

- `authenticated: true`（`auth_source`=`env_var`）→ 环境变量已配置，**直接进入业务查询**
- `authenticated: true`（`auth_source`=`cache`）→ 本地缓存有效，**直接进入业务查询**
- `authenticated: false` → **请确认环境变量 CXDA_USER_KEY 是否已正确配置**，或通过 SMS 流程认证（send-code + verify）

> **火山部署说明**：环境变量 `CXDA_USER_KEY` 优先级最高，配置后自动隐式接受服务协议、自动认证，无需手动 terms-check/terms-accept 或 SMS 登录。

> **安全提示**：`status` 输出的 `CXDA_USER_KEY` 已脱敏（仅显示前4后4字符），不要向用户展示或记录该字段。

---

## 执行标准流程

当本 Skill 被触发后，按以下唯一主流程执行：

1. **确认认证状态**：本轮首次业务查询前执行 `status`。未认证时确认环境变量 `CXDA_USER_KEY` 是否已配置；认证失败且无法继续时停止，不调用业务接口。

2. **选择最小必要接口**：在下方「接口清单」中选定目标 API_ID，并先阅读其接口文档（接口清单「接口文档」列，路径形如 `references/{API_ID}.md`）。优先选择能直接满足问题的最少接口，不要预先串行调用所有可能相关的接口。

3. **校验入参与前置依赖**：严格按接口文档定义的入参字段组织参数；不得使用文档中不存在的接口或字段。缺少必填入参时，优先向用户询问；只有接口文档明确存在前置依赖、且当前查询目标需要补齐该字段时，才调用前置接口。

4. **（按需）确认分页大小**：若结果可能超过默认条数、需要大量数据或较长时间段数据，先按下文「分页获取」查询该接口的 maxPageSize，再设置 `pageNum` / `pageSize`。

5. **开始积分会话**：本轮首次业务 `api` 调用前执行一次 `$PYTHON "$QUERY_SCRIPT" session start`，重置本轮积分账本。

6. **调用统一查询工具**

```bash
$PYTHON "$QUERY_SCRIPT" api <API_ID> key=value [key=value ...]
```
- 所有业务接口统一使用 `api` 子命令，参数采用 `key=value` 格式
- 命令输出为格式化 JSON，无需手动处理 token 或解码响应
- 若输出 `status: "confirmation_required"`，说明本轮会话已有 50 次成功计费接口调用。必须暂停并询问用户是否确认继续调用，用户确认后先执行 `$PYTHON "$QUERY_SCRIPT" session confirm`，再继续调用 `api`。

7. **解析结果与单次消耗**：将输出的 JSON 数据解析后呈现给用户；每次成功且 `consumePoints > 0` 时，按「积分消耗提示」播报本次消耗。

8. **最终汇总**：当已经获得足够数据并准备给用户最终答案时，视为本轮查询完成；如果本轮发生过业务接口调用，执行 `$PYTHON "$QUERY_SCRIPT" session summary`，按「积分消耗提示」汇总本轮消耗和套餐剩余额度。

9. **失败停止边界**：认证失败、权限不足、缺少关键入参、前置接口无结果、接口返回错误或输出为空时，不要盲目重复调用；先按「故障排除」说明原因，必要时向用户补充询问。

---

## 积分消耗提示（**会话调用了接口时必须执行**）

> 用于让用户清楚每次调用的积分消耗与整轮会话的累计消耗。积分明细从命令输出读取，会话统计以 `session summary` 返回为准。

**会话开始**（本轮首次业务 `api` 调用前，执行一次以重置积分账本）：

```bash
$PYTHON "$QUERY_SCRIPT" session start
```

**超过 50 次调用确认**：当 `api` 返回 `status: "confirmation_required"` 时，必须先向用户说明「本轮会话已成功调用 50 次计费接口，继续调用消耗积分可能超出预期」，并询问是否继续。只有用户明确确认后，才执行：

```bash
$PYTHON "$QUERY_SCRIPT" session confirm
```

执行成功后可继续原业务查询；用户未确认或拒绝时停止继续调用接口。

**每次调用后播报**：从 `api` 返回的 JSON 中读取消耗字段（成功时 `code` 为 `10000`，消耗字段为 `consumePoints`）：
- 成功且 `consumePoints > 0` → 告知用户：「已调用接口 {接口名称}，本次消耗 {consumePoints} 积分。」
- 成功但消耗为 0 → 正常返回数据，**不提积分消耗**。
- 失败（`code != 10000`）→ 按故障排除处理，**不提积分消耗**（失败不计费）。

**会话结束时汇总**（准备给用户最终答案前，如果本轮发生过业务接口调用，必须进行汇总）：

```bash
$PYTHON "$QUERY_SCRIPT" session summary
```
- 读取 `call_count`（会话调用接口数量）与 `total_consumed`（本次会话累计消耗），告知用户：「本次会话共调用 {call_count} 次接口，累计消耗 {total_consumed} 积分。」
- 同时读取 `packages` 逐套餐播报剩余额度，按「套餐展示模板」展示总量积分与每日额度。
- 不同套餐的剩余积分不能混合合计，不要输出总剩余额度。
- 如果 `package_error` 非空，只汇总本次会话调用次数和累计消耗，并提示套餐清单获取失败。
- 消耗提示与套餐剩余额度提示必须同时进行，且必须在会话结束时进行汇总提示**不允许在会话中途或调用接口后单独提示套餐剩余额度**。

> 仅「成功且消耗 > 0」的调用计入会话统计；失败与 0 消耗均不计入。当已经获得足够数据并准备回复用户时，视为本轮查询完成，并以 `session summary` 汇总本轮消耗与套餐剩余额度。

`session summary` 固定返回示例：

```json
{
  "success": true,
  "session_start": "2026-06-09 14:00:00",
  "call_count": 2,
  "total_consumed": 12,
  "calls": [
    {
      "time": "2026-06-09 14:01:10",
      "api_id": "getStkBasicInfoByCond-K",
      "consumed": 5
    },
    {
      "time": "2026-06-09 14:02:10",
      "api_id": "getCooWineCateDailQuoByWineName",
      "consumed": 7
    }
  ],
  "package_count": 1,
  "packages": [
    {
      "source_type": "人工添加",
      "package_name": "测试套餐(高)",
      "balance": 1000,
      "total_money": 1000,
      "integral": "1000/1000",
      "day_balance": 1000,
      "day_money": 1000,
      "valid_end": "2027-06-30 13:56:05"
    }
  ],
  "package_error": null
}
```

---

## 默认分页（强约束）
当用户不主动提出分页参数需求时，必须优先使用references中接口的默认分页参数

## 分页获取（按需）

每个接口允许返回的最大条数（maxPageSize）不同。**当查询结果可能超过默认条数、需要获取大量数据或较长时间段的数据时，必须先查询该接口的最大 pageSize，再用 pageSize 参数指定返回条数，否则数据会被截断。**

```bash
$PYTHON "$QUERY_SCRIPT" page-size <API_ID>
```
返回示例：`{"msg":"请求成功","code":"10000","maxPageSize":100}`，此时调用接口时可传 `pageSize=100`。

---

## 套餐额度查询

查询用户已开通套餐及剩余额度时，使用：

```bash
$PYTHON "$QUERY_SCRIPT" package
$PYTHON "$QUERY_SCRIPT" package --api-main <API_ID>
```

套餐展示模板（字段为空、`null` 或 `-` 时不展示对应行或片段）：

```text
{package_name}（来源：{source_type}）
总量积分：剩余 {balance} / 总积分 {total_money}
每日额度：每日剩余 {day_balance} / 每日积分 {day_money}
到期时间：{valid_end}
```

展示规则：
- `source_type` 为空时，不展示「来源」。
- `balance`、`total_money` 都有值时展示为「总量积分：剩余 {balance} / 总积分 {total_money}」；只有一个字段有值时，只展示该字段。
- `day_balance`、`day_money` 都有值时展示为「每日额度：每日剩余 {day_balance} / 每日积分 {day_money}」；只有一个字段有值时，只展示该字段。
- `valid_end` 为空时，不展示到期时间。

固定返回示例：

```json
{
  "code": "10000",
  "msg": "返回权限清单成功",
  "package_count": 1,
  "packages": [
    {
      "relation_id": 161,
      "user_id": 425,
      "package_id": 92,
      "package_name": "测试套餐(高)",
      "package_code": "TEST_PACKAGE",
      "source_type": "人工添加",
      "status": "2",
      "valid_start": "2026-06-08 13:56:02",
      "valid_end": "2027-06-30 13:56:05",
      "total_money": 1000,
      "balance": 1000,
      "day_balance": 1000,
      "day_money": 1000
    }
  ]
}
```

## 接口清单
> ⚠️ **注意事项**：
> 1. 所有接口输入输出需要严格按照接口文档规范
> 2. 所有接口标识必须严格按照 API_ID 进行请求，不得杜撰不存在的接口
> 3. 调用接口之前必须阅读接口文档,所有接口输入参数必须严格遵循文档中的输入字段
> 4. 不得修改、编造接口输出的返回值

| 接口名称 | 接口文档 | API_ID | 接口描述 |
|----------|----------|--------|----------|
| 敏感舆情指数表-通用 | ./references/getIndexLyricalList1ByCond-G.md | getIndexLyricalList1ByCond-G | 存储上市公司每日敏感舆情指数信息。包含指数日期、股票代码、股票名称、新闻标题、今日指数、昨日指数、周平均指数、周波动、周市场平均、周市场波动、负面信息总数、主要负面信息总数、格式化后的标题、股票简称、更新日期、详情地址链接、业务分类、业务小分类等维度。 |
| 正面舆情指数表-通用 | ./references/getIndexLyricalList2ByCond-G.md | getIndexLyricalList2ByCond-G | 存储上市公司每日正面舆情指数信息。包含指数日期、股票代码、股票名称、新闻标题、今日指数、昨日指数、周平均指数、周波动、周市场平均、周市场波动、负面信息总数、主要负面信息总数、格式化后的标题、股票简称、更新日期、详情地址链接、业务分类、业务小分类等维度。 |

## 字段与调用约定

- **相同含义字段说明**：ORG_UNI_CODE==COM_UNI_CODE；STK_UNI_CODE==BOND_UNI_CODE；如无明确说明股票代码不需要携带 SH、HK 等交易所代码。
- **接口输入字段不明确**：接口输入参数是 ORG_UNI_CODE、STK_UNI_CODE 等参数时可以先通过对应的机构信息、股票信息基础接口调用尝试获取，获取不到时反馈并停止。
- **多接口查询边界**：一次只调用当前问题所需的最小接口集合。除非接口文档明确要求，或当前接口缺少必填入参，否则不要为了“可能有用”而调用上游或同类接口。

## 故障排除

- **未认证 / 调用失败**：执行 `$PYTHON "$AUTH_SCRIPT" status` 确认认证状态；未认证时按 `references/auth-flow.md` 完成协议确认与登录，并确认网络连接正常。
- **输出为空**：确认输入参数是否正确，检查 API_ID 是否匹配查询类型。
- **权限问题**：接口返回无权限或者权限到期时，提示用户前往 `https://yun.ccxe.com.cn/` 联系客服。
- **套餐、积分问题**：返回套餐到期、积分不足、没有套餐、套餐渠道受限等情况时，提示用户前往`https://store.ccxe.com.cn/`财新数据商城购买套餐
- **参数缺失 / 前置无结果**：缺少关键入参或前置接口查不到结果时，停止继续调用并向用户说明需要补充的信息。
- **避免无效重试**：认证失败、权限不足、参数缺失、上游无结果或接口明确返回错误时，不要重复消耗接口调用；先处理原因或询问用户。
- **命令路径问题**：文档中 `$AUTH_SCRIPT`、`$QUERY_SCRIPT` 等为「环境准备」中定义的变量，请确认已正确定位到 Skill 目录。
- **接口错误码对照**：接口返回错误码时，错误描述示例参照：http://cxapi.ccxe.com.cn/cxda/mall/visitshop_preview.htm?downType=errorCode
