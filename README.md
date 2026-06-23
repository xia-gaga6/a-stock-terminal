# A股金融终端 — 使用说明

## 快速启动

### 第一步：启动后端
双击 `start.bat`，或者在终端执行：
```
C:\Users\HP\.workbuddy\binaries\python\envs\default\Scripts\python.exe server.py
```
看到 `* Running on http://0.0.0.0:5000` 表示后端启动成功。

### 第二步：打开前端
用浏览器打开 `index.html`，或在 WorkBuddy 里预览。

---

## 数据接口说明

| 接口 | 说明 | 数据源 |
|------|------|--------|
| `/api/indices` | 四大指数实时行情 | 腾讯财经（不封IP）|
| `/api/quote` | 批量股票行情 | 腾讯财经 |
| `/api/stock` | 个股详情 | 腾讯 + 东财 |
| `/api/industry` | 行业板块涨跌排行 | 东财 push2 |
| `/api/hot` | 同花顺当日热点强势股 | 同花顺（零鉴权）|
| `/api/news` | 全球财经资讯7x24 | 东财 |
| `/api/northbound` | 北向资金分钟流向 | 同花顺 hsgtApi |
| `/api/fundflow` | 个股资金流（日级120日）| 东财 push2his |
| `/api/dragonboard` | 全市场龙虎榜 | 东财 datacenter |
| `/api/kline` | K线（含MA5/MA20）| 百度股市通 |
| `/api/search` | 股票代码/名称搜索 | 腾讯 smartbox |
| `/api/stocknews` | 个股相关新闻 | 东财 |

## 依赖

```
pip install flask flask-cors mootdx requests pandas stockstats
```

## 东财防封说明

东财接口内置限流（间隔 ≥ 1s + 随机抖动），正常使用不会触发封禁。
行情数据走腾讯/同花顺，无封IP风险。
