# 人間棋譜source・利用条件確認

確認日: 2026-09-08。以下は研究上の利用判断であり、包括的な法的保証ではない。

## 採用: Lishogi公式API — ローカル小規模研究のみ

[公式利用規約](https://lishogi.org/terms-of-service) は教育・開発用途を支持する一方、利用者投稿の権利が利用者に残る旨を定める。
今回確認した規約から、棋譜データ全体のCC0や第三者の無制限再配布許諾は確認できなかった。
ソフトウェアのAGPLと棋譜データの利用許諾は別物として扱う。

[公式API](https://lishogi.org/api) と [公式リポジトリのAPI仕様](https://raw.githubusercontent.com/WandererXII/lishogi/master/ui/@build/static/assets/doc/lishogi-api.yaml)
に公開ユーザー対局exportがある。教育・開発目的の公開API利用として、少量のローカル解析を行う判断とした。
サービスへの負荷を避け、2リクエストを逐次実行、各最大25件、HTTPエラー時停止、取得済みデータは再取得しない。
これを棋譜再配布の許諾とは解釈しない。`redistribution_approved=false` を保存した。

選定アカウントは公開の [棋譜取得に関する公式フォーラム](https://lishogi.org/forum/lishogi-feedback/feature-request-batch-download-of-kifu)
で確認した pona / Toadofsky。各アカウントの直近最大25件という便宜標本であり、無作為抽出でも人口代表標本でもない。
実取得21+25=46件。宣言BOT/AI23件、双方の識別情報不足3件、未完了・着手なし1件を除外し19件を受理。
BOT title / aiLevelを検査するが、未申告の支援利用まで判定できない。ラベルは `no_declared_bot_or_ai`。

ローカルrawにはrequest URL、取得UTC日時、レスポンスSHA256、規約/API URL、source、game ID、moves、rating、clock、BOT/AI情報を保存。
DBには採否と除外理由も保持。公開リポジトリへのraw/DBアップロードは行っていない。
本格取得・再配布に進む際は、Lishogi側の明示的許諾または適用可能なデータライセンスを追加確認する。

## 保留: 81Dojo

[公式規約](https://81dojo.com/en/terms.html) は公式アプリ以外のサーバーアクセスを禁止しているため、クローラー/API代用の自動取得先には採用しない。
棋譜共有には別条件があり、商用利用には相談を求めている。将来使う場合は管理者との調整、または権限ある提供者の適法なexportを検討する。
今回は取得していない。

## 保留: ShogiDB2

[サイト](https://shogidb2.com/) には人間棋譜だけでなくコンピュータ対局もあるため、そのまま人間データと扱えない。
今回、大量取得・再利用を明示的に認める条件を確認できず、取得していない。

Lichessの公開DBライセンスをLishogiへ転用して解釈しない。名称が似ていても別サービス・別データである。
