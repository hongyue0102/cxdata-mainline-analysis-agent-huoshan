# 证监会、申万行业分类-通用 (getDPubInduCodeByCond-G)

**API_ID:** getDPubInduCodeByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 | 示例值 |
|--------|------------|----------|----------|----------|----------|
| induUniCode | 行业统一编码 | 数值类型 | 否 |  | 401302246 |
| induSysPar | 行业分类体系 | 数值类型 | 否 |  | 10 |
| pageNum | 页码 | Integer | 是 | 1 |  |
| pageSize | 每页条数 | Integer | 是 | 20 |  |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| INDU_UNI_CODE | 行业统一编码 | 数值类型 |
| INDU_SYS_PAR | 行业分类体系 | 数值类型 |
| INDU_CODE1 | 一级行业代码 | 字符类型 |
| INDU_NAME1 | 一级行业名称 | 字符类型 |
| INDU_CODE2 | 二级行业代码 | 字符类型 |
| INDU_NAME2 | 二级行业名称 | 字符类型 |
| INDU_CODE3 | 三级行业代码 | 字符类型 |
| INDU_NAME3 | 三级行业名称 | 字符类型 |
| INDU_CODE4 | 四级行业代码 | 字符类型 |
| INDU_NAME4 | 四级行业名称 | 字符类型 |

#### 直接前置依赖
以下参数存在可参考的直接前置接口。是否调用前置接口，取决于当前查询目标、已知条件以及当前接口入参是否已满足。
- 参数 `induUniCode`：可通过调用 **行业代码表-通用（API_ID:getPubInduCodeByCond-G）** 获取

#### 多流程依赖说明
当当前接口的关键入参存在多种补齐方式时，可按以下流程逐级调用，不要预先串行调用所有上游接口。
##### 流程1（补齐参数 `induUniCode`）
1. 调用 **行业代码表-通用（API_ID:getPubInduCodeByCond-G）**，补齐后续所需参数 `induUniCode`
2. 调用 **证监会、申万行业分类-通用（API_ID:getDPubInduCodeByCond-G）**，完成当前查询

