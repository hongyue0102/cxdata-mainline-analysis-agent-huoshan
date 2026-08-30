# 行业代码表-通用 (getPubInduCodeByCond-G)

**API_ID:** getPubInduCodeByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 | 示例值 |
|--------|------------|----------|----------|----------|----------|
| induUniCode | 行业统一编码 | 数值类型 | 否 |  | 401302081 |
| induSysPar | 行业分类体系参数 | 数值类型 | 否 |  | 8 |
| induClassName | 行业分类名称 | 字符类型 | 否 |  | 非日常生活消费品 |
| fatUniCode | 父类行业统一编码 | 数值类型 | 否 |  | 401302081 |
| induUniCode1 | 一级行业统一编码 | 数值类型 | 否 |  | 401302081 |
| induUniCode2 | 二级行业统一编码 | 数值类型 | 否 |  | 401302081 |
| induUniCode3 | 三级行业统一编码 | 数值类型 | 否 |  | 401302081 |
| induUniCode4 | 四级行业统一编码 | 数值类型 | 否 |  | 401302081 |
| pageNum | 页码 | Integer | 是 | 1 |  |
| pageSize | 每页条数 | Integer | 是 | 20 |  |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| INDU_SYS_PAR | 行业分类体系参数 | 数值类型 |
| INDU_CLASS_NAME | 行业分类名称 | 字符类型 |
| INDU_CLASS_CODE | 行业分类代码 | 字符类型 |
| INDU_LEVEL | 行业级别 | 字符类型 |
| FAT_UNI_CODE | 父类行业统一编码 | 数值类型 |
| INDU_CLASS_DES | 行业分类说明 | 字符类型 |
| START_DATE | 开始日期 | 日期类型 |
| IS_VALID | 是否存在 | 数值类型 |
| DIS_DATE | 取消日期 | 日期类型 |
| INDU_CODE1 | 一级行业代码 | 字符类型 |
| INDU_NAME1 | 一级行业名称 | 字符类型 |
| INDU_CODE2 | 二级行业代码 | 字符类型 |
| INDU_NAME2 | 二级行业名称 | 字符类型 |
| INDU_CODE3 | 三级行业代码 | 字符类型 |
| INDU_NAME3 | 三级行业名称 | 字符类型 |
| INDU_CODE4 | 四级行业代码 | 字符类型 |
| INDU_NAME4 | 四级行业名称 | 字符类型 |


