#!/usr/bin/env python3
"""
投资委员会行情抓取脚本
主数据源：腾讯 qt.gtimg.cn（免费，无需 API key，实时行情）
备用数据源：stooq.com（历史K线回退）

支持：A股、港股、美股、BTC/加密、黄金/外汇

用法：
  python3 fetch_price.py GOOGL          # 美股
  python3 fetch_price.py 700            # 港股腾讯
  python3 fetch_price.py GOOGL 700 BTC  # 多标的
"""

import sys
import subprocess
import json
from datetime import datetime, timedelta

# ── 符号映射：用户输入 → 腾讯代码 ──
TENCENT_MAP = {
    # 美股
    'GOOGL': 'usGOOGL',  'GOOG':  'usGOOG',
    'NVDA':  'usNVDA',   'AAPL':  'usAAPL',
    'MSFT':  'usMSFT',   'AMZN':  'usAMZN',
    'META':  'usMETA',   'TSLA':  'usTSLA',
    'BABA':  'usBABA',   'PDD':   'usPDD',
    'QQQ':   'usQQQ',    'SPY':   'usSPY',
    'TLT':   'usTLT',
    # A股
    '600519': 'sh600519', '000858': 'sz000858',  # 茅台、五粮液
    '601318': 'sh601318', '000002': 'sz000002',  # 平安、万科
    '300750': 'sz300750', '688981': 'sh688981',  # 宁德、中芯
    '茅台':    'sh600519', '平安':    'sh601318',
    '宁德':    'sz300750',
    # 港股
    '700':   'hk00700',  '9988':  'hk09988',
    '3690':  'hk03690',  '1810':  'hk01810',
    '9618':  'hk09618',  '2318':  'hk02318',
    # 加密（ETF 代理，腾讯无直接加密行情）
    'BTC':   'usIBIT',   'GBTC':  'usGBTC',
    'ETH':   'usETHA',   'SOL':   'usSOL.CC',
    # 商品（ETF 代理）
    'GOLD':  'usGLD',    '黄金':   'usGLD',
}

# stooq 回退映射（历史数据用）
STOOQ_MAP = {
    'GOOGL': 'googl.us', 'GOOG': 'goog.us',
    'NVDA': 'nvda.us',   'AAPL': 'aapl.us',
    'MSFT': 'msft.us',   'AMZN': 'amzn.us',
    'META': 'meta.us',   'TSLA': 'tsla.us',
    'BABA': 'baba.us',   'PDD':  'pdd.us',
    'QQQ':  'qqq.us',    'SPY':  'spy.us',
    'TLT':  'tlt.us',
    '700':  '700.hk',    '9988': '9988.hk',
    '3690': '3690.hk',
    'BTC':  'btc.v',     'ETH':  'eth.v',
    'SOL':  'sol.v',
    'GOLD': 'xauusd',    '黄金':  'xauusd',
}


def normalize_tencent(s):
    """用户输入 → 腾讯接口代码"""
    key = s.upper().strip()
    if key in TENCENT_MAP:
        return TENCENT_MAP[key]
    # 纯数字 → 区分 A 股和港股
    if key.isdigit():
        if len(key) == 6:
            # 6 位数字 = A 股
            if key.startswith(('60', '68')):
                return f'sh{key}'   # 上海
            elif key.startswith(('00', '30', '02')):
                return f'sz{key}'   # 深圳
        # 其他数字 → 港股
        return f'hk{key.zfill(5)}'
    # 已带前缀（hk00700, usAAPL）直接用
    if key.startswith(('HK', 'US', 'SH', 'SZ')):
        return key.lower()[:2] + key[2:]
    # 默认当美股
    return f'us{key}'


def normalize_stooq(s):
    """用户输入 → stooq 代码"""
    key = s.upper().strip()
    if key in STOOQ_MAP:
        return STOOQ_MAP[key]
    return s.lower().replace('.HK', '.hk').replace('.US', '.us')


def curl_get(url, encoding='utf-8'):
    """用 curl 发请求，避免依赖 requests 库"""
    try:
        result = subprocess.run(
            ['curl', '-s', '-m', '10', url],
            capture_output=True, timeout=15
        )
        raw = result.stdout
        if encoding == 'gbk':
            return raw.decode('gbk', errors='replace')
        return raw.decode('utf-8', errors='replace')
    except Exception:
        return None


# ── 腾讯接口（主） ──

