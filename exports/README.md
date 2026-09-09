# ShogiHome exports

`surprise export-shogihome` が生成するUTF-8の分岐付き `.kif` です。ShogiHome v1.29.0で「ファイルを開く」から読み込み、候補手の後に表示される本線・変化をクリックして盤面を確認します。

```bash
.venv/bin/surprise export-shogihome --input reports/pass_pilot --output exports/shogihome --limit 10
.venv/bin/surprise export-shogihome --input reports/pass_pilot \
  --candidate-id eb5bc2ef917ec96fe217_9g9f --output exports/shogihome
```

候補ごとに `.kif` と警告を記録した同名 `.json` を出力します。`[ShogiShock candidate]` コメントにcandidate ID、先後、評価値、pass指標、手数を埋め込みます。候補後の通常PVを本線にし、audit/obvious/confirmに存在する合法応手を変化として統合します。現在のpilotにそれらが存在しない場合も、PV本線だけでKIFを生成します。

KIF生成時にPVの不正手を検出した場合、該当枝を打ち切って他の枝を残し、`.json` とKIF末尾にwarningを記録します。研究候補や既存reportは上書きしません。
