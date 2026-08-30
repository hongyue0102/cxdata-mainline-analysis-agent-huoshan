# 上市公司从属申万行业变动表-通用 (getPubComInduChanSwByCond-G)

**API_ID:** getPubComInduChanSwByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 | 示例值 |
|--------|------------|----------|----------|----------|----------|
| stkCode | 股票代码 | 字符类型 | 否 |  | 002997 |
| stkShortName | 股票简称 | 字符类型 | 否 |  | *ST荣控 |
| induUniCode | 行业统一编码 | 数值类型 | 否 |  | 401302081 |
| pageNum | 页码 | Integer | 是 | 1 |  |
| pageSize | 每页条数 | Integer | 是 | 20 |  |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| STK_CODE | 股票代码 | 字符类型 |
| STK_SHORT_NAME | 股票简称 | 字符类型 |
| INDU_UNI_CODE | 行业统一编码 | 数值类型 |
| START_DATE | 开始日期 | 日期类型 |
| END_DATE | 截止日期 | 日期类型 |
| INDU_SYS_PAR | 行业分类体系参数 | 数值类型 |


