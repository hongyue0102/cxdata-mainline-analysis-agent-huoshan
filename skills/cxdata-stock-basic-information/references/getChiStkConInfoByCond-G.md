# 境外上市主体关联表-通用 (getChiStkConInfoByCond-G)

**API_ID:** getChiStkConInfoByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 | 示例值 |
|--------|------------|----------|----------|----------|----------|
| marCode | 证券代码 | 字符类型 | 否 |  | CXDC |
| secShortName | 证券简称 | 字符类型 | 否 |  | 鑫达集团 |
| secMarPar | 证券市场参数 | 数值类型 | 否 |  | 9 |
| comChiName | 所属国内公司名称 | 字符类型 | 否 |  | 河北鑫达钢铁集团有限公司 |
| pageNum | 页码 | Integer | 是 | 1 |  |
| pageSize | 每页条数 | Integer | 是 | 20 |  |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| MAR_CODE | 证券代码 | 字符类型 |
| SEC_SHORT_NAME | 证券简称 | 字符类型 |
| ORG_ENG_NAME | 公司英文名称 | 字符类型 |
| ORG_CHI_NAME | 公司中文名称 | 字符类型 |
| SEC_MAR_PAR | 证券市场参数 | 数值类型 |
| LIST_STA_PAR | 上市状态参数 | 数值类型 |
| LIST_DATE | 上市日期 | 日期类型 |
| QUIT_DATE | 退市日期 | 日期类型 |
| COM_CHI_NAME | 所属国内公司名称 | 字符类型 |
| IS_LIST_US | 是否赴美上市 | 数值类型 |


