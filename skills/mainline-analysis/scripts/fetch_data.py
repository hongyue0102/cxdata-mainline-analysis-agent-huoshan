#!/usr/bin/env python3
"""
A股主线识别 - 数据获取脚本
从财新数据 API 拉取分析所需的全部数据，保存为 JSON 文件。

使用方式：
    python fetch_data.py [日期]
    示例: python fetch_data.py 2026-04-20

输出目录：data/

鉴权说明：
    本脚本进程内直接调用 query.py 的取数函数（run_api_inline / get_page_size_inline），
    认证状态由 common.py 自动管理（进程内单例缓存 + requests.Session 连接复用）。
    若未认证，会返回错误，需先由 Agent 引导用户完成 auth.py 鉴权流程。
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from query import run_api_inline, get_page_size_inline

# ========== 业务接口（硬编码，只允许以下接口） ==========

_ALLOWED_APIS = frozenset([
    "getDIndDayQuoByCond-G",
    "getStkHotMarketByCond-G",
    "getInduDayQuoByCond-G",
    "getStkDayQuoByCond-G",
    "getStatTradeDateMainByCond-G",
    "getDStkValueMidByCond-G",
    "getDPubComInfo1ByCond-G",
    "getPubInduCodeByCond-G",
    "getDStkBlockTradeByCond-G",
])


def call_api(api_id: str, params: dict) -> dict:
    """进程内调用业务接口（仅允许 _ALLOWED_APIS 中的接口）。

    直接调用 query.run_api_inline，不 spawn 子进程。
    认证、token 缓存、gzip+base64 解码由 common.py/query.py 在进程内完成。
    返回的 dict 与原 HTTP 直连版本兼容：含 code/result/totalCount 等字段。
    """
    if api_id not in _ALLOWED_APIS:
        print(f"  [ERROR] 不允许的接口: {api_id}")
        return {"code": "error", "result": [], "totalCount": 0}

    data = run_api_inline(api_id, params)

    # 认证失败不重试
    if data.get("status") in ("failed", "terms_not_accepted"):
        msg = data.get("error", "未知错误")
        print(f"  [ERROR] {api_id}: {msg}")
        return {"code": "error", "result": [], "totalCount": 0,
                "status": data.get("status")}

    return data


def _get_max_page_size(api_id: str, params: dict = None, default: int = 1000) -> int:
    """进程内查询接口在当前业务条件下的最大返回条数。

    服务端的 maxPageSize 会随查询条件变化（传 tradeDate 时返回 500，不传时返回 20），
    必须传入业务参数获取最优分页大小，否则拿到固定的小值导致分页过多。
    """
    try:
        data = get_page_size_inline(api_id, params)
        mps = data.get("maxPageSize")
        if mps and int(mps) > 0:
            return int(mps)
    except Exception as e:
        print(f"  [WARN] 获取 {api_id} 的 maxPageSize 失败，用默认 {default}: {e}")
    return default


def fetch_all_pages(api_id: str, params: dict, show_progress: bool = False) -> list:
    """自动分页拉取全部数据。pageSize 动态取接口最大返回条数，避免写死导致分页错误。

    并发拉取：第一页先拿 totalCount 算出总页数，剩余页用 ThreadPoolExecutor(max_workers=15) 并发拉取。
    """
    page_size = _get_max_page_size(api_id, params)

    # 第一页：拿 totalCount 算总页数
    params_copy = {**params, "pageNum": "1", "pageSize": str(page_size)}
    data = call_api(api_id, params_copy)
    results = data.get("result", [])
    if not results:
        return []

    total = data.get("totalCount")
    if total is not None:
        total = int(total)
        total_pages = -(total // -page_size) if total > 0 else 1
        print(f"    totalCount={total}, pageSize={page_size}, 分{total_pages}页拉取（并发15）")
    else:
        return results  # 无 totalCount，只能拉一页

    if total_pages == 1:
        if total is not None and len(results) != total:
            print(f"  [WARN][一致性] {api_id}: 拉取 {len(results)} 条 ≠ totalCount {total} 条")
        return results

    # 剩余页并发拉取
    page_results = {1: results}

    def _fetch_page(p):
        pc = {**params, "pageNum": str(p), "pageSize": str(page_size)}
        d = call_api(api_id, pc)
        return p, d.get("result", [])

    with ThreadPoolExecutor(max_workers=15) as pool:
        futures = [pool.submit(_fetch_page, p) for p in range(2, total_pages + 1)]
        done_count = 1
        for f in as_completed(futures):
            p, r = f.result()
            page_results[p] = r
            done_count += 1
            if show_progress and done_count % 10 == 0:
                fetched = sum(len(page_results.get(k, [])) for k in range(1, done_count + 1))
                print(f"    ... 已拉取 {min(fetched, total)}/{total}")

    # 按页序合并
    all_results = []
    for p in sorted(page_results.keys()):
        all_results.extend(page_results[p])

    if show_progress:
        print(f"    ... 已拉取 {len(all_results)}/{total}")

    # 一致性自检
    if total is not None and len(all_results) != total:
        print(f"  [WARN][一致性] {api_id}: 拉取 {len(all_results)} 条 ≠ totalCount {total} 条，"
              f"可能被服务端限流/截断，下游分析可能不全")
    return all_results


# ========== 辅助函数 ==========

def safe_float(val, default=0.0):
    if val in (None, "", "NaN"):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    return int(safe_float(val, default))


def _get_board(code):
    if not code:
        return "main"
    prefix = code[:2]
    if prefix in ("83", "87", "88", "92"):
        return "bse"
    elif prefix == "30":
        return "gem"
    elif prefix == "68":
        return "star"
    else:
        return "main"


def is_b_share(code):
    """判断是否 B 股（主线分析针对上证A股，需排除B股）。

    B 股代码：上交所 B 股 900 开头（前2位 90），深交所 B 股 200 开头（前2位 20）。
    B 股也有涨跌停，若不排除会被计入全市场涨停/封板/主线统计，污染 A 股主线口径。
    """
    if not code:
        return False
    return code.startswith("90") or code.startswith("20")


def _get_limit_threshold(code, name):
    board = _get_board(code)
    is_st = "ST" in (name or "")
    if board == "bse":
        return 30
    elif board in ("gem", "star"):
        return 20
    else:
        return 5 if is_st else 10


def is_limit_up(r):
    return r.get("PRICE_UPDOWN_TYPE_PAR") == "涨停"


def is_limit_down(r):
    return r.get("PRICE_UPDOWN_TYPE_PAR") == "跌停"


def _limit_up_price(r):
    """计算涨停价 = ROUND(昨收 × (1 + 板块涨跌幅限制), 2)。
    四舍五入到分，与交易所「涨停价」口径一致。"""
    pre = safe_float(r.get("PRE_CLOSE_PRICE"))
    if pre <= 0:
        return None
    threshold = _get_limit_threshold(r.get("STK_CODE"), r.get("STK_SHORT_NAME"))
    return round(pre * (1 + threshold / 100.0), 2)


def is_sealed(r):
    """封板：收盘价封在涨停板上（= 接口标记的『涨停』）。

    PRICE_UPDOWN_TYPE_PAR=='涨停' 即收盘价 == 涨停价，与交易所口径一致，
    这部分都是封板成功的。"""
    return is_limit_up(r)


def is_broken(r):
    """炸板：盘中最高价触及涨停价，但收盘价未封住涨停。

    判定：HIGH_PRICE >= 涨停价 - 0.001 且 收盘价 < 涨停价 - 0.001。
    （阈值 0.001 容忍浮点误差。新股/次新股 PRE_CLOSE 缺失时不算炸板。）

    注意：收盘仍封在涨停板上的（is_sealed=True）不算炸板。"""
    if is_limit_up(r):
        return False
    limit_price = _limit_up_price(r)
    if not limit_price or limit_price <= 0:
        return False
    high = safe_float(r.get("HIGH_PRICE"))
    close = safe_float(r.get("CLOSE_PRICE"))
    if high <= 0 or close <= 0:
        return False
    return high >= limit_price - 0.001 and close < limit_price - 0.001


# ========== 主流程 ==========

def main():
    force = "--force" in sys.argv
    if force:
        sys.argv.remove("--force")

    if len(sys.argv) > 1:
        date = sys.argv[1]
        # 输入校验：日期必须为合法 YYYY-MM-DD 格式，拒绝非法/畸形输入进入后续
        # subprocess 参数与后端 API 请求（防御性加固，避免非法输入透传到下游）。
        try:
            date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            print(f"[ERROR] 非法日期参数: {date!r}（要求格式 YYYY-MM-DD，如 2026-04-20）")
            sys.exit(1)
    else:
        today = datetime.now()
        if today.weekday() == 5:
            today -= timedelta(days=1)
        elif today.weekday() == 6:
            today -= timedelta(days=2)
        date = today.strftime("%Y-%m-%d")

    # 数据防滥用限制（agent层面）：
    # 日期范围限制：只能拉取最近 30 个自然日内的数据，防止批量拉取全量历史数据
    _MAX_LOOKBACK_DAYS = 30
    _request_date = datetime.strptime(date, "%Y-%m-%d")
    _earliest = datetime.now() - timedelta(days=_MAX_LOOKBACK_DAYS)
    if _request_date < _earliest:
        print(f"[ERROR] 日期 {date} 超出允许范围（仅允许最近 {_MAX_LOOKBACK_DAYS} 天），"
              f"禁止拉取远期历史数据（数据防滥用限制）")
        sys.exit(1)
    if _request_date > datetime.now():
        print(f"[ERROR] 日期 {date} 为未来日期，禁止拉取（数据防滥用限制）")
        sys.exit(1)

    today_str = datetime.now().strftime("%Y-%m-%d")
    if date == today_str:
        now = datetime.now()
        cutoff_hour, cutoff_minute = 16, 10
        if now.hour < cutoff_hour or (now.hour == cutoff_hour and now.minute < cutoff_minute):
            msg = (
                f"[WARNING] 今日({date})数据尚未更新——财新数据接口每日 {cutoff_hour}:{cutoff_minute:02d} 后才更新当日完整数据。\n"
                f"当前时间 {now.strftime('%H:%M')}，拉取到的可能是盘中不完整快照，分析结果不可靠。\n"
                f"建议等到 {cutoff_hour}:{cutoff_minute:02d} 后再执行，或使用 --force 强制拉取（数据可能不完整）。"
            )
            if not force:
                print(msg)
                sys.exit(1)
            else:
                print(msg)
                print("[--force] 继续拉取盘中快照，请注意数据可能不完整。")

    t_start = time.time()

    print(f"=== A股主线识别数据获取 ===")
    print(f"目标日期: {date}")

    output_dir = Path(__file__).parent / "data"

    # 按交易日归档缓存：历史交易日数据不变，命中则跳过拉取
    date_cache_dir = output_dir / date
    _EXPECTED_FILES = {
        "index_quotes.json", "market_heat.json", "industry_quotes.json",
        "industry_l2_quotes.json", "stock_top_rise.json", "stock_top_drop.json",
        "limit_up_full.json", "limit_broken.json", "limit_down_full.json",
        "abnormal_trade.json", "stock_value.json", "stock_detail.json",
        "block_trade.json", "meta.json",
    }

    if date_cache_dir.exists():
        existing = {f.name for f in date_cache_dir.iterdir() if f.is_file()}
        if _EXPECTED_FILES.issubset(existing):
            print(f"[CACHE] 日期 {date} 数据已存在且完整，跳过拉取")
            print(f"[DONE] 耗时: 0.0s (缓存命中)")
            return

    date_cache_dir.mkdir(parents=True, exist_ok=True)

    def save(filename: str, data):
        with open(date_cache_dir / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  [OK] {filename} ({len(data)} 条)")

    # ========================================
    # 0/8 三大指数日线行情
    # ========================================
    print("[0/8] 三大指数行情...")
    INDEX_NAMES = ["上证指数", "深证成指", "创业板指"]
    index_quotes = []
    for idx_name in INDEX_NAMES:
        data = call_api("getDIndDayQuoByCond-G",
                        {"indShortName": idx_name, "tradeDate": date, "pageNum": "1", "pageSize": "1"})
        results = data.get("result", [])
        if results:
            index_quotes.append(results[0])
    save("index_quotes.json", index_quotes)

    # ========================================
    # 1/8 市场情绪温度
    # ========================================
    print("\n[1/8] 市场情绪温度...")
    heat = fetch_all_pages("getStkHotMarketByCond-G", {"endDate": date})
    save("market_heat.json", heat)

    # ========================================
    # 2/8 申万一级行业涨跌幅（按行业级别批量拉取）
    # ========================================
    print("[2/8] 申万一级行业涨跌幅（induLevel=1 批量拉取）...")

    def fetch_industry_by_level(level: str, date_str: str) -> list:
        # 必传 endDate：getInduDayQuoByCond-G 不传日期会返回最近多个交易日的快照，
        # 同一行业会出现多条不同 END_DATE 的记录，排序后旧日期记录可能被误当作当日数据使用。
        # 见 2026-08-31 非金属材料Ⅱ 事件（8/27 旧记录 day=10.92 排在 8/31 真值 day=0.62 前面）。
        page_size = _get_max_page_size("getInduDayQuoByCond-G", {"induLevel": level, "endDate": date_str})
        all_results = []
        page = 1
        while True:
            data = call_api("getInduDayQuoByCond-G",
                            {"induLevel": level, "endDate": date_str,
                             "pageNum": str(page), "pageSize": str(page_size)})
            results = data.get("result", [])
            if not results:
                break
            all_results.extend(results)
            tc = data.get("totalCount")
            if tc and len(all_results) >= int(tc):
                break
            page += 1
            time.sleep(0.1)
        # 兜底防御：即便服务端仍返回多日数据，也只保留目标交易日
        return [r for r in all_results
                if r.get("REST_TYPE_PAR") == "后复权"
                and r.get("WEIGH_TYPE_PAR") == "流通市值加权"
                and r.get("END_DATE") == date_str]

    industry_quotes = fetch_industry_by_level("1", date)
    if not industry_quotes:
        print("  [ERROR] 一级行业数据为空，API 调用可能失败，后续分析结果不可靠")
    industry_quotes.sort(key=lambda x: float(x.get("INDU_LIMIT_DAY", 0) or 0), reverse=True)
    save("industry_quotes.json", industry_quotes)
    print(f"  [OK] industry_quotes.json ({len(industry_quotes)} 条)")

    # ========================================
    # 2b/8 申万二级行业涨跌幅（按行业级别批量拉取）
    # ========================================
    print("[2b/8] 申万二级行业涨跌幅（induLevel=2 批量拉取）...")

    industry_l2_quotes = fetch_industry_by_level("2", date)
    if not industry_l2_quotes:
        print("  [ERROR] 二级行业数据为空，API 调用可能失败，后续分析结果不可靠")
    industry_l2_quotes.sort(key=lambda x: float(x.get("INDU_LIMIT_DAY", 0) or 0), reverse=True)
    save("industry_l2_quotes.json", industry_l2_quotes)
    print(f"  [OK] industry_l2_quotes.json ({len(industry_l2_quotes)} 条)")

    # ========================================
    # 3/8 全市场个股日线行情（分页拉取全部）
    # ========================================
    print("[3/8] 全市场个股日线行情...")
    all_quotes = fetch_all_pages("getStkDayQuoByCond-G", {"tradeDate": date}, show_progress=True)
    if not all_quotes:
        print("  [ERROR] 个股行情数据为空，API 调用可能失败，后续分析结果不可靠")
    # 过滤：需有涨幅数据 + 排除 B 股（主线分析针对上证A股口径，B 股单独计价、波动逻辑不同）
    valid_quotes = [r for r in all_quotes
                    if r.get("PRICE_LIMIT") not in (None, "", "NaN")
                    and not is_b_share(r.get("STK_CODE", ""))]
    valid_quotes.sort(key=lambda x: float(x.get("PRICE_LIMIT", 0)), reverse=True)

    save("stock_top_rise.json", valid_quotes[:100])
    save("stock_top_drop.json", valid_quotes[-50:] if len(valid_quotes) > 100 else [])

    all_limit_up = [r for r in valid_quotes if is_limit_up(r)]
    all_limit_down = [r for r in valid_quotes if is_limit_down(r)]
    # 炸板股：盘中触及涨停但收盘未封住（仅在全市场行情里反推，无额外接口调用）
    all_broken = [r for r in valid_quotes if is_broken(r)]
    # 全市场涨停股全集（封板成功的全部，用于主线/锚点/情绪分析）
    # 旧版只存涨幅榜前100，会丢失非涨幅靠前的涨停股，导致 103 vs 61 不一致
    save("limit_up_full.json", all_limit_up)
    save("limit_broken.json", all_broken)
    # 跌停股全集：与涨停股对称存盘（当前分析仅用计数，但保留明细避免将来踩同款 bug）
    save("limit_down_full.json", all_limit_down)
    print(f"  总成交: {len(valid_quotes)}家")
    print(f"  涨停(封板): {len(all_limit_up)}家")
    print(f"  炸板(触板未封): {len(all_broken)}家")
    print(f"  跌停: {len(all_limit_down)}家")

    # ========================================
    # 4/8 异动披露
    # ========================================
    print("[4/8] 异动披露...")
    abnormal = fetch_all_pages("getStatTradeDateMainByCond-G", {"endDate": date})
    save("abnormal_trade.json", abnormal)

    # ========================================
    # 5/8 涨停股市值（并发查询）
    # ========================================
    print("[5/8] 涨停股市值...")

    def query_stock_value(r):
        val = call_api("getDStkValueMidByCond-G",
                       {"stkCode": r["STK_CODE"], "endDate": date, "pageNum": "1", "pageSize": "1"})
        return val.get("result", [])

    stock_value = []
    with ThreadPoolExecutor(max_workers=15) as pool:
        futures = [pool.submit(query_stock_value, r) for r in all_limit_up]
        for f in as_completed(futures):
            stock_value.extend(f.result())
    save("stock_value.json", stock_value)

    # ========================================
    # 6/8 涨停股行业分类（申万二级）
    # ========================================
    print("[6/8] 涨停股行业分类...")

    # 行业名→(二级名, 二级代码) 记忆化，避免对同一行业名重复查 getPubInduCodeByCond-G
    _indu_code_cache = {}

    def query_stock_detail(r):
        code = r.get("STK_CODE", "")
        name = r.get("STK_SHORT_NAME", "")
        ind_data = call_api("getDPubComInfo1ByCond-G",
                            {"stkCode": code, "pageNum": "1", "pageSize": "1"})
        ind_res = ind_data.get("result", [{}])
        info = ind_res[0] if ind_res else {}

        # 申万二级行业（权威口径）：
        # INDU_CLASS_NAME_S 是申万三级名（与 getPubComInduChanSwByCond-G 一致），
        # 用它做入参查行业代码表。该接口对同一个行业名会返回多条记录（GICS/中证/申万各一条），
        # 必须筛选 INDU_SYS_PAR 含「申银万国」的那条，否则取到的 INDU_NAME2 是 GICS 口径
        # （如「半导体产品与设备」），与板块行情的申万二级（「半导体」）对不上。
        # 旧版直接用 INDU_CLASS_NAME_Q（GICS）+ 字符串包含匹配，导致 14.6% 漏归。此为根治。
        sw_l2_name = ""
        sw_l2_code = ""
        sw_l3 = info.get("INDU_CLASS_NAME_S", "")
        if sw_l3:
            if sw_l3 in _indu_code_cache:
                sw_l2_name, sw_l2_code = _indu_code_cache[sw_l3]
            else:
                code_data = call_api("getPubInduCodeByCond-G",
                                     {"induClassName": sw_l3, "pageNum": "1", "pageSize": "20"})
                code_res = code_data.get("result", [])
                # 优先取申万 2021，其次任意申万版本，最后回退有效记录
                sw_2021 = [c for c in code_res
                           if "申银万国" in (c.get("INDU_SYS_PAR") or "") and "2021" in (c.get("INDU_SYS_PAR") or "")]
                sw_any = [c for c in code_res if "申银万国" in (c.get("INDU_SYS_PAR") or "")]
                chosen = (sw_2021 or sw_any or [c for c in code_res if c.get("IS_VALID") == "是"] or code_res)
                if chosen:
                    sw_l2_name = chosen[0].get("INDU_NAME2", "")
                    sw_l2_code = chosen[0].get("INDU_CODE2", "")
                _indu_code_cache[sw_l3] = (sw_l2_name, sw_l2_code)

        return {
            "code": code,
            "name": name,
            "sw_industry_l2": sw_l2_name,        # 申万二级名（权威，用于主线/锚点归并）
            "sw_industry_l2_code": sw_l2_code,   # 申万二级代码
            "sw_industry_s": info.get("INDU_CLASS_NAME_S", ""),   # 申万三级名
            "sw_industry_q": info.get("INDU_CLASS_NAME_Q", ""),   # GICS口径，仅参考
            "sw_industry_z": info.get("INDU_CLASS_NAME_Z", ""),
        }

    stock_detail = []
    with ThreadPoolExecutor(max_workers=15) as pool:
        futures = [pool.submit(query_stock_detail, r) for r in all_limit_up]
        for f in as_completed(futures):
            stock_detail.append(f.result())
    no_industry = sum(1 for d in stock_detail if not d.get("sw_industry_s") and not d.get("sw_industry_q"))
    if no_industry > 0 and len(all_limit_up) > 0:
        print(f"  [WARN] {no_industry}/{len(all_limit_up)} 只涨停股行业分类为空，行业分类 skill 可能配置异常")
    save("stock_detail.json", stock_detail)

    # ========================================
    # 7/8 大宗交易
    # ========================================
    print("[7/8] 大宗交易...")
    block = fetch_all_pages("getDStkBlockTradeByCond-G", {"tradeDate": date})
    save("block_trade.json", block)

    # 元数据
    meta = {
        "date": date,
        "total_stocks": len(valid_quotes),
        "limit_up_count": len(all_limit_up),      # 涨停=封板（收盘封住）
        "limit_down_count": len(all_limit_down),
        "sealed_count": len(all_limit_up),        # 封板数（= 涨停数）
        "broken_count": len(all_broken),          # 炸板数（触板未封）
    }
    save("meta.json", [meta])

    elapsed = time.time() - t_start
    print(f"\n=== 完成！日期: {date}, 总成交: {len(valid_quotes)}, 涨停: {len(all_limit_up)}, 炸板: {len(all_broken)}, 跌停: {len(all_limit_down)} ===")
    print(f"总耗时: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
