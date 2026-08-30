# 股票上市状态变动-通用 (getStkListStaChanByCond-G)

**API_ID:** getStkListStaChanByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 | 示例值 |
|--------|------------|----------|----------|----------|----------|
| stkCode | 股票代码 | 字符类型 | 否 |  | 600128 |
| stkShortName | 股票简称 | 字符类型 | 否 |  | 苏豪弘业 |
| chanDate | 变动日期 | 日期类型(yyyy-MM-dd) | 否 |  | 1997-09-01 |
| listStaChanTypePar | 上市状态变动类型 | 数值类型 | 否 |  | 1 |
| pageNum | 页码 | Integer | 是 | 1 |  |
| pageSize | 每页条数 | Integer | 是 | 20 |  |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| STK_CODE | 股票代码 | 字符类型 |
| STK_SHORT_NAME | 股票简称 | 字符类型 |
| CHAN_DATE | 变动日期 | 日期类型 |
| LIST_STA_CHAN_TYPE_PAR | 上市状态变动类型 | 数值类型 |
| SEC_MAR_PAR | 证券市场类型 | 数值类型 |


