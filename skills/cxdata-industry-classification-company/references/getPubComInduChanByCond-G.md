# 公司从属行业变动表-通用 (getPubComInduChanByCond-G)

**API_ID:** getPubComInduChanByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 | 示例值 |
|--------|------------|----------|----------|----------|----------|
| comUniCode | 公司统一编码 | 数值类型 | 否 |  | 200000074 |
| induUniCode | 行业统一编码 | 数值类型 | 否 |  | 401302552 |
| induSysPar | 行业分类体系参数 | 数值类型 | 否 |  | 10 |
| pageNum | 页码 | Integer | 是 | 1 |  |
| pageSize | 每页条数 | Integer | 是 | 20 |  |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| COM_UNI_CODE | 公司统一编码 | 数值类型 |
| INDU_UNI_CODE | 行业统一编码 | 数值类型 |
| START_DATE | 开始日期 | 日期类型 |
| END_DATE | 截止日期 | 日期类型 |
| INDU_SYS_PAR | 行业分类体系参数 | 数值类型 |

#### 直接前置依赖
以下参数存在可参考的直接前置接口。是否调用前置接口，取决于当前查询目标、已知条件以及当前接口入参是否已满足。
- 参数 `induUniCode`：可通过调用 **行业代码表-通用（API_ID:getPubInduCodeByCond-G）** 获取
- 参数 `comUniCode`：可通过调用 **机构基本信息-ES（API_ID:getPubOrgInfoByCond-ES）** 获取
- 参数 `comUniCode`：可通过调用 **机构基本信息-通用（API_ID:getPubOrgInfoByCond-G）** 获取

#### 多流程依赖说明
当当前接口的关键入参存在多种补齐方式时，可按以下流程逐级调用，不要预先串行调用所有上游接口。
##### 流程1（补齐参数 `induUniCode`）
1. 调用 **行业代码表-通用（API_ID:getPubInduCodeByCond-G）**，补齐后续所需参数 `induUniCode`
2. 调用 **公司从属行业变动表-通用（API_ID:getPubComInduChanByCond-G）**，完成当前查询

##### 流程2（补齐参数 `comUniCode`）
1. 调用 **机构基本信息-ES（API_ID:getPubOrgInfoByCond-ES）**，补齐后续所需参数 `comUniCode`
2. 调用 **公司从属行业变动表-通用（API_ID:getPubComInduChanByCond-G）**，完成当前查询

##### 流程3（补齐参数 `comUniCode`）
1. 调用 **机构基本信息-通用（API_ID:getPubOrgInfoByCond-G）**，补齐后续所需参数 `comUniCode`
2. 调用 **公司从属行业变动表-通用（API_ID:getPubComInduChanByCond-G）**，完成当前查询

