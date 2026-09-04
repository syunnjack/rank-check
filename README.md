# rank-check（campsignal.jp）— モール横断の検索順位ウォッチ

**リポジトリ名は rank-check だが、公開先は campsignal.jp。**

自店の商品が、モールの検索で何番目に出るかを毎日記録する。

- 公開先: https://campsignal.jp
- 配信: GitHub Pages（`dist/CNAME` は `scripts/build_site.mjs` の `SITE_DOMAIN` から作る）
- **ドメインは `SITE_DOMAIN` 1箇所で決める。** 個別のファイルに書かない

## 何が他と違うのか

**APIの並び順ではなく、買い物客が見る検索結果ページの順位を数えている。**

楽天もYahooも商品検索APIを公開しているが、その並び順が買い物客の画面と
同じである保証はない。APIの順位を「検索順位」と呼ぶツールは、そこで嘘をつく。

このツールは検索結果ページそのものを読む。2026-09-04 の実測で、
手で数えた順位と一致することを確かめてある。

    楽天  「財布 メンズ」 kinoco → 3位（手で数えても3位）
    Yahoo 「財布 メンズ」 mura   → 5位（手で数えても5位）

## 対応しているモール

| モール | 順位 | 取り方 |
|---|---|---|
| 楽天市場 | ✅ | 検索結果ページ（1ページ45件） |
| Yahoo!ショッピング | ✅ | 検索結果ページ（1ページ30件） |
| Amazon | ❌ | 未対応。PA-API の鍵に「180日で3件の売上」が要る |
| Google | ⏸ | 検索順位の機械取得は規約違反。**Search Console API なら自社サイトの掲載順位を正規に取れる**ので、そちらで実装する |

**Google をスクレイピングしない。** 競合ツールにはやっているものもあるが、
規約違反でいつ止まってもおかしくない。自社ECサイトを持つ店には
Search Console API のほうが正確で、止まらない。

## PCとスマホ

User-Agent を変えると**別のページが返る**（実測でサイズも中身も違う）。
ただし**そのとき並び順は同じだった。**

「スマホでは順位が違う」は、いつも起きることではない。両方見るのは
差が出たときに気づくためで、**差が出るのが普通だと言ってはいけない。**
`config/watch.json` の `devices` で片方だけにもできる。

## 相手のサイトへの負荷

`robots.txt` を確かめてある（2026-09-04）。どちらもキーワード検索の
基本パスは `Disallow` に入っておらず、`Crawl-delay` の指定もない。

    search.rakuten.co.jp
    shopping.yahoo.co.jp

**それでも4秒あける。** 店主が自分で検索して順位を見る、その代わりを
する道具なので、人が手でやるより速く叩く理由がない。

## 設定

`config/watch.json`

```json
{
  "devices": ["pc", "sp"],
  "sites": [
    {
      "name": "自分の店",
      "shops": { "rakuten": "<楽天の店コード>", "yahoo": "<Yahooの seller id>" },
      "keywords": ["財布 メンズ", "長財布 本革"]
    }
  ]
}
```

店コードは商品URLに入っている。

    https://item.rakuten.co.jp/kinoco/wallet-04/          → kinoco
    https://store.shopping.yahoo.co.jp/mura/wallet-09.html → mura

## 使い方

```bash
python scripts/check_rank.py          # 既定は2ページ（楽天90位・Yahoo60位まで）
MAX_PAGES=4 python scripts/check_rank.py
ONLY=4 python scripts/check_rank.py   # 動作確認
```

結果は `data/history.json` に積み上がる。

## これから足すもの

- **AI可視性チェック** — ChatGPT や Claude に聞いたとき自店が出てくるか。
  `ANTHROPIC_API_KEY` が要る。1問あたり Opus 5 で10円前後、Haiku 4.5 で2円前後
- **Google Search Console** — 自社ECサイトの掲載順位
- 結果を見る静的サイト（いまは JSON のみ）

## やらないこと

- **レビューの自動生成。** 事業者が自作自演のレビューを作る道具になり、
  ステマ規制（景表法・2023年10月施行）に抵触する。
  レビューへの**返信の下書き**を作るのは別で、こちらは問題ない
- **Google 検索結果のスクレイピング。** 規約違反
- 「リアルタイム」を名乗ること。データ元の更新より速くはできない
