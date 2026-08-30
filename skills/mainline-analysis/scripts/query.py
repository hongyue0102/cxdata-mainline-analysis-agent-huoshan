# -*- coding: utf-8 -*-
"""
CXDA Skill - 统一查询脚本（火山部署版）

提供数据查询和系统查询功能：
  - api:       调用业务数据接口
  - page-size: 查询接口分页大小限制
  - package:   查询用户套餐额度

用法：
  python query.py api <API_ID> key=value [key=value ...]
  python query.py page-size <API_ID>
  python query.py package [--api-main <API_ID>]
"""

import argparse
import hashlib
import json
import re
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (
    BASE_URL,
    ensure_token,
    http_get,
    http_post_form,
    get_user_key,
    check_terms_accepted,
    output_json,
    output_error,
)


# ── 常量 ──────────────────────────────────────────────────────────────

SUCCESS_CODE = "10000"

_TIME_FMT = "%Y-%m-%d %H:%M:%S"
_DISPLAY_TZ = timezone(timedelta(hours=8))
_PAGE_SIZE_CACHE = None
_PAGE_SIZE_LOCK = threading.RLock()

_FORBIDDEN_PARAM_KEYS = {"authtoken", "userkey", "requestchannel"}

_API_ID_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')


def _validate_api_id(api_id):
    if not isinstance(api_id, str) or not _API_ID_RE.match(api_id):
        raise ValueError("非法 API ID（仅允许字母数字下划线连字符）: {!r}".format(api_id))
    return api_id


def _format_timestamp(value, default="-"):
    if value is None or isinstance(value, bool):
        return default
    try:
        text = str(value).strip()
        if text == "":
            return default
        timestamp = float(text)
        if timestamp > 9999999999:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, _DISPLAY_TZ).strftime(_TIME_FMT)
    except (ValueError, TypeError, OSError, OverflowError):
        return default


def _format_package_item(item):
    return {
        "relation_id": item.get("id", ""),
        "user_id": item.get("wsUserId", ""),
        "package_id": item.get("wsPackageId", ""),
        "package_name": item.get("packageName", "-"),
        "package_code": item.get("packageCode", ""),
        "status": item.get("status", ""),
        "valid_start": _format_timestamp(item.get("validStartTime")),
        "valid_end": _format_timestamp(item.get("validEndTime")),
        "total_money": item.get("totalMoney", ""),
        "balance": item.get("balance", ""),
        "day_balance": item.get("dayBalance", ""),
        "day_money": item.get("dayMoney", ""),
    }


def _query_package_result(user_key, api_main=""):
    if not user_key:
        return {
            "code": "10500",
            "msg": "未找到 CXDA_USER_KEY，请先通过 auth.py 完成认证",
            "package_count": 0,
            "packages": [],
        }

    params = {"userKey": user_key}
    if api_main:
        params["apiMain"] = api_main

    resp_data = http_post_form(
        f"{BASE_URL}/mall/api_getAuthList.htm",
        data=params
    )
    if str(resp_data.get("code")) != SUCCESS_CODE:
        return {
            "code": str(resp_data.get("code", "10500")),
            "msg": resp_data.get("msg", "查询失败"),
            "package_count": 0,
            "packages": [],
        }

    raw_list = resp_data.get("data", [])
    if not isinstance(raw_list, list):
        raw_list = []

    formatted = []
    for item in raw_list:
        if isinstance(item, dict):
            formatted.append(_format_package_item(item))
    return {
        "code": SUCCESS_CODE,
        "msg": resp_data.get("msg", "返回权限清单成功"),
        "package_count": len(formatted),
        "packages": formatted,
    }


def parse_params(args):
    params = {}
    for arg in args:
        if '=' in arg:
            k, v = arg.split('=', 1)
            k = k.strip()
            if k.lower() in _FORBIDDEN_PARAM_KEYS:
                raise ValueError("禁止覆盖保留参数（脚本自动管理）: {}".format(k))
            params[k] = v.strip()
    return params


