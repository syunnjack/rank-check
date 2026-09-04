"""Search Console を読む許可を一度だけもらい、refresh token を出す。

**これは1回だけ動かす道具。** 出てきた refresh token を GitHub Secrets に入れれば、
あとは check_gsc.py が毎日それを使って動く。

    GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... python scripts/authorize_gsc.py

デスクトップアプリのクライアントを使う前提。手順は
docs/google-search-console.md に書いてある。

**refresh token は画面に出るだけで、どこにも保存しない。**
うっかりリポジトリに入らないようにするため。
"""
import json
import os
import sys
import urllib.parse
import urllib.request

AUTH = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN = 'https://oauth2.googleapis.com/token'
SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly'
# デスクトップアプリで、ブラウザに出たコードを手で貼るときの決まり文句。
REDIRECT = 'urn:ietf:wg:oauth:2.0:oob'


def main():
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()

    if not client_id or not client_secret:
        print('GOOGLE_CLIENT_ID と GOOGLE_CLIENT_SECRET が要ります。', file=sys.stderr)
        print('作り方は docs/google-search-console.md を見てください。', file=sys.stderr)
        return 1

    url = AUTH + '?' + urllib.parse.urlencode({
        'client_id': client_id,
        'redirect_uri': REDIRECT,
        'response_type': 'code',
        'scope': SCOPE,
        # refresh token は「初めての同意」のときしか返らない。
        # 取り直したいときのために毎回聞き直す。
        'access_type': 'offline',
        'prompt': 'consent',
    })

    print('このURLをブラウザで開いて、許可してください。\n')
    print(f'  {url}\n')
    code = input('出てきたコードを貼ってください: ').strip()

    if not code:
        print('コードが空です。', file=sys.stderr)
        return 1

    body = urllib.parse.urlencode({
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': REDIRECT,
        'grant_type': 'authorization_code',
    }).encode()

    try:
        request = urllib.request.Request(TOKEN, data=body, method='POST')
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception as error:
        detail = ''
        if hasattr(error, 'read'):
            detail = error.read().decode('utf-8', 'replace')[:300]
        print(f'交換できませんでした: {error} {detail}', file=sys.stderr)
        return 1

    token = payload.get('refresh_token')
    if not token:
        print('refresh token が返りませんでした。', file=sys.stderr)
        print('すでに同意済みのことがあります。Googleアカウントの'
              '「サードパーティ製アプリ」から一度解除して、やり直してください。', file=sys.stderr)
        return 1

    print('\n取れました。次の値を GitHub Secrets に入れてください。\n')
    print(f'  GOOGLE_REFRESH_TOKEN = {token}\n')
    print('  gh secret set GOOGLE_REFRESH_TOKEN')
    print('\n**この値はリポジトリに書かないでください。**')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
