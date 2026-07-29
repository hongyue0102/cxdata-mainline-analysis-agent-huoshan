# 认证流程详细说明

> 本文件由 SKILL.md 主流程按需引用，不可独立执行。

---

## 环境变量鉴权（火山部署版）

> **火山部署版**：`CXDA_USER_KEY` 通过环境变量配置，无需 SMS 验证码登录。环境变量优先级最高，配置后自动隐式接受服务协议、自动认证。

**鉴权检查（一条命令即可）：**

```bash
$PYTHON "$AUTH_SCRIPT" status
```

**返回结果：**
- `authenticated: true`（`auth_source`=`env_var`）→ 环境变量已配置，**直接进入业务查询**
- `authenticated: true`（`auth_source`=`cache`）→ 本地缓存有效，**直接进入业务查询**
- `authenticated: false` → 请确认环境变量 `CXDA_USER_KEY` 是否已正确配置

> 环境变量 `CXDA_USER_KEY` 优先级高于本地缓存，常见部署方式：
> - 云平台环境变量配置面板（如火山引擎）
> - 容器环境变量（Docker/K8s env）
> - Shell 环境变量（`export CXDA_USER_KEY=xxx`）
