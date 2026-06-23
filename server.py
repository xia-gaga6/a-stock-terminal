"""
A股金融终端 — Flask 后端
提供前端所需的所有真实数据接口
"""
import time
import random
import uuid
import json
import math
import urllib.request
import requests
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────
# 公共 Helper
# ─────────────────────────────────────────────────────────
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

EM_SESSION = requests.Session()
EM_SESSION.headers.update({"User-Agent": UA})
EM_MIN_INTERVAL = 1.0
_em_last_call = [0.0]

def em_get(url, params=None, headers=None, timeout=15, **kwargs):
    wait = EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.4))
    try:
        return EM_SESSION.get(url, params=params, headers=headers, timeout=timeout, **kwargs)
    finally:
        _em_last_call[0] = time.time()

DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

def eastmoney_datacenter(report_name, columns="ALL", filter_str="", page_size=50,
                          sort_columns="", sort_types="-1"):
    params = {
        "reportName": report_name, "columns": columns,
        "filter": filter_str, "pageNumber": "1", "pageSize": str(page_size),
        "sortColumns": sort_columns, "sortTypes": sort_types,
        "source": "WEB", "client": "WEB",
    }
    r = em_get(DATACENTER_URL, params=params, timeout=15)
    d = r.json()
    if d.get("result") and d["result"].get("data"):
        return d["result"]["data"]
    return []

def get_prefix(code):
    if code.startswith(("6", "9")):
        return "sh"
    elif code.startswith("8"):
        return "bj"
    return "sz"

def ok(data):
    return jsonify({"code": 0, "data": data})

def err(msg):
    return jsonify({"code": -1, "msg": msg}), 500

# ─────────────────────────────────────────────────────────
# 1. 行情 — 腾讯财经（不封IP）
# ─────────────────────────────────────────────────────────
def tencent_quote(codes):
    prefixed = [f"{get_prefix(c)}{c}" for c in codes]
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("gbk")

    result = {}
    for line in raw.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        code = key[2:]
        result[code] = {
            "name":         vals[1],
            "price":        float(vals[3]) if vals[3] else 0,
            "last_close":   float(vals[4]) if vals[4] else 0,
            "open":         float(vals[5]) if vals[5] else 0,
            "change_amt":   float(vals[31]) if vals[31] else 0,
            "change_pct":   float(vals[32]) if vals[32] else 0,
            "high":         float(vals[33]) if vals[33] else 0,
            "low":          float(vals[34]) if vals[34] else 0,
            "amount_wan":   float(vals[37]) if vals[37] else 0,
            "turnover_pct": float(vals[38]) if vals[38] else 0,
            "pe_ttm":       float(vals[39]) if vals[39] else 0,
            "amplitude_pct":float(vals[43]) if vals[43] else 0,
            "mcap_yi":      float(vals[44]) if vals[44] else 0,
            "float_mcap_yi":float(vals[45]) if vals[45] else 0,
            "pb":           float(vals[46]) if vals[46] else 0,
            "limit_up":     float(vals[47]) if vals[47] else 0,
            "limit_down":   float(vals[48]) if vals[48] else 0,
            "vol_ratio":    float(vals[49]) if vals[49] else 0,
            "pe_static":    float(vals[52]) if vals[52] else 0,
        }
    return result

