"""自店の商品が、モールの検索で何番目に出るかを毎日調べる。

## APIの順位ではなく、実際の検索結果の順位を見る

**楽天もYahooも、商品検索APIの並び順は買い物客が見る画面と同じとは限らない。**
APIの順位を「検索順位」と呼ぶツールは、そこで嘘をつくことになる。
このツールは**買い物客と同じ検索結果ページ**を読んで順位を数える。

読んでよいことは robots.txt で確かめてある（2026-09-04）。

    search.rakuten.co.jp   キーワード検索の基本パスは Disallow に無い。Crawl-delay 無し
    shopping.yahoo.co.jp   同じく無い

**それでも間隔は空ける。** 店主が自分で検索して順位を見る、その代わりをする
道具なので、人が手でやるより速く叩く理由がない。

## PCとスマホ

User-Agent を変えると**別のページが返る**（2026-09-04 実測。楽天 990KB/860KB、
Yahoo 1,477KB/1,219KB と中身が違う）。ただし**そのとき並び順は同じだった。**

つまり「スマホでは順位が違う」は、いつも起きることではない。
両方見るのは差が出たときに気づくためで、**差が出るのが普通だと言ってはいけない。**
config の devices で片方だけにもできる（そのぶんモールへの負荷も半分になる）。

## 使い方

    python scripts/check_rank.py

    config/watch.json  調べる店とキーワード
    data/history.json  日ごとの順位（積み上げ）

環境変数:
  MAX_PAGES   1キーワードあたり何ページまで見るか（既定 2）
  ONLY        この件数だけ試す（動作確認用）
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / 'config' / 'watch.json'
HISTORY = ROOT / 'data' / 'history.json'

# 人が手で検索するより速く叩かない。
PAUSE = 4.0

DEVICES = {
    'pc': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
           ' (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
    'sp': ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15'
           ' (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'),
}

# 1ページに並ぶ数（実測・2026-09-04）。ページ送りの位置を数えるのに使う。
PER_PAGE = {'rakuten': 45, 'yahoo': 30}


def load(path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return fallback


def get(url, agent, tries=3):
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={
                'User-Agent': agent,
                'Accept-Language': 'ja,en;q=0.8',
            })
            with urllib.request.urlopen(request, timeout=40) as response:
                return response.read().decode('utf-8', 'replace')
        except Exception as error:
            if attempt == tries - 1:
                print(f'    取れません: {error}', file=sys.stderr)
                return ''
            time.sleep(6 * (attempt + 1))
    return ''


def rakuten_url(keyword, page):
    path = urllib.parse.quote(keyword, safe='')
    return f'https://search.rakuten.co.jp/search/mall/{path}/' + (f'?p={page}' if page > 1 else '')


def yahoo_url(keyword, page):
    params = {'p': keyword}
    if page > 1:
        params['b'] = (page - 1) * PER_PAGE['yahoo'] + 1
    return 'https://shopping.yahoo.co.jp/search?' + urllib.parse.urlencode(params)


def rakuten_items(html):
    """検索結果に出ている商品を、並んでいる順に返す。(店コード, 商品コード)。"""
    out, seen = [], set()
    for shop, code in re.findall(r'item\.rakuten\.co\.jp/([a-z0-9\-_]+)/([^/"\'\s?<>]+)/', html):
        key = (shop, code)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def yahoo_items(html):
    out, seen = [], set()
    for shop, code in re.findall(r'store\.shopping\.yahoo\.co\.jp/([a-z0-9\-_]+)/([^/"\'\s?<>]+)\.html', html):
        key = (shop, code)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


MALLS = {
    'rakuten': (rakuten_url, rakuten_items, '楽天市場'),
    'yahoo': (yahoo_url, yahoo_items, 'Yahoo!ショッピング'),
}


def find_rank(mall, keyword, shop, device, max_pages):
    """順位を返す。見つからなければ None（＝調べた範囲では圏外）。"""
    build_url, parse, _label = MALLS[mall]
    position = 0

    for page in range(1, max_pages + 1):
        html = get(build_url(keyword, page), DEVICES[device])
        time.sleep(PAUSE)

        items = parse(html)
        if not items:
            # 1ページ目で取れないのは、締め出されたか作りが変わったとき。
            # **0件と混同しない。** 見分けがつかないので None ではなく例外にする。
            if page == 1:
                raise RuntimeError(f'{mall} の検索結果を読めませんでした（{keyword} / {device}）')
            break

        for item_shop, item_code in items:
            position += 1
            if item_shop.lower() == shop.lower():
                return position, item_code

    return None, None


def main():
    config = load(CONFIG, None)
    if not config:
        print(f'{CONFIG} がありません。', file=sys.stderr)
        return 1

    devices = [d for d in (config.get('devices') or list(DEVICES)) if d in DEVICES]
    if not devices:
        print('devices が空です。pc / sp のどちらかを入れてください。', file=sys.stderr)
        return 1

    max_pages = int(os.environ.get('MAX_PAGES') or 2)
    only = int(os.environ.get('ONLY') or 0)
    today = date.today().isoformat()

    history = load(HISTORY, {'rows': []})
    rows = history.get('rows') or []

    jobs = []
    for site in config.get('sites', []):
        for keyword in site.get('keywords', []):
            for mall, shop in (site.get('shops') or {}).items():
                if mall not in MALLS:
                    print(f'知らないモール: {mall}', file=sys.stderr)
                    continue
                for device in devices:
                    jobs.append((site['name'], mall, shop, keyword, device))

    if only:
        jobs = jobs[:only]

    print(f'{len(jobs)}件を調べます（1件あたり最大{max_pages}ページ）。', file=sys.stderr)

    for name, mall, shop, keyword, device in jobs:
        try:
            rank, code = find_rank(mall, keyword, shop, device, max_pages)
        except RuntimeError as error:
            print(f'  {error}', file=sys.stderr)
            continue

        rows.append({
            'date': today, 'site': name, 'mall': mall, 'shop': shop,
            'keyword': keyword, 'device': device,
            'rank': rank, 'item': code,
            'checked': max_pages * PER_PAGE[mall],
        })

        label = f'{rank}位' if rank else f'{max_pages * PER_PAGE[mall]}位までに無し'
        print(f'  [{MALLS[mall][2]}/{device}] {keyword} → {label}', file=sys.stderr)

        HISTORY.write_text(json.dumps({'confirmedOn': today, 'rows': rows}, ensure_ascii=False),
                           encoding='utf-8')

    print(f'\n{len(rows):,}行になりました。', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
