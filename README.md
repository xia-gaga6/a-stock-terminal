# A股金融终端 — 使用说明

## 快速启动

### 方式一：EXE 一键启动
双击 `dist/AStockTerminal.exe`，自动启动后端并打开浏览器。

### 方式二：Python 启动
双击 `start.bat`，或在终端执行：
```
python server.py
```
看到 `* Running on http://0.0.0.0:5000` 表示后端启动成功，浏览器自动打开。

---

## 数据接口说明（22个API）

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
| `/api/research` | 研报列表+评级+EPS预测 | 东财 reportapi |
| `/api/margin` | 融资融券明细 | 东财 datacenter |
| `/api/blocktrade` | 大宗交易记录 | 东财 datacenter |
| `/api/holders` | 股东户数变化 | 东财 datacenter |
| `/api/dividend` | 分红送转历史 | 东财 datacenter |
| `/api/lockup` | 限售解禁日历 | 东财 datacenter |
| `/api/concept` | 概念板块归属 | 百度股市通 |
| `/api/finance` | 财报三表(利润/资产/现金流) | 新浪财经 |
| `/api/announcement` | 公告全文检索 | 巨潮 cninfo |
| `/api/ping` | 健康检测 | 本地 |

## 依赖

```
pip install flask flask-cors requests
```

## 东财防封说明

东财接口内置限流（间隔 ≥ 1s + 随机抖动），正常使用不会触发封禁。
行情数据走腾讯/同花顺，无封IP风险。