@app.route("/api/quote")
def api_quote():
    """批量行情：?codes=000001,000300,399006"""
    raw = request.args.get("codes", "000001,000300,399006,399001")
    codes = [c.strip() for c in raw.split(",") if c.strip()]
    try:
        data = tencent_quote(codes)
        return ok(data)
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 2. 大盘指数列表（固定四大指数）
# ─────────────────────────────────────────────────────────
@app.route("/api/indices")
def api_indices():
    codes = ["000001", "000300", "399006", "000688"]  # 上证/沪深300/创业板/科创50
    try:
        q = tencent_quote(codes)
        result = []
        labels = {"000001": "上证指数", "000300": "沪深300", "399006": "创业板指", "000688": "科创50"}
        for c in codes:
            d = q.get(c, {})
            d["label"] = labels.get(c, c)
            d["code"] = c
            result.append(d)
        return ok(result)
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 3. 个股完整信息（行情 + 基本面 + 资金流）
# ─────────────────────────────────────────────────────────
@app.route("/api/stock")
def api_stock():
    code = request.args.get("code", "").strip().lstrip("0") .zfill(6)
    if not code or len(code) != 6:
        return err("请提供6位股票代码")
    try:
        # 行情
        q = tencent_quote([code]).get(code, {})

        # 东财基本面
        market_code = 1 if code.startswith("6") else 0
        info_url = "https://push2.eastmoney.com/api/qt/stock/get"
        info_params = {
            "fltt": "2", "invt": "2",
            "fields": "f57,f58,f84,f85,f127,f116,f117,f189,f43",
            "secid": f"{market_code}.{code}",
        }
        try:
            r = em_get(info_url, params=info_params, timeout=10)
            idata = r.json().get("data", {})
        except:
            idata = {}

        info = {
            "industry": idata.get("f127", ""),
            "total_shares": idata.get("f84", 0),
            "float_shares": idata.get("f85", 0),
            "list_date": str(idata.get("f189", "")),
        }

        # 最近5日资金流
        try:
            flow_data = stock_fund_flow_internal(code)
            recent_flow = flow_data[-5:] if flow_data else []
        except:
            recent_flow = []

        return ok({
            "code": code,
            "quote": q,
            "info": info,
            "fund_flow": recent_flow,
        })
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 4. 行业板块排行
# ─────────────────────────────────────────────────────────
@app.route("/api/industry")
def api_industry():
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1", "pz": "50", "po": "1", "np": "1",
            "fltt": "2", "invt": "2",
            "fs": "m:90+t:2",
            "fields": "f2,f3,f4,f12,f13,f14,f104,f105,f128,f136,f140,f141,f207",
        }
        r = em_get(url, params=params, timeout=15)
        items = r.json().get("data", {}).get("diff", [])
        rows = []
        for i, item in enumerate(items[:30]):
            rows.append({
                "rank": i + 1,
                "name": item.get("f14", ""),
                "change_pct": round(float(item.get("f3", 0) or 0), 2),
                "code": item.get("f12", ""),
                "up_count": item.get("f104", 0),
                "down_count": item.get("f105", 0),
                "leader": item.get("f140", ""),
                "leader_change": round(float(item.get("f136", 0) or 0), 2),
            })
        return ok(rows)
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 5. 同花顺热点强势股
# ─────────────────────────────────────────────────────────
@app.route("/api/hot")
def api_hot():
    try:
        today = date.today().strftime("%Y-%m-%d")
        url = (f"http://zx.10jqka.com.cn/event/api/getharden/"
               f"date/{today}/orderby/date/orderway/desc/charset/GBK/")
        headers = {"User-Agent": UA}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if data.get("errocode", 0) != 0:
            return err(f"同花顺热点: {data.get('errormsg')}")
        rows = []
        for item in (data.get("data") or [])[:50]:
            rows.append({
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "reason": item.get("reason", ""),
                "change_pct": float(item.get("zhangfu", 0) or 0),
                "turnover": float(item.get("huanshou", 0) or 0),
                "amount": item.get("chengjiaoe", ""),
            })
        return ok(rows)
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 6. 东财全球资讯（7x24）
# ─────────────────────────────────────────────────────────
@app.route("/api/news")
def api_news():
    try:
        url = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"
        params = {
            "client": "web", "biz": "web_724",
            "fastColumn": "102", "sortEnd": "",
            "pageSize": "50",
            "req_trace": str(uuid.uuid4()),
        }
        headers = {"User-Agent": UA, "Referer": "https://kuaixun.eastmoney.com/"}
        r = em_get(url, params=params, headers=headers, timeout=10)
        rows = []
        for item in r.json().get("data", {}).get("fastNewsList", []):
            rows.append({
                "title": item.get("title", ""),
                "summary": item.get("summary", "")[:200],
                "time": item.get("showTime", ""),
            })
        return ok(rows)
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 7. 北向资金（同花顺）
# ─────────────────────────────────────────────────────────
@app.route("/api/northbound")
def api_northbound():
    try:
        url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
        headers = {
            "User-Agent": UA,
            "Host": "data.hexin.cn",
            "Referer": "https://data.hexin.cn/",
        }
        r = requests.get(url, headers=headers, timeout=10)
        d = r.json()
        times = d.get("time", [])
        hgt = d.get("hgt", [])
        sgt = d.get("sgt", [])
        n = len(times)
        rows = []
        for i in range(n):
            rows.append({
                "time": times[i],
                "hgt": float(hgt[i]) if i < len(hgt) and hgt[i] is not None else None,
                "sgt": float(sgt[i]) if i < len(sgt) and sgt[i] is not None else None,
            })
        return ok(rows)
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 8. 个股资金流（120日）
# ─────────────────────────────────────────────────────────
def stock_fund_flow_internal(code):
    market_code = 1 if code.startswith("6") else 0
    url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    params = {
        "secid": f"{market_code}.{code}",
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",
        "lmt": "120",
    }
    headers = {"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"}
    r = em_get(url, params=params, headers=headers, timeout=15)
    klines = r.json().get("data", {}).get("klines", [])
    rows = []
    for line in klines:
        parts = line.split(",")
        if len(parts) >= 6:
            rows.append({
                "date": parts[0],
                "main_net": float(parts[1]) if parts[1] != "-" else 0,
                "small_net": float(parts[2]) if parts[2] != "-" else 0,
                "mid_net": float(parts[3]) if parts[3] != "-" else 0,
                "large_net": float(parts[4]) if parts[4] != "-" else 0,
                "super_net": float(parts[5]) if parts[5] != "-" else 0,
            })
    return rows

