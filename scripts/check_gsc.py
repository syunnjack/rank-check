"""Search Console から、自分のサイトの掲載順位を取る。

**Google の検索結果はスクレイピングしない。** 規約違反で、いつ止まってもおかしくない。
Search Console API は Google が公式に出している道具で、しかも正確。

## モールの順位とは別のものだと分かるように持つ

    モール   いま検索したときの、その1件の順位
    GSC     過去数日の**平均掲載順位**。しかも2〜3日遅れる

同じ「3位」でも意味が違う。混ぜないよう、記録の kind を 'gsc' に分けて、
平均であることと、いつまでのデータかを一緒に持つ。

## 使い方

    python scripts/check_gsc.py

環境変数:
  GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN
  GSC_DAYS   何日ぶんをならすか（既定 7）

refresh token の取り方は docs/google-search-console.md。
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / 'config' / 'watch.json'
HISTORY = ROOT / 'data' / 'history.json'

TOKEN = 'https://oauth2.googleapis.com/token'
BASE = 'https://searchconsole.googleapis.com/webmasters/v3'

# Search Console のデータは2〜3日遅れる。今日を含めても空が返るだけ。
LAG_DAYS = 3


def load(path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return fallback


def access_token(client_id, client_secret, refresh_token):
    body = urllib.parse.urlencode({
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    }).encode()

    request = urllib.request.Request(TOKEN, data=body, method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))['access_token']


def query(token, site_url, payload):
    url = f'{BASE}/sites/{urllib.parse.quote(site_url, safe="")}/searchAnalytics/query'
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method='POST', headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        detail = error.read().decode('utf-8', 'replace')[:200]
        print(f'    {error.code}: {detail}', file=sys.stderr)
        return {}


def main():
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
    refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN', '').strip()

    if not (client_id and client_secret and refresh_token):
        print('GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN が要ります。',
              file=sys.stderr)
        print('取り方は docs/google-search-console.md を見てください。', file=sys.stderr)
        return 1

    config = load(CONFIG, None)
    if not config:
        print(f'{CONFIG} がありません。', file=sys.stderr)
        return 1

    targets = [site for site in config.get('sites', []) if site.get('gsc')]
    if not targets:
        print('config に gsc のプロパティが書かれていません。'
              '（自社ECサイトが無い店では使えません）', file=sys.stderr)
        return 0

    days = int(os.environ.get('GSC_DAYS') or 7)
    end = date.today() - timedelta(days=LAG_DAYS)
    start = end - timedelta(days=days - 1)

    try:
        token = access_token(client_id, client_secret, refresh_token)
    except Exception as error:
        print(f'アクセストークンを取れません: {error}', file=sys.stderr)
        return 1

    history = load(HISTORY, {'rows': []})
    rows = history.get('rows') or []
    today = date.today().isoformat()

    for site in targets:
        site_url = site['gsc']
        keywords = site.get('keywords') or []
        print(f'{site["name"]}（{site_url}）{start} 〜 {end}', file=sys.stderr)

        payload = {
            'startDate': start.isoformat(),
            'endDate': end.isoformat(),
            'dimensions': ['query'],
            # **1回で取り切れる上限まで取ってから、手元で引き当てる。**
            # 1キーワードずつ絞って何度も叩くより、APIへの負荷が軽い。
            # 25,000件に収まらないほど大きなサイトなら、ここは分けて取る必要がある。
            'rowLimit': 25000,
        }
        result = query(token, site_url, payload)
        found = {r['keys'][0]: r for r in (result.get('rows') or [])}

        for keyword in keywords:
            row = found.get(keyword)
            rows.append({
                'date': today, 'site': site['name'], 'kind': 'gsc',
                'mall': 'google', 'shop': site_url,
                'keyword': keyword, 'device': 'all',
                # **平均掲載順位。** モールの順位と同じ数字ではない。
                'rank': round(row['position'], 1) if row else None,
                'impressions': row['impressions'] if row else 0,
                'clicks': row['clicks'] if row else 0,
                'period': f'{start}〜{end}',
                'checked': None,
            })

            if row:
                print(f'  {keyword} → 平均 {row["position"]:.1f}位 '
                      f'/ 表示 {row["impressions"]:,} / クリック {row["clicks"]:,}', file=sys.stderr)
            else:
                print(f'  {keyword} → この期間に表示されていません', file=sys.stderr)

    HISTORY.write_text(json.dumps({'confirmedOn': today, 'rows': rows}, ensure_ascii=False),
                       encoding='utf-8')
    print(f'\n{len(rows):,}行になりました。', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