def _normalize_max_page_size(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        text = str(value).strip()
        if text == "":
            return None
        number = int(float(text))
        return number if number > 0 else None
    except (ValueError, TypeError):
        return None


def _load_page_size_cache():
    global _PAGE_SIZE_CACHE
    if not isinstance(_PAGE_SIZE_CACHE, dict):
        _PAGE_SIZE_CACHE = {}
    return _PAGE_SIZE_CACHE


def _page_size_cache_key(api_id, params):
    """按接口和业务输入参数生成分页上限缓存键。

    服务端的 maxPageSize 会随查询条件变化（如传 tradeDate 时返回 500，
    不传时返回 20），必须按参数组合缓存，避免不同查询互相污染。
    """
    normalized_params = {
        str(key): value
        for key, value in dict(params or {}).items()
        if str(key).lower() not in ("pagenum", "pagesize")
    }
    payload = json.dumps(
        normalized_params,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return "{}:{}".format(api_id, digest)


def _fetch_api_limit_setting(api_id, params=None):
    """携带业务输入参数查询当前条件下的最优分页大小。

    分页控制字段（pageSize/pageNum）不是业务条件，也不应被转发给分页配置接口。
    尤其是 pageSize，必须避免调用方传入的值影响 maxPageSize 的计算。
    """
    user_key = get_user_key()
    if not user_key:
        raise RuntimeError("未找到 CXDA_USER_KEY，请先通过 auth.py 完成认证")

    request_data = {
        key: value
        for key, value in dict(params or {}).items()
        if str(key).lower() not in ("pagesize", "pagenum")
    }
    request_data["userKey"] = user_key
    request_data["apiMain"] = api_id
    return http_post_form(
        f"{BASE_URL}/mall/api_getApiLimitSetting.htm",
        data=request_data,
    )


def _get_api_max_page_size(api_id, params):
    """获取当前业务输入对应的最优分页大小，并按参数组合缓存。

    同一进程内的并发首屏请求共享一个获取动作（_PAGE_SIZE_LOCK），避免多个
    线程同时发现缓存为空而重复调用 api_getApiLimitSetting。
    """
    cache_key = _page_size_cache_key(api_id, params)
    with _PAGE_SIZE_LOCK:
        cache = _load_page_size_cache()
        if cache_key in cache:
            return cache[cache_key]

        data = _fetch_api_limit_setting(api_id, params)
        max_page_size = _normalize_max_page_size(
            data.get("maxPageSize") if isinstance(data, dict) else None
        )
        if max_page_size is None:
            msg = data.get("msg") if isinstance(data, dict) else ""
            raise RuntimeError(
                "查询接口最大分页失败：{}".format(msg or "未返回有效 maxPageSize")
            )

        cache[cache_key] = max_page_size
        return max_page_size


def _cache_api_max_page_size(api_id, params, data):
    max_page_size = _normalize_max_page_size(data.get("maxPageSize") if isinstance(data, dict) else None)
    if max_page_size is None:
        return
    cache_key = _page_size_cache_key(api_id, params)
    cache = _load_page_size_cache()
    cache[cache_key] = max_page_size


def _apply_default_page_size(api_id, params):
    """忽略调用方 pageSize，统一使用接口返回的 maxPageSize（按当前业务条件动态获取）。"""
    normalized_params = dict(params or {})
    page_size = normalized_params.get("pageSize")
    if page_size is not None and str(page_size).strip() != "":
        return normalized_params
    normalized_params["pageSize"] = str(_get_api_max_page_size(api_id, params))
    return normalized_params


# ── 进程内调用的取数函数（供 fetch_data.py import，消除 subprocess 开销） ──

def run_api_inline(api_id, params) -> dict:
    """进程内调用业务接口（不 spawn 子进程，不 output_json，直接返回 dict）。

    供 fetch_data.py 等脚本 import 使用，消除三层 subprocess 的固定开销。
    失败时返回 {"status": "failed", "error": msg}，不 sys.exit。
    """
    try:
        _validate_api_id(api_id)
    except ValueError as e:
        return {"status": "failed", "error": str(e)}

    accepted, error_response = check_terms_accepted()
    if not accepted:
        return {"status": "terms_not_accepted", "error": error_response.get("error", "条款未接受")}

    try:
        params = _apply_default_page_size(api_id, params)
        token = ensure_token()

        request_params = {"authtoken": token}
        request_params.update(params)

        data = http_get(
            f"{BASE_URL}/webservice/cxdata/{api_id}.htm",
            params=request_params
        )
        return data
    except SystemExit:
        return {"status": "failed", "error": "认证失败"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def get_page_size_inline(api_id, params=None) -> dict:
    """进程内查询接口分页大小（不 spawn 子进程，不 output_json，直接返回 dict）。

    供 fetch_data.py 等脚本 import 使用。传入 params 可获取当前业务条件下的
    最优分页大小（服务端会根据查询参数返回不同的 maxPageSize）。
    """
    try:
        _validate_api_id(api_id)
    except ValueError as e:
        return {"status": "failed", "error": str(e)}

    accepted, error_response = check_terms_accepted()
    if not accepted:
        return {"status": "terms_not_accepted", "error": error_response.get("error", "条款未接受")}

    user_key = get_user_key()
    if not user_key:
        return {"status": "failed", "error": "未找到 CXDA_USER_KEY"}

    try:
        data = _fetch_api_limit_setting(api_id, params)
        _cache_api_max_page_size(api_id, params, data)
        return data
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ── 子命令：api ──────────────────────────────────────────────────────

def cmd_api(api_id, params):
    _validate_api_id(api_id)
    accepted, error_response = check_terms_accepted()
    if not accepted:
        output_json(error_response)
        return

    try:
        params = _apply_default_page_size(api_id, params)
        token = ensure_token()

        request_params = {"authtoken": token}
        request_params.update(params)

        data = http_get(
            f"{BASE_URL}/webservice/cxdata/{api_id}.htm",
            params=request_params
        )
        output_json(data)
    except Exception as e:
        output_error(str(e))


# ── 子命令：page-size ────────────────────────────────────────────────

def cmd_page_size(api_id):
    _validate_api_id(api_id)
    accepted, error_response = check_terms_accepted()
    if not accepted:
        output_json(error_response)
        return

    user_key = get_user_key()
    if not user_key:
        output_error("未找到 CXDA_USER_KEY，请先通过 auth.py 完成认证")
        return

    try:
        data = _fetch_api_limit_setting(api_id)
        _cache_api_max_page_size(api_id, data)
        output_json(data)
    except Exception as e:
        output_error(str(e))


# ── 子命令：package ──────────────────────────────────────────────────

def cmd_package(api_main=""):
    if api_main:
        try:
            _validate_api_id(api_main)
        except ValueError as e:
            output_json({"code": "10400", "msg": str(e),
                         "package_count": 0, "packages": []})
            return

    accepted, error_response = check_terms_accepted()
    if not accepted:
        output_json(error_response)
        return

    user_key = get_user_key()

    if not user_key:
        output_json({
            "code": "10500",
            "msg": "未找到 CXDA_USER_KEY，请先通过 auth.py 完成认证",
            "package_count": 0,
            "packages": [],
        })
        return

    try:
        output_json(_query_package_result(user_key, api_main))
    except Exception as e:
        output_json({"code": "10500", "msg": str(e), "package_count": 0, "packages": []})


# ── 入口 ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CXDA Skill - 统一查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令说明：

  api <API_ID> [key=value ...]
    调用业务数据接口，查询具体数据。
    authtoken 由脚本自动管理（缓存300秒，过期自动刷新），无需手动传入。
    返回数据经 gzip+base64 编码，脚本自动解码。

  page-size <API_ID>
    查询指定接口的分页大小限制。

  package [--api-main <API_ID>]
    查询用户套餐额度信息。
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_api = subparsers.add_parser(
        "api",
        help="调用业务数据接口",
        description="调用业务数据接口查询具体数据。需要先完成认证（authenticated=true）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python query.py api getStkBasicInfoByCond-K stkCode=600519
  python query.py api getCooWineCateDailQuoByWineName wineName=飞天茅台
        """
    )
    p_api.add_argument("api_id", help="接口访问标识（API ID）")
    p_api.add_argument("params", nargs="*", help="查询参数，格式 key=value（可多个）")

    p_ps = subparsers.add_parser(
        "page-size",
        help="查询接口分页大小限制",
        description="查询指定接口的分页大小限制。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python query.py page-size getStkBasicInfoByCond-K
        """
    )
    p_ps.add_argument("api_id", help="接口访问标识（API ID）")

    p_pkg = subparsers.add_parser(
        "package",
        help="查询用户套餐额度",
        description="查询用户套餐额度信息。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python query.py package
  python query.py package --api-main getStkBasicInfoByCond-K
        """
    )
    p_pkg.add_argument("--api-main", default="", help="接口访问标识（可选）")

    args = parser.parse_args()

    if args.command == "api":
        params = parse_params(args.params)
        cmd_api(args.api_id, params)
    elif args.command == "page-size":
        cmd_page_size(args.api_id)
    elif args.command == "package":
        cmd_package(args.api_main)


if __name__ == "__main__":
    main()
