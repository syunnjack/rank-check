# Google を順位に入れる方法

**Google の検索結果をスクレイピングしない。** 規約違反で、いつ止まってもおかしくない。
代わりに Search Console API を使う。こちらは Google が公式に出している。

エンドポイントは実在を確かめてある（2026-09-04・いずれも 401 で OAuth 2 を要求）。

    GET  webmasters/v3/sites                             持っているサイトの一覧
    POST webmasters/v3/sites/{siteUrl}/searchAnalytics/query   掲載順位・表示・クリック
    POST v1/urlInspection/index:inspect                  そのURLが登録されているか

スコープは `https://www.googleapis.com/auth/webmasters.readonly`。

---

## 先に決めること：モールの順位と**同じものではない**

これを混ぜると、読む人を必ず誤解させる。

| | モール（楽天・Yahoo） | Google Search Console |
|---|---|---|
| 何の数字か | **いま検索したときの、その1件の順位** | **過去数日の平均掲載順位** |
| いつの話か | 調べた瞬間 | **2〜3日遅れる** |
| 誰の目線か | 誰が検索しても同じ | 実際に表示された人たちの平均 |
| 3位の意味 | 3番目に並んでいた | ある人には1位、ある人には5位で、ならすと3 |

**同じ表に「3位」と並べて置いてはいけない。** 列を分け、GSC 側には
「平均掲載順位・◯月◯日まで」と必ず添える。

Search Console は**自社ECサイトを持っている店だけ**が使える。
楽天市場店・Yahoo店しか無い店には、そもそもプロパティが無い。

---

## 誰のサイトを見るかで、作りが3通りに分かれる

### A. 自分のサイトだけ見る（いますぐ作れる）

Google Cloud にプロジェクトを1つ作り、OAuth クライアント（デスクトップ）を発行して、
**一度だけブラウザで同意する**。返ってくる refresh token を GitHub Secrets に入れれば、
あとは Actions から毎日叩ける。

- **審査は要らない**（自分がプロパティの所有者だから）
- サーバーも要らない。いまの作り（静的サイト＋Actions）のまま
- 必要な秘密は3つ: `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REFRESH_TOKEN`

`scripts/authorize_gsc.py` で同意し、`scripts/check_gsc.py` で毎日取る。

### B. 他人には CSV を読ませる（無料ツールとして配るなら、これ）

店主が Search Console の画面から検索パフォーマンスを CSV で書き出し、
ツールに読み込ませる。

- **OAuth も審査もサーバーも要らない**
- **他人の認証情報を預からない。** 預からなければ漏らしようがない
- 手間は増えるが、無料ツールの入口としてはこれで足りる

集客用の無料ツールなら、**まず B を出すのが正しい。**
「Googleに繋いでください」と言われて鍵を渡す店主より、
CSVを1枚上げる店主のほうがずっと多い。

### C. 他人の Search Console に OAuth で繋ぐ（本格的にやるなら）

これは別事業になる。軽く考えると事故る。

- **Google の審査が要る。** webmasters スコープは機微情報あつかいで、
  審査を通さないと利用者100人までのテスト状態から出られない
- **他人の refresh token を預かって保管することになる。**
  暗号化・漏洩時の責任・削除依頼への対応が必要
- 静的サイト＋Actions では作れない。サーバーとデータベースが要る
- プライバシーポリシーと利用規約が必須

**やるなら、事業として本気でやると決めてから。** A と B を出して
使われることが分かってからで遅くない。

---

## 進め方

1. **A を作る**（自分のサイトで動かして、値の意味を確かめる）
2. **B を足す**（他人向けの入口。CSVの列名を実物で確認してから）
3. C は、使われ方を見てから判断する

---

## A の手順

### 1. Google Cloud でプロジェクトと OAuth クライアントを作る

1. https://console.cloud.google.com でプロジェクトを作る
2. 「APIとサービス」→ ライブラリ → **Google Search Console API** を有効にする
3. 「OAuth 同意画面」を作る（外部・テストのままでよい。自分だけなので）
4. 「認証情報」→ OAuth クライアント ID →**デスクトップアプリ**
5. クライアントIDとシークレットを控える

### 2. 一度だけ同意する

```bash
GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... python scripts/authorize_gsc.py
```

表示されたURLをブラウザで開いて許可すると、コードが出る。
それを貼ると refresh token が表示される。

### 3. GitHub Secrets に入れる

```bash
gh secret set GOOGLE_CLIENT_ID
gh secret set GOOGLE_CLIENT_SECRET
gh secret set GOOGLE_REFRESH_TOKEN
```

**refresh token はリポジトリに書かない。**

### 4. 毎日取る

```bash
python scripts/check_gsc.py
```

`config/watch.json` の `gsc` に見るプロパティを書く。