def fetch_tencent(symbols_raw):
    """批量获取腾讯实时行情，返回 {原始输入: quote_dict}"""
    mapping = {}  # tencent_code → raw_input
    codes = []
    for s in symbols_raw:
        code = normalize_tencent(s)
        codes.append(code)
        mapping[code] = s

    url = f'http://qt.gtimg.cn/q={",".join(codes)}'
    text = curl_get(url, encoding='gbk')
    if not text:
        return {}

    results = {}
    for line in text.strip().split(';'):
        line = line.strip()
        if not line or '=' not in line:
            continue
        # v_hk00700="..."
        var_name, _, raw_val = line.partition('=')
        val = raw_val.strip('"')
        fields = val.split('~')
        if len(fields) < 45:
            continue

        code_key = var_name.replace('v_', '')
        raw_input = mapping.get(code_key, code_key)

        try:
            close = float(fields[3])
            prev_close = float(fields[4]) if fields[4] else None
            high = float(fields[33]) if fields[33] else close
            low = float(fields[34]) if fields[34] else close
            open_price = float(fields[5]) if fields[5] else close
            change_pct = float(fields[32]) if fields[32] else None
        except (ValueError, IndexError):
            continue

        results[raw_input] = {
            'symbol_raw': raw_input,
            'name':       fields[1],
            'code':       fields[2],
            'close':      close,
            'prev_close': prev_close,
            'open':       open_price,
            'high':       high,
            'low':        low,
            'change_pct': change_pct,
            'volume':     fields[36] if len(fields) > 36 else 'N/A',
            'pe':         fields[39] if len(fields) > 39 else 'N/A',
            'market_cap': fields[45] if len(fields) > 45 else 'N/A',
            'w52_high':   fields[47] if len(fields) > 47 else 'N/A',
            'w52_low':    fields[48] if len(fields) > 48 else 'N/A',
            'time':       fields[30] if len(fields) > 30 else '',
            'currency':   fields[61] if len(fields) > 61 else '',
            'source':     'tencent',
        }
    return results


# ── stooq 接口（备用） ──

def fetch_stooq(symbol_raw, days_back=5):
    """单只查询 stooq 历史数据"""
    sym = normalize_stooq(symbol_raw)
    today = datetime.now()
    d2 = today.strftime('%Y%m%d')
    d1 = (today - timedelta(days=days_back)).strftime('%Y%m%d')

    url = f'https://stooq.com/q/d/l/?s={sym}&d1={d1}&d2={d2}&i=d'
    text = curl_get(url)
    if not text:
        return None
    lines = text.strip().split('\n')
    if len(lines) < 2:
        return None
    last = lines[-1].split(',')
    try:
        return {
            'symbol_raw': symbol_raw,
            'name':       symbol_raw,
            'code':       sym,
            'close':      float(last[4]),
            'prev_close': float(lines[-2].split(',')[4]) if len(lines) >= 3 else None,
            'open':       float(last[1]),
            'high':       float(last[2]),
            'low':        float(last[3]),
            'change_pct': None,
            'volume':     last[5] if len(last) > 5 else 'N/A',
            'pe':         'N/A',
            'market_cap': 'N/A',
            'w52_high':   'N/A',
            'w52_low':    'N/A',
            'time':       last[0],
            'currency':   '',
            'source':     'stooq',
        }
    except (ValueError, IndexError):
        return None


# ── 输出格式化 ──

def format_quote(q):
    if not q:
        return '❌ 无数据'

    # 涨跌
    if q['change_pct'] is not None:
        chg = q['change_pct']
    elif q['prev_close']:
        chg = (q['close'] - q['prev_close']) / q['prev_close'] * 100
    else:
        chg = None

    arrow = '📈' if chg and chg >= 0 else '📉'
    pct_str = f'  {arrow} {chg:+.2f}%' if chg is not None else ''

    pe_str = f'  PE:{q["pe"]}' if q['pe'] != 'N/A' and q['pe'] else ''
    cap_str = ''
    if q['market_cap'] != 'N/A' and q['market_cap']:
        try:
            cap = float(q['market_cap'])
            if cap > 10000:
                cap_str = f'  市值:{cap/10000:.0f}万亿'
            elif cap > 1:
                cap_str = f'  市值:{cap:.0f}亿'
        except ValueError:
            pass

    src = f'[{q["source"]}]' if q.get('source') == 'stooq' else ''

    name = q.get('name', '')
    return (
        f'{name}  ${q["close"]:.2f}'
        f'  (H:{q["high"]:.2f} / L:{q["low"]:.2f})'
        f'{pct_str}{pe_str}{cap_str}'
        f'  [{q["time"]}] {src}'
    )


def fetch_all(targets):
    """主入口：先用腾讯批量拉，失败的走 stooq 回退"""
    # 腾讯批量
    results = fetch_tencent(targets)

    # stooq 回退
    for t in targets:
        if t not in results:
            q = fetch_stooq(t)
            if q:
                results[t] = q

    return results


if __name__ == '__main__':
    targets = sys.argv[1:] if len(sys.argv) > 1 else ['700', 'AAPL', 'BTC', 'GOLD']
    results = fetch_all(targets)
    for t in targets:
        q = results.get(t)
        print(f'{t:15s} {format_quote(q)}')