@app.route("/api/fundflow")
def api_fundflow():
    code = request.args.get("code", "").strip().zfill(6)
    if not code or len(code) != 6:
        return err("请提供6位股票代码")
    try:
        rows = stock_fund_flow_internal(code)
        return ok(rows)
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 9. 全市场龙虎榜
# ─────────────────────────────────────────────────────────
@app.route("/api/dragonboard")
def api_dragonboard():
    trade_date = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    try:
        data = eastmoney_datacenter(
            "RPT_DAILYBILLBOARD_DETAILSNEW",
            filter_str=f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
            page_size=200,
            sort_columns="BILLBOARD_NET_AMT", sort_types="-1",
        )
        if not data:
            # 尝试昨天
            yd = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            data = eastmoney_datacenter(
                "RPT_DAILYBILLBOARD_DETAILSNEW",
                filter_str=f"(TRADE_DATE>='{yd}')(TRADE_DATE<='{yd}')",
                page_size=200,
                sort_columns="BILLBOARD_NET_AMT", sort_types="-1",
            )
        stocks = []
        for row in data:
            stocks.append({
                "code": row.get("SECURITY_CODE", ""),
                "name": row.get("SECURITY_NAME_ABBR", ""),
                "reason": row.get("EXPLANATION", ""),
                "close": float(row.get("CLOSE_PRICE") or 0),
                "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
                "net_buy_wan": round(float((row.get("BILLBOARD_NET_AMT") or 0)) / 10000, 1),
                "buy_wan": round(float((row.get("BILLBOARD_BUY_AMT") or 0)) / 10000, 1),
                "sell_wan": round(float((row.get("BILLBOARD_SELL_AMT") or 0)) / 10000, 1),
                "turnover_pct": round(float(row.get("TURNOVERRATE") or 0), 2),
            })
        return ok({"date": trade_date, "total": len(stocks), "stocks": stocks})
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 10. K线数据（百度股市通，带MA）
# ─────────────────────────────────────────────────────────
@app.route("/api/kline")
def api_kline():
    code = request.args.get("code", "").strip().zfill(6)
    if not code or len(code) != 6:
        return err("请提供6位股票代码")
    try:
        url = "https://finance.pae.baidu.com/selfselect/getstockquotation"
        params = {
            "all": "1", "isIndex": "false", "isBk": "false", "isBlock": "false",
            "isFutures": "false", "isStock": "true", "newFormat": "1",
            "group": "quotation_kline_ab", "finClientType": "pc",
            "code": code, "start_time": "", "ktype": "1",
        }
        headers = {
            "User-Agent": UA,
            "Accept": "application/vnd.finance-web.v1+json",
            "Origin": "https://gushitong.baidu.com",
            "Referer": "https://gushitong.baidu.com/",
        }
        r = requests.get(url, params=params, headers=headers, timeout=10)
        d = r.json()
        md = d.get("Result", {}).get("newMarketData", {})
        keys = md.get("keys", [])
        rows_raw = md.get("marketData", "").split(";")
        rows = []
        for raw in rows_raw:
            if not raw.strip():
                continue
            parts = raw.split(",")
            if len(parts) < len(keys):
                continue
            row = {}
            for i, k in enumerate(keys):
                row[k] = parts[i] if i < len(parts) else ""
            rows.append(row)
        # 只返回最近120根
        return ok({"keys": keys, "rows": rows[-120:]})
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 11. 股票搜索（腾讯查询接口）
# ─────────────────────────────────────────────────────────
@app.route("/api/search")
def api_search():
    kw = request.args.get("kw", "").strip()
    if not kw:
        return ok([])
    try:
        url = f"https://smartbox.gtimg.cn/s3/?v=2&q={kw}&type=N&count=10"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", UA)
        resp = urllib.request.urlopen(req, timeout=5)
        raw = resp.read().decode("utf-8")
        # 格式: v_hint="...~股票~代码~名称..."
        inner = raw.split('"')[1] if '"' in raw else ""
        parts = [p for p in inner.split("^") if p]
        result = []
        for p in parts[:8]:
            fields = p.split("~")
            if len(fields) >= 3:
                result.append({
                    "code": fields[1],
                    "name": fields[2],
                    "type": fields[0],
                })
        return ok(result)
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 12. 个股新闻
# ─────────────────────────────────────────────────────────
@app.route("/api/stocknews")
def api_stocknews():
    code = request.args.get("code", "").strip().zfill(6)
    if not code:
        return err("请提供股票代码")
    try:
        cb = "jQuery_news"
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        inner_params = json.dumps({
            "uid": "",
            "keyword": code,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {"cmsArticleWebOld": {
                "searchScope": "default", "sort": "default",
                "pageIndex": 1, "pageSize": 20,
                "preTag": "", "postTag": "",
            }},
        }, separators=(',', ':'))
        params = {"cb": cb, "param": inner_params}
        headers = {"User-Agent": UA, "Referer": "https://so.eastmoney.com/"}
        r = em_get(url, params=params, headers=headers, timeout=15)
        text = r.text
        json_str = text[text.index("(") + 1: text.rindex(")")]
        d = json.loads(json_str)
        articles = d.get("result", {}).get("cmsArticleWebOld", []) or []
        import re
        rows = []
        for a in articles:
            rows.append({
                "title": re.sub(r'<[^>]+>', '', a.get("title", "")),
                "content": re.sub(r'<[^>]+>', '', a.get("content", ""))[:200],
                "time": a.get("date", ""),
                "source": a.get("mediaName", ""),
                "url": a.get("url", ""),
            })
        return ok(rows)
    except Exception as e:
        return err(str(e))

# ─────────────────────────────────────────────────────────
# 健康检测
# ─────────────────────────────────────────────────────────
@app.route("/api/ping")
def api_ping():
    return ok({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": "ok"})

if __name__ == "__main__":
    print("=" * 50)
    print("A股金融终端 后端服务启动中...")
    print("访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
