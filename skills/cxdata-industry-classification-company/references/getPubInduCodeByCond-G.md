# 行业代码表-通用 (getPubInduCodeByCond-G)

**API_ID:** getPubInduCodeByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 |
|--------|------------|----------|----------|----------|
| induClassName | 行业分类名称 | 字符类型 | 否 |  |
| pageNum | 页码 | Integer | 是 | 1 |
| pageSize | 每页条数 | Integer | 是 | 20 |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| INDU_CLASS_NAME | 行业分类名称 | 字符类型 |
| INDU_SYS_PAR | 行业分类体系参数 | 字符类型 |
| INDU_LEVEL | 行业级别 | 字符类型 |
| IS_VALID | 是否有效 | 字符类型 |
| INDU_CODE1 | 一级行业代码 | 字符类型 |
| INDU_NAME1 | 一级行业名称 | 字符类型 |
| INDU_CLASS_NAME1 | 一级行业分类名称 | 字符类型 |
| INDU_CODE2 | 二级行业代码 | 字符类型 |
| INDU_NAME2 | 二级行业名称 | 字符类型 |
| INDU_CODE3 | 三级行业代码 | 字符类型 |
| INDU_NAME3 | 三级行业名称 | 字符类型 |
| INDU_CODE4 | 四级行业代码 | 字符类型 |
| INDU_NAME4 | 四级行业名称 | 字符类型 |
| INDU_CLASS_CODE | 行业分类代码 | 字符类型 |
| INDU_CLASS_DES | 行业分类描述 | 字符类型 |
| START_DATE | 生效日期 | 日期类型 |
| DIS_DATE | 失效日期 | 日期类型 |

#### 说明

- 同一 `induClassName` 可能返回多条记录，分别对应不同分类体系（申银万国、GICS、中诚信、恒生等），需通过 `INDU_SYS_PAR` 筛选所需体系
- 申万 2021 版体系名称格式为：`申银万国行业分类标准(2021)`
- 需授权「股票库定制套餐(largeType-254)」，否则报 10201
