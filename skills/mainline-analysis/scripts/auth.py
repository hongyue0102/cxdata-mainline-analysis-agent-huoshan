# -*- coding: utf-8 -*-
"""
CXDA Skill 授权模块（火山部署版）

提供服务协议确认、认证状态管理能力。
火山部署版通过环境变量 CXDA_USER_KEY 自动认证，无需 SMS 登录。

用法：
  python auth.py terms-check                      # 检查协议接受状态
  python auth.py terms-accept                     # 接受服务协议
  python auth.py terms-decline                    # 拒绝服务协议
  python auth.py status                           # 查看认证状态
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (
    BASE_URL,
    HEADERS,
    PROXIES,
    REQUEST_CHANNEL,
    get_user_key,
    set_user_key,
    get_cached_auth,
    save_auth,
    check_terms_accepted,
    mask_user_key,
)


# ── 审计日志 ──────────────────────────────────────────────────────────
_AUDIT_CONTROL_RE = re.compile(r"[\r\n\t\x00-\x1f\x7f]")


def _audit_scrub(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        return {k: _audit_scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_audit_scrub(v) for v in value]
    return _AUDIT_CONTROL_RE.sub(" ", str(value))


_audit_logger = logging.getLogger("cxda.auth.audit")
if not _audit_logger.handlers:
    _audit_handler = logging.StreamHandler(sys.stderr)
    _audit_handler.setFormatter(logging.Formatter("%(message)s"))
    _audit_logger.addHandler(_audit_handler)
    _audit_logger.setLevel(logging.INFO)
    _audit_logger.propagate = False


def _audit(op: str, success: bool, **meta):
    try:
        entry = {
            "ts": int(time.time()),
            "op": _audit_scrub(op),
            "success": bool(success),
            "meta": _audit_scrub(meta) if meta else {},
        }
        _audit_logger.info(json.dumps(entry, ensure_ascii=False))
    except Exception:
        pass


# ── 常量 ──────────────────────────────────────────────────────────────

TERMS_ACCEPTED_KEY = "terms_accepted"

PRIVACY_URL = "https://cdp.ccxe.com.cn/clause/privacy"
SERVICE_URL = "https://cdp.ccxe.com.cn/clause/service"
VIP_URL = "https://cdp.ccxe.com.cn/clause/vip"


# ── 命令：terms-check ─────────────────────────────────────────────────

def cmd_terms_check():
    """检查用户是否已接受服务协议"""
    user_key = get_user_key()
    if user_key:
        _audit("terms-check", True, terms_accepted=True, auth_source="env_or_cache")
        print(json.dumps({
            "success": True,
            "terms_accepted": True,
            "message": "已具备有效 CXDA_USER_KEY（环境变量或缓存），隐式接受服务协议"
        }, ensure_ascii=False))
        return

    auth = get_cached_auth()
    accepted = auth.get(TERMS_ACCEPTED_KEY, False)

    _audit("terms-check", True, terms_accepted=accepted)
    print(json.dumps({
        "success": True,
        "terms_accepted": accepted,
        "message": "用户已接受服务协议" if accepted else "用户尚未接受服务协议"
    }, ensure_ascii=False))


# ── 命令：terms-accept ────────────────────────────────────────────────

def cmd_terms_accept():
    """用户接受服务协议"""
    auth = get_cached_auth()
    auth[TERMS_ACCEPTED_KEY] = True
    save_auth(auth)

    _audit("terms-accept", True)
    print(json.dumps({
        "success": True,
        "terms_accepted": True,
        "message": "已接受服务协议，可以继续使用"
    }, ensure_ascii=False))


# ── 命令：terms-decline ───────────────────────────────────────────────

def cmd_terms_decline(assume_yes: bool = False):
    """用户拒绝服务协议（敏感操作：会清除本地登录状态，必须显式确认）。"""
    if not assume_yes:
        raw_confirm = ""
        if not sys.stdin.isatty():
            try:
                raw_confirm = sys.stdin.read().strip()
            except Exception:
                pass
        confirmed = False
        if raw_confirm:
            try:
                obj = json.loads(raw_confirm)
                if isinstance(obj, dict) and bool(obj.get("confirm")):
                    confirmed = True
            except (json.JSONDecodeError, ValueError):
                if raw_confirm.strip().lower() in ("y", "yes", "true", "1"):
                    confirmed = True
        elif sys.stdin.isatty():
            try:
                ans = input("确认拒绝服务协议并清除本地认证信息? [y/N]: ").strip().lower()
                confirmed = ans in ("y", "yes")
            except EOFError:
                confirmed = False

        if not confirmed:
            _audit("terms-decline", False, reason="not_confirmed")
            print(json.dumps({
                "success": False,
                "status": "need_confirmation",
                "message": "此操作将清除本地认证信息，请通过 --yes 或 stdin {\"confirm\":true} 显式确认。",
            }, ensure_ascii=False))
            return

    auth = get_cached_auth()
    auth[TERMS_ACCEPTED_KEY] = False
    auth["CXDA_USER_KEY"] = ""
    auth["authtoken"] = ""
    auth["authtoken_expire"] = ""
    save_auth(auth)

    _audit("terms-decline", True, cleared_credentials=True)
    print(json.dumps({
        "success": True,
        "terms_accepted": False,
        "message": "已拒绝服务协议，无法继续使用相关功能"
    }, ensure_ascii=False))


# ── 命令：status ─────────────────────────────────────────────────────

def cmd_status():
    """查看当前认证状态（本地检查缓存 + 环境变量）"""
    user_key = get_user_key()
    auth = get_cached_auth()
    authed_at = auth.get("authed_at", "")
    terms_accepted = bool(user_key) or auth.get(TERMS_ACCEPTED_KEY, False)

    env_key = os.environ.get("CXDA_USER_KEY", "")
    auth_source = "env_var" if env_key else "cache"

    _audit("status", True,
           authenticated=bool(user_key),
           terms_accepted=bool(terms_accepted),
           auth_source=auth_source)

    if user_key:
        print(json.dumps({
            "success": True,
            "authenticated": True,
            "terms_accepted": terms_accepted,
            "authed_at": authed_at,
            "auth_source": auth_source,
            "CXDA_USER_KEY": mask_user_key(user_key),
            "message": "已认证（{}）".format("环境变量" if auth_source == "env_var" else "本地缓存")
        }, ensure_ascii=False))
    else:
        print(json.dumps({
            "success": True,
            "authenticated": False,
            "terms_accepted": terms_accepted,
            "message": "未认证，请配置环境变量 CXDA_USER_KEY"
        }, ensure_ascii=False))


# ── 入口 ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CXDA Skill 用户认证工具（火山部署版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令说明：

  status
    查看当前认证状态（本地检查，不调用远程接口）。
    返回 authenticated=true/false、terms_accepted=true/false、CXDA_USER_KEY（脱敏）等。

  terms-check
    检查用户是否已接受服务协议。
    返回 terms_accepted=true/false。首次使用时必须先引导用户接受协议。

  terms-accept
    标记用户已接受服务协议。
    接受后状态持久化存储，同一设备后续无需重复确认。

  terms-decline
    标记用户拒绝服务协议。同时清除本地 CXDA_USER_KEY、authtoken、authtoken_expire。
    拒绝后无法使用任何功能。

火山部署版认证方式：
  通过环境变量 CXDA_USER_KEY 自动认证，无需 SMS 登录。
  配置 CXDA_USER_KEY 后自动隐式接受服务协议。
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # terms-check
    subparsers.add_parser(
        "terms-check",
        help="检查用户是否已接受服务协议",
        description="检查用户是否已接受《财新数据隐私政策》《用户服务协议》《付费用户服务协议》。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
输出 JSON 格式：
  {"success": true, "terms_accepted": true/false, "message": "..."}

说明：
  - CXDA_USER_KEY 环境变量有效时，隐式已接受协议
  - terms_accepted=false → 需要引导用户接受协议
  - 协议接受状态持久化存储，同一设备后续无需重复确认
        """
    )

    # terms-accept
    subparsers.add_parser(
        "terms-accept",
        help="接受服务协议",
        description="标记用户已接受全部服务协议（隐私政策、用户服务协议、付费用户服务协议）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
输出 JSON 格式：
  {"success": true, "terms_accepted": true, "message": "已接受服务协议，可以继续使用"}

说明：
  - 状态持久化存储，后续无需重复确认
        """
    )

    # terms-decline
    p_decline = subparsers.add_parser(
        "terms-decline",
        help="拒绝服务协议",
        description="标记用户拒绝服务协议，同时清除本地认证信息。需要显式确认。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
输出 JSON 格式：
  确认后 → {"success": true, "terms_accepted": false, "message": "已拒绝服务协议，无法继续使用相关功能"}
  未确认 → {"success": false, "status": "need_confirmation", "message": "..."}

说明：
  - 敏感操作：会清除本地 CXDA_USER_KEY、authtoken、authtoken_expire
  - 必须通过下列任一方式显式确认：
      1) --yes / -y
      2) stdin JSON {"confirm": true}
      3) 交互终端输入 y/Y
  - 拒绝后无法使用任何功能
        """
    )
    p_decline.add_argument(
        "--yes", "-y",
        action="store_true",
        help="跳过确认，直接拒绝并清除本地认证信息",
    )

    # status
    subparsers.add_parser(
        "status",
        help="查看当前认证状态",
        description="本地检查认证状态（不调用远程接口），返回认证信息。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
输出 JSON 格式：
  已认证 → {"success": true, "authenticated": true, "terms_accepted": true, "CXDA_USER_KEY": "xxxx****xxxx", ...}
  未认证 → {"success": true, "authenticated": false, "terms_accepted": true/false, ...}

说明：
  - 纯本地检查，不发起网络请求
  - authenticated=true 表示已配置有效的 CXDA_USER_KEY
  - terms_accepted=true 表示用户已接受服务协议
        """
    )

    args = parser.parse_args()

    if args.command == "terms-check":
        cmd_terms_check()
    elif args.command == "terms-accept":
        cmd_terms_accept()
    elif args.command == "terms-decline":
        cmd_terms_decline(assume_yes=getattr(args, "yes", False))
    elif args.command == "status":
        cmd_status()


if __name__ == "__main__":
    main()
