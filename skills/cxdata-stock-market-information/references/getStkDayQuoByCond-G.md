# 交易所股票日行情-通用 (getStkDayQuoByCond-G)

**API_ID:** getStkDayQuoByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 | 示例值 |
|--------|------------|----------|----------|----------|----------|
| stkCode | 股票代码 | 字符类型 | 否 |  | 002052 |
| stkShortName | 股票简称 | 字符类型 | 否 |  | 同洲电子 |
| tradeDate | 交易日期 | 日期类型(yyyy-MM-dd) | 否 |  | 2026-06-09 |
| pageNum | 页码 | Integer | 是 | 1 |  |
| pageSize | 每页条数 | Integer | 是 | 20 |  |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| STK_CODE | 股票代码 | 字符类型 |
| STK_SHORT_NAME | 股票简称 | 字符类型 |
| TRADE_DATE | 交易日期 | 日期类型 |
| PRE_CLOSE_PRICE | 昨收盘价 | 数值类型 |
| OPEN_PRICE | 开盘价 | 数值类型 |
| TRADE_AMUT | 成交金额 | 数值类型 |
| HIGH_PRICE | 最高价 | 数值类型 |
| LOW_PRICE | 最低价 | 数值类型 |
| CLOSE_PRICE | 收盘价 | 数值类型 |
| TRADE_VOL | 成交数量 | 数值类型 |
| PRICE_LIMIT | 价格涨跌幅 | 数值类型 |
| PRICE_UPDOWN_TYPE_PAR | 涨跌幅状态参数 | 数值类型 |
| TRADE_VOL_AFTER | 	盘后成交量 | 数值类型 |
| TRADE_AMUT_AFTER | 盘后成交额 | 数值类型 |


