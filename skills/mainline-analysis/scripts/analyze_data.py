#!/usr/bin/env python3
"""
A股主线识别 - 数据分析脚本
读取 fetch_data.py 拉取的 JSON 数据，按主线识别框架进行结构化分析，
输出 analysis.json 供 Agent LLM 生成六段式报告使用。

使用方式：
    python analyze_data.py [日期]
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load(name: str) -> list:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def safe_float(val, default=0.0):
    if val in (None, "", "NaN"):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    """安全转整数（缓解火山风险4：审计日志缺失/类型校验缺失）。
    JSON 被篡改为字符串时 TypeError 崩溃，统一兜底为 default。
    """
    return int(safe_float(val, default))


def _get_board(code):
    """根据股票代码返回板块: bse(北交所) / gem(创业板) / star(科创板) / main(主板)"""
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


def _get_limit_threshold(code, name):
    """根据板块和ST标识返回涨跌停板阈值(%)"""
    board = _get_board(code)
    is_st = "ST" in (name or "")
    if board == "bse":
        return 30
    elif board in ("gem", "star"):
        return 20
    else:
        return 5 if is_st else 10


def is_limit_up(r):
    """判断是否涨停（直接用接口字段，与交易所口径一致）"""
    return r.get("PRICE_UPDOWN_TYPE_PAR") == "涨停"


def analyze_market_environment(heat, industry_quotes, meta):
    """第一步：判断市场整体环境"""
    h = heat[0] if heat else {}
    up_ratio = safe_float(h.get("UP_NUM_PER"))
    pe_mid = safe_float(h.get("PE_MID"))
    pe_index = h.get("PE_INDEX", "未知")
    up_down_index = h.get("UP_DOWN_INDEX", "未知")
    hot_comment = h.get("HOT_INDEX_COS", "")
    hot_index = safe_float(h.get("HOT_INDEX"))

    total_stocks = safe_int(meta.get("total_stocks", 0))
    limit_up = safe_int(meta.get("limit_up_count", 0))
    limit_down = safe_int(meta.get("limit_down_count", 0))

    # 行业涨跌分布
    rising_industries = [i for i in industry_quotes if safe_float(i.get("INDU_LIMIT_DAY")) > 0]
    falling_industries = [i for i in industry_quotes if safe_float(i.get("INDU_LIMIT_DAY")) < 0]

    # 判断市场状态
    if up_ratio >= 65 and limit_up >= 80:
        status = "强势"
        action = "主动进攻"
    elif up_ratio >= 55 and limit_up >= 40:
        status = "震荡偏强" if hot_index > 50 else "震荡"
        action = "精选参与"
    elif up_ratio >= 40:
        status = "震荡偏弱"
        action = "控制仓位"
    else:
        status = "弱势"
        action = "观望"

    return {
        "status": status,
        "action": action,
        "up_ratio": up_ratio,
        "pe_mid": pe_mid,
        "pe_index": pe_index,
        "up_down_index": up_down_index,
        "hot_comment": hot_comment,
        "hot_index": hot_index,
        "total_stocks": total_stocks,
        "limit_up": limit_up,
        "limit_down": limit_down,
        "rising_industries": len(rising_industries),
        "falling_industries": len(falling_industries),
    }



def analyze_main_lines(industry_l2_quotes, limit_up_full, abnormal_trade, stock_detail=None):
    """第二步：识别主线与次级热点（基于二级行业涨幅 + 涨停集中度）"""
    bottom_industries = industry_l2_quotes[-3:] if len(industry_l2_quotes) >= 3 else []

    # 涨停股按板块归类
    limit_up_stocks = [s for s in limit_up_full if is_limit_up(s)]

    # 从异动数据提取活跃方向
    active_directions = {}
    for r in abnormal_trade:
        name = r.get("STK_SHORT_NAME", "")
        rise = safe_float(r.get("RISE_DROP_RANGE"))
        if rise >= 5:
            active_directions[name] = {
                "code": r.get("STK_CODE", ""),
                "rise": rise,
                "abnorm_type": r.get("ABNORM_TYPE_PAR", ""),
                "amount": safe_float(r.get("TRADE_AMUT")),
            }

    # --- 涨停股集中度分析：统计每个二级行业的涨停股数量 ---
    detail_map = {}
    if stock_detail:
        detail_map = {r.get("code", ""): r for r in stock_detail}

    # L2 标准行业名清单（用于漏归自检）
    l2_standard_names = [ind.get("INDU_CLASS_NAME", "") for ind in industry_l2_quotes
                         if ind.get("INDU_CLASS_NAME")]
    l2_standard_set = set(l2_standard_names)

    # 申万二级归并：直接用 fetch 阶段取好的 sw_industry_l2（申万2021口径）精确匹配，
    # 不再用 _match_l2_from_industry_name 字符串包含匹配（旧版用 GICS 名瞎猜，14.6% 漏归）。
    l2_limit_count = {}
    unmatched_codes = []
    for s in limit_up_stocks:
        code = s.get("STK_CODE", "")
        info = detail_map.get(code, {})
        sw_l2 = info.get("sw_industry_l2", "")
        if sw_l2 and sw_l2 in l2_standard_set:
            l2_limit_count[sw_l2] = l2_limit_count.get(sw_l2, 0) + 1
        else:
            unmatched_codes.append((code, s.get("STK_SHORT_NAME", ""), sw_l2))
    # 漏归自检：申万二级缺失或不在板块列表的，告警（防止静默漏算涨停集中度）
    if unmatched_codes:
        print(f"  [WARN][行业归并] {len(unmatched_codes)}/{len(limit_up_stocks)} 只涨停股未归入任何"
              f"申万二级（行业分类缺失或未命中板块列表），主线涨停数可能偏少：")
        for code, name, sw in unmatched_codes[:10]:
            print(f"    {code} {name}: sw_industry_l2={sw!r}")

    max_limit = max(l2_limit_count.values()) if l2_limit_count else 0

    # --- 对全部二级行业计算综合得分（四维评分） ---
    # 维度：日涨幅排名(30%) + 涨停集中度(30%) + 周涨幅趋势(20%) + 月涨幅趋势(20%)
    all_day_changes = [safe_float(ind.get("INDU_LIMIT_DAY")) for ind in industry_l2_quotes]
    all_week_changes = [safe_float(ind.get("INDU_LIMIT_1W")) for ind in industry_l2_quotes]
    all_month_changes = [safe_float(ind.get("INDU_LIMIT_1M")) for ind in industry_l2_quotes]
    max_week = max(all_week_changes) if all_week_changes else 1
    max_month = max(all_month_changes) if all_month_changes else 1

    industry_scored = []
    for idx, ind in enumerate(industry_l2_quotes):
        name = ind.get("INDU_CLASS_NAME", "")
        limit_count = l2_limit_count.get(name, 0)
        limit_score = round(limit_count / max_limit * 100, 1) if max_limit > 0 else 0
        day_rank_score = max(0, 100 - idx * 0.8)
        day_change = safe_float(ind.get("INDU_LIMIT_DAY"))
        week_change = safe_float(ind.get("INDU_LIMIT_1W"))
        month_change = safe_float(ind.get("INDU_LIMIT_1M"))
        week_score = round(max(0, week_change) / max_week * 100, 1) if max_week > 0 else 0
        month_score = round(max(0, month_change) / max_month * 100, 1) if max_month > 0 else 0
        composite = round(day_rank_score * 0.4 + limit_score * 0.2 + week_score * 0.2 + month_score * 0.2, 1)

        if limit_count >= 3:
            line_type = "资金攻击型"
        elif limit_count >= 1:
            line_type = "资金攻击型" if limit_score >= 30 else "趋势/防御型"
        else:
            line_type = "趋势/防御型"

        industry_scored.append({
            "name": name,
            "day_change": day_change,
            "week_change": week_change,
            "month_change": month_change,
            "compo_num": int(safe_float(ind.get("INDU_COMPO_NUM"))),
            "limit_up_count": limit_count,
            "limit_up_score": limit_score,
            "week_score": week_score,
            "month_score": month_score,
            "composite_score": composite,
            "line_type": line_type,
        })

    industry_scored.sort(key=lambda x: x["composite_score"], reverse=True)

    return {
        "main_lines": industry_scored[:2],
        "secondary_hot": industry_scored[2:5],
        "bottom_industries": [{"name": i.get("INDU_CLASS_NAME"), "day_change": safe_float(i.get("INDU_LIMIT_DAY"))} for i in bottom_industries],
        "limit_up_stocks": limit_up_stocks,
        "active_directions": active_directions,
        "l2_limit_count": l2_limit_count,
    }


def analyze_anchor_stocks(limit_up_full, stock_value, limit_up_count,
                          main_line_names=None, stock_detail=None, l2_standard_names=None):
    """第三步：识别龙头、中军、补涨 — 只从核心主线和第二主线的涨停股中选"""
    limit_ups = [s for s in limit_up_full
                 if is_limit_up(s) and safe_float(s.get("PRICE_LIMIT")) < 100
                 and "ST" not in (s.get("STK_SHORT_NAME") or "")]

    # 如果有主线行业名，只保留属于主线行业的涨停股（用申万二级精确匹配）
    if main_line_names and stock_detail:
        detail_map = {r.get("code", ""): r for r in stock_detail}
        main_line_set = set(main_line_names)
        filtered = []
        for s in limit_ups:
            code = s.get("STK_CODE", "")
            info = detail_map.get(code, {})
            sw_l2 = info.get("sw_industry_l2", "")
            if sw_l2 and sw_l2 in main_line_set:
                filtered.append(s)
        # 主线涨停股不足5只时回退到全市场
        limit_ups = filtered if len(filtered) >= 5 else limit_ups

    # 市值数据转dict
    value_map = {}
    for v in stock_value:
        code = v.get("STK_CODE", "")
        value_map[code] = {
            "total_value": safe_float(v.get("TOT_VALUE_S")),
            "float_value": safe_float(v.get("FLOAT_VALUE_S")),
        }

    # 构建所有涨停股信息
    all_info = []
    detail_map = {r.get("code", ""): r for r in (stock_detail or [])}
    for s in limit_ups:
        code = s.get("STK_CODE", "")
        rise = safe_float(s.get("PRICE_LIMIT"))
        amount = safe_float(s.get("TRADE_AMUT"))
        val = value_map.get(code, {})
        total_val = val.get("total_value", 0)

        # 解析个股的申万二级行业归属（fetch 阶段已取好，精确匹配板块列表）
        info = detail_map.get(code, {})
        industry = info.get("sw_industry_l2", "") or "未知"

        if total_val > 500e8:
            role = "趋势中军"
        elif _get_board(code) in ("gem", "star", "bse"):
            role = "情绪标的（20cm）"
        else:
            role = "情绪标的" if amount > 10e8 else "补涨标的"

        all_info.append({
            "code": code,
            "name": s.get("STK_SHORT_NAME", ""),
            "rise": rise,
            "amount": amount,
            "total_value": total_val,
            "role": role,
            "industry": industry,
        })

    all_info.sort(key=lambda x: x["amount"], reverse=True)

    # 按角色各取代表性个股，总共 5-8 只
    leaders = [s for s in all_info if s["role"] in ("情绪标的", "情绪标的（20cm）")]
    mid_trend = [s for s in all_info if s["role"] == "趋势中军"]
    followers = [s for s in all_info if s["role"] == "补涨标的"]

    anchors = []
    anchors.extend(leaders[:3])
    anchors.extend(mid_trend[:2])
    anchors.extend(followers[:2])

    anchors.sort(key=lambda x: x["rise"], reverse=True)
    return anchors


def analyze_emotion_cycle(meta, market_heat):
    """第四步：判断当前情绪（三维加权：广度40%+强度35%+量能25%）"""
    limit_up = safe_int(meta.get("limit_up_count", 0))
    limit_down = safe_int(meta.get("limit_down_count", 0))

    h = market_heat[0] if market_heat else {}
    up_ratio = safe_float(h.get("UP_NUM_PER"))

    # === 1. 广度维度（40%）===
    # 改为加权计分：涨停数、跌停数、上涨占比分别评分后取均值
    # 涨停数量评分（权重40%）
    if limit_up >= 120:
        lu_score = 4
    elif limit_up >= 80:
        lu_score = 3
    elif limit_up >= 40:
        lu_score = 2
    elif limit_up >= 15:
        lu_score = 1
    else:
        lu_score = 0

    # 跌停数量评分（权重30%，跌停越少分越高）
    if limit_down <= 5:
        ld_score = 4
    elif limit_down <= 15:
        ld_score = 3
    elif limit_down <= 30:
        ld_score = 2
    elif limit_down <= 50:
        ld_score = 1
    else:
        ld_score = 0

    # 上涨占比评分（权重30%）
    if up_ratio >= 70:
        ur_score = 4
    elif up_ratio >= 55:
        ur_score = 3
    elif up_ratio >= 45:
        ur_score = 2
    elif up_ratio >= 35:
        ur_score = 1
    else:
        ur_score = 0

    breadth_score = round(lu_score * 0.4 + ld_score * 0.3 + ur_score * 0.3)

    # === 2. 强度维度（35%）===
    # 封板/炸板口径（修正旧版 bug）：
    #   封板 sealed = 收盘封住涨停（= 涨停数 limit_up_count，来自全市场行情全集）
    #   炸板 broken = 盘中触及涨停但收盘未封（全市场行情反推，见 fetch_data.is_broken）
    # 这两个数都来自全市场行情，与涨幅榜前 N 无关，避免旧版 103 vs 61 不一致。
    # 数据由 fetch_data 计算后写入 meta；旧数据无 sealed_count/broken_count 时回退。
    sealed = safe_int(meta.get("sealed_count", meta.get("limit_up_count", 0)))
    broken = safe_int(meta.get("broken_count", 0))
    total_touched = sealed + broken  # 今天所有触过涨停板的股票
    broken_rate = round(broken / total_touched * 100, 1) if total_touched > 0 else 0

    # 综合封板数量和炸板率：封板绝对数量也很重要，不能只看比率
    if total_touched == 0:
        strength_score = 0
    elif sealed >= 80 and broken_rate <= 25:
        strength_score = 4
    elif sealed >= 50 and broken_rate <= 40:
        strength_score = 3
    elif sealed >= 25:
        strength_score = 2
    elif sealed >= 10:
        strength_score = 1
    else:
        strength_score = 0

    # === 3. 量能维度（25%）===
    hot_index = safe_float(h.get("HOT_INDEX"))
    up_down_index = h.get("UP_DOWN_INDEX", "")

    if hot_index >= 70 and "偏热" in up_down_index:
        volume_score = 4
    elif hot_index >= 55:
        volume_score = 3
    elif hot_index >= 40:
        volume_score = 2
    elif hot_index >= 25:
        volume_score = 1
    else:
        volume_score = 0

    # === 综合加权评分 ===
    weighted = (breadth_score * 0.40 + strength_score * 0.35 + volume_score * 0.25)

    # 映射情绪阶段
    if weighted >= 3.5:
        phase = "高潮"
    elif weighted >= 2.8:
        phase = "主升"
    elif weighted >= 2.0:
        phase = "修复"
    elif weighted >= 1.2:
        phase = "调整"
    else:
        phase = "冰点"

    return {
        "phase": phase,
        "weighted_score": round(weighted, 2),
        "breadth": {"score": breadth_score, "limit_up": limit_up, "limit_down": limit_down, "up_ratio": round(up_ratio, 1)},
        "strength": {"score": strength_score, "sealed": sealed, "broken": broken, "broken_rate": broken_rate},
        "volume": {"score": volume_score, "hot_index": round(hot_index, 1), "sentiment": up_down_index},
    }


def analyze_sustainability(industry_quotes, stock_detail):
    """第五步：评估主线持续性"""
    results = []
    for ind in industry_quotes[:3]:
        name = ind.get("INDU_CLASS_NAME", "")
        day = safe_float(ind.get("INDU_LIMIT_DAY"))
        week = safe_float(ind.get("INDU_LIMIT_1W"))
        month = safe_float(ind.get("INDU_LIMIT_1M"))

        score = 0
        reasons = []
        if week > 5:
            score += 1
            reasons.append("周涨幅强势")
        if month > 0:
            score += 1
            reasons.append("月线趋势向上")
        if day > 2:
            score += 1
            reasons.append("日涨幅领先")

        if score >= 3:
            level = "强"
        elif score >= 2:
            level = "较强"
        elif score >= 1:
            level = "一般"
        else:
            level = "弱"

        results.append({
            "name": name,
            "score": score,
            "level": level,
            "reasons": reasons,
            "day_change": day,
            "week_change": week,
        })

    return results


def analyze_summary_and_observations(env, lines, emotion, anchors, index_quotes):
    """
    生成结构性总结与观察点（Python 固定，LLM 必须引用，不得自创）

    输出三块：
      - market_summary: 一句话总结（含 status/phase/core_line/second_line）
      - observation_points: 明日观察重点（规则触发，LLM 必须全部涵盖）
      - key_judgments: 当日关键判断（规则触发，LLM 必须在报告引用）
    """
    main_lines = lines.get("main_lines", [])
    secondary = lines.get("secondary_hot", [])

    core = main_lines[0] if len(main_lines) >= 1 else {}
    second = main_lines[1] if len(main_lines) >= 2 else {}
    core_name = core.get("name", "未知")
    second_name = second.get("name", "未知")

    status = env.get("status", "未知")
    phase = emotion.get("phase", "未知")

    # ===== 1. market_summary =====
    market_summary = {
        "one_line": f"市场处于「{status}·{phase}」阶段，结构性机会集中在 {core_name}（核心）+ {second_name}（第二主线）",
        "status": status,
        "phase": phase,
        "core_line": core_name,
        "second_line": second_name,
    }

    # ===== 2. observation_points =====
    obs = []
    limit_up_core = core.get("limit_up_count", 0)
    if limit_up_core >= 3 and len(anchors) >= 2:
        # 从锚点里筛出属于核心主线的票取前两名，避免张冠李戴
        # （旧版取全局 anchors[0]/[1]，可能属其他板块，如核心是玻纤却写出面板股）
        core_anchors = [a for a in anchors if a.get("industry") == core_name]
        pick = core_anchors if len(core_anchors) >= 2 else anchors
        a0 = pick[0].get("name", "")
        a1 = pick[1].get("name", "") if len(pick) >= 2 else ""
        focus = f"关注 {a0}、{a1} 能否守住高位" if a1 else f"关注 {a0} 能否守住高位"
        obs.append(f"{core_name} 板块涨停股次日分化情况，{focus}")
    elif limit_up_core >= 1:
        obs.append(f"{core_name} 板块 {limit_up_core} 只涨停后能否扩散到更多成分股")

    second_week = second.get("week_change", 0)
    if second_week >= 20:
        obs.append(f"{second_name}（周涨幅 {second_week:.1f}%）高位持续性，是否出现分歧")

    attack_secondary = [s for s in secondary if s.get("line_type") == "资金攻击型"]
    if attack_secondary:
        names = "、".join(s["name"] for s in attack_secondary[:3])
        obs.append(f"次级热点（{names}）能否接力补涨")
    elif secondary:
        obs.append("次级热点缺少资金攻击型方向，主线扩散力度待观察")

    hot_index = env.get("hot_index", 0)
    if hot_index < 50:
        obs.append(f"大盘温度（{hot_index:.1f}）能否回升至 50 以上")

    up_ratio = env.get("up_ratio", 0)
    if up_ratio < 50:
        obs.append(f"上涨家数比（{up_ratio:.1f}%）能否突破 50%")

    limit_down = env.get("limit_down", 0)
    if limit_down >= 30:
        obs.append(f"跌停家数（{limit_down} 家）能否回落到 20 家以下")

    limit_up_total = env.get("limit_up", 0)
    if limit_down >= limit_up_total and limit_up_total > 0:
        obs.append(f"跌停 {limit_down} 家 ≥ 涨停 {limit_up_total} 家，注意杀跌风险是否扩散")

    # 指数判断
    idx_map = {i["name"]: i for i in index_quotes}
    sh = idx_map.get("上证指数", {})
    sz = idx_map.get("深证成指", {})
    cy = idx_map.get("创业板指", {})
    sh_pct = sh.get("change_pct", 0)
    sz_pct = sz.get("change_pct", 0)
    cy_pct = cy.get("change_pct", 0)
    if sh_pct <= -1:
        obs.append(f"沪指（{sh_pct:+.2f}%）能否企稳，权重走弱是否拖累整体情绪")
    if cy_pct >= 1.5:
        obs.append(f"创业板（{cy_pct:+.2f}%）领涨能否延续，成长风格是否持续占优")

    # ===== 3. key_judgments =====
    judgments = []
    rising = env.get("rising_industries", 0)
    falling = env.get("falling_industries", 0)
    if rising + falling > 0:
        if rising <= falling * 0.5:
            judgments.append(f"行业涨跌比 {rising}/{falling}，下跌方向占绝对多数")
        elif rising >= falling * 2:
            judgments.append(f"行业涨跌比 {rising}/{falling}，上涨方向占绝对多数")

    if limit_up_total > 0 and limit_up_core / limit_up_total >= 0.3:
        pct = limit_up_core / limit_up_total * 100
        judgments.append(f"{core_name} 贡献 {limit_up_core} 只涨停（占全市场 {pct:.0f}%），资金高度集中")

    if second_week >= 25:
        judgments.append(f"{second_name} 周涨幅 {second_week:.1f}%，处于高位")

    for s in secondary:
        if s.get("composite_score", 0) >= 70:
            judgments.append(f"{s['name']}（得分 {s['composite_score']}）接近主线强度，可能接力")

    sealed = emotion.get("strength", {}).get("sealed", 0)
    broken = emotion.get("strength", {}).get("broken", 0)
    broken_rate = emotion.get("strength", {}).get("broken_rate", 0)
    # 封板率 = 封板数 / (封板数+炸板数)，反映资金封涨停的坚决程度。
    # 按封板率分档输出客观判断，避免旧版『broken_rate==0 就无脑说坚决』。
    if sealed + broken == 0:
        pass  # 无涨停无炸板，不输出封板相关判断
    elif broken_rate >= 40:
        judgments.append(f"封板 {sealed} 家、炸板 {broken} 家，封板率仅 {100-broken_rate:.0f}%，封板意愿弱、追涨风险高")
    elif broken_rate >= 20:
        judgments.append(f"封板 {sealed} 家、炸板 {broken} 家，封板率 {100-broken_rate:.0f}%，封板一般")
    else:
        judgments.append(f"封板 {sealed} 家、炸板 {broken} 家，封板率 {100-broken_rate:.0f}%，资金封板坚决")

    if (sh_pct > 0) != (sz_pct > 0):
        judgments.append(f"沪深分化：沪指 {sh_pct:+.2f}% / 深指 {sz_pct:+.2f}%，资金风格切换")

    return {
        "market_summary": market_summary,
        "observation_points": obs,
        "key_judgments": judgments,
    }


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else "latest"

    print(f"=== A股主线识别数据分析 ===")

    # 加载数据
    heat = load("market_heat.json")
    index_quotes = load("index_quotes.json")
    industry_quotes = load("industry_quotes.json")
    try:
        industry_l2_quotes = load("industry_l2_quotes.json")
    except FileNotFoundError:
        industry_l2_quotes = []
    stock_top_rise = load("stock_top_rise.json")
    # 涨停股全集（封板成功的全部股票）。
    # 旧版只有 stock_top_rise（涨幅榜前100），会丢失非涨幅靠前的涨停股，
    # 导致主线/锚点/情绪分析用的涨停股不全（如 103 vs 61 不一致）。
    try:
        limit_up_full = load("limit_up_full.json")
    except FileNotFoundError:
        limit_up_full = None
    # 若全集缺失或数量明显少于 meta 记录，回退到涨幅榜（并记录告警）
    if not limit_up_full:
        print("  [WARN] limit_up_full.json 缺失，回退到 stock_top_rise（涨停股可能不全）")
        limit_up_full = [s for s in stock_top_rise if is_limit_up(s)]
    abnormal_trade = load("abnormal_trade.json")
    stock_value = load("stock_value.json")
    stock_detail = load("stock_detail.json")
    meta_data = load("meta.json")
    meta = meta_data[0] if meta_data else {}

    # === 数据一致性自检（防止旧版『涨停103 vs 封板61』不一致再次发生）===
    # meta.limit_up_count 是 fetch 阶段全市场统计的涨停数；
    # limit_up_full 是写盘的全集。两者必须一致，否则下游主线/锚点/情绪全部偏。
    meta_lu = safe_int(meta.get("limit_up_count"))
    if meta_lu is not None and len(limit_up_full) != meta_lu:
        print(f"  [WARN][一致性] 涨停股全集 {len(limit_up_full)} 家 ≠ meta.limit_up_count {meta_lu} 家，"
              f"可能 fetch 取数不全或 data/ 目录陈旧，建议重新运行 fetch_data.py")
    # 封板+炸板应 ≥ 涨停数（封板就是涨停的子集，炸板是额外触板的）
    sealed = safe_int(meta.get("sealed_count", meta.get("limit_up_count", 0)))
    broken = safe_int(meta.get("broken_count", 0))
    if sealed and sealed + broken < sealed:
        print(f"  [WARN][一致性] 封板 {sealed} + 炸板 {broken} < 封板数本身，meta 数据异常")

    # 六步分析
    print("[1/6] 市场环境...")
    env = analyze_market_environment(heat, industry_l2_quotes or industry_quotes, meta)

    print("[2/6] 主线识别...")
    lines = analyze_main_lines(industry_l2_quotes or industry_quotes, limit_up_full, abnormal_trade, stock_detail)

    print("[3/6] 核心锚点...")
    main_line_names = [m["name"] for m in lines["main_lines"]]
    # 传递 L2 标准名清单给锚点分析，确保行业匹配跟主线识别一致
    l2_std_set = set(ind.get("INDU_CLASS_NAME", "") for ind in (industry_l2_quotes or industry_quotes)
                     if ind.get("INDU_CLASS_NAME"))
    anchors = analyze_anchor_stocks(limit_up_full, stock_value, safe_int(meta.get("limit_up_count", 0)),
                                    main_line_names=main_line_names, stock_detail=stock_detail,
                                    l2_standard_names=l2_std_set)

    print("[4/6] 情绪周期...")
    emotion = analyze_emotion_cycle(meta, heat)

    print("[5/6] 持续性评估...")
    sustainability = analyze_sustainability(industry_quotes, stock_detail)

    print("[6/6] 明日观察重点...")

    # 保存分析结果（精简字段，减少大模型 token 消耗）
    slim_industries = []
    for i in industry_quotes:
        slim_industries.append({
            "name": i.get("INDU_CLASS_NAME", ""),
            "day": safe_float(i.get("INDU_LIMIT_DAY")),
            "week": safe_float(i.get("INDU_LIMIT_1W")),
            "month": safe_float(i.get("INDU_LIMIT_1M")),
            "compo_num": int(safe_float(i.get("INDU_COMPO_NUM"))),
        })

    slim_limit_ups = []
    for s in lines.get("limit_up_stocks", []):
        slim_limit_ups.append({
            "code": s.get("STK_CODE", ""),
            "name": s.get("STK_SHORT_NAME", ""),
            "rise": safe_float(s.get("PRICE_LIMIT")),
            "amount": round(safe_float(s.get("TRADE_AMUT")) / 1e8, 2),
        })

    # 按三级行业归类涨停股
    detail_map = {r["code"]: r for r in stock_detail}
    industry_groups = {}
    for s in slim_limit_ups:
        info = detail_map.get(s["code"], {})
        ind = info.get("sw_industry_s") or info.get("sw_industry_q") or "未知"
        if ind not in industry_groups:
            industry_groups[ind] = []
        industry_groups[ind].append(s)
    sorted_industry_groups = sorted(industry_groups.items(), key=lambda x: len(x[1]), reverse=True)
    limit_up_by_industry = [{"industry": ind, "count": len(stocks), "stocks": stocks}
                            for ind, stocks in sorted_industry_groups]

    slim_abnormal = {}
    for k, v in lines.get("active_directions", {}).items():
        slim_abnormal[k] = {
            "code": v.get("code", ""),
            "rise": v.get("rise", 0),
            "type": v.get("abnorm_type", ""),
        }

    slim_index = []
    for idx in index_quotes:
        slim_index.append({
            "name": idx.get("IND_SHORT_NAME", ""),
            "close": safe_float(idx.get("CLOSE_PRICE")),
            "pre_close": safe_float(idx.get("PRE_CLOSE_PRICE")),
            "change_pct": safe_float(idx.get("PRI_LIMIT")),
            "open": safe_float(idx.get("OPEN_PRICE")),
            "high": safe_float(idx.get("HIGH_PRICE")),
            "low": safe_float(idx.get("LOW_PRICE")),
            "amount": round(safe_float(idx.get("TRADE_AMUT")) / 1e8, 1),
        })

    summary_pkg = analyze_summary_and_observations(env, lines, emotion, anchors, slim_index)

    analysis = {
        "date": meta.get("date", date),
        "index_quotes": slim_index,
        "environment": env,
        "main_lines": {
            "main_lines": lines["main_lines"],
            "secondary_hot": lines["secondary_hot"],
            "bottom_industries": lines["bottom_industries"],
            "l2_limit_count": lines.get("l2_limit_count", {}),
        },
        "anchors": anchors,
        "emotion": emotion,
        "sustainability": sustainability,
        "industry_quotes_all": slim_industries,
        "limit_up_details": slim_limit_ups,
        "limit_up_by_industry": limit_up_by_industry,
        "abnormal_summary": slim_abnormal,
        "market_summary": summary_pkg["market_summary"],
        "observation_points": summary_pkg["observation_points"],
        "key_judgments": summary_pkg["key_judgments"],
    }

    output = DATA_DIR / "analysis.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print(f"\n=== 分析完成！结果已保存到 {output} ===")
    print(f"市场状态: {env['status']}, 操作建议: {env['action']}")
    print(f"情绪周期: {emotion['phase']}, 综合评分: {emotion['weighted_score']}, 涨停: {emotion['breadth']['limit_up']}家")


if __name__ == "__main__":
    main()
