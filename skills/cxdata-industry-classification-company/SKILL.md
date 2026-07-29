---
name: cxdata-industry-classification-company
description: 行业代码表查询。通过行业分类名称查询多分类体系（申万/GICS/中诚信/恒生等）的行业代码与层级映射，用于将申万三级行业名映射到申万二级行业名与代码。
tags: ["industry-classification", "sw-industry", "industry-code-mapping"]
---

# cxdata-industry-classification-company

本 Skill 提供行业代码表查询接口，支持将行业名称映射到不同分类体系（申银万国、GICS、中诚信、恒生等）的各层级代码与名称。

主要用途：
- 通过申万三级行业名（`INDU_CLASS_NAME_S`）查询行业代码表，从返回的多条记录中筛选申万体系记录，获取申万二级行业名（`INDU_NAME2`）与代码（`INDU_CODE2`）
- 同一行业名在不同分类体系下有不同的层级代码和名称，必须按 `INDU_SYS_PAR` 筛选所需体系

## 接口清单

| 接口中文名 | 参考文档 | API_ID | 说明 |
|------------|----------|--------|------|
| 行业代码表-通用 | ./references/getPubInduCodeByCond-G.md | getPubInduCodeByCond-G | 通过行业分类名称查询多分类体系的行业代码与层级映射。同一行业名返回多条不同分类体系记录（申万/GICS/中诚信/恒生等），需按 INDU_SYS_PAR 筛选。 |

## 使用注意事项

- **同一行业名返回多条记录**：`induClassName=半导体` 会返回申万、GICS、中诚信、恒生等多条记录，必须通过 `INDU_SYS_PAR` 筛选所需分类体系
- **申万体系筛选**：优先筛选 `INDU_SYS_PAR` 含「申银万国」+「2021」的记录，其次任意申万版本
- **GICS 口径不一致**：GICS 的二级名（如「半导体产品与设备」）与申万二级名（「半导体」）不同，不可混用
