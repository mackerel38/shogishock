# ShogiHome exports

`surprise export-shogihome` が生成するUTF-8の分岐付き `.kif` です。ShogiHome v1.29.0で「ファイルを開く」から読み込み、候補手の後に表示される本線・変化をクリックして盤面を確認します。

```bash
.venv/bin/surprise export-shogihome --input reports/pass_pilot --output exports/shogihome --limit 10
.venv/bin/surprise export-shogihome --input reports/pass_pilot \
  --candidate-id eb5bc2ef917ec96fe217_9g9f --output exports/shogihome
```

候補ごとに `.kif` と警告を記録した同名 `.json` を出力します。`[ShogiShock candidate]` コメントにcandidate ID、先後、評価値、pass指標、手数を埋め込みます。候補後の通常PVを本線にし、audit/obvious/confirmに存在する合法応手を変化として統合します。現在のpilotにそれらが存在しない場合も、PV本線だけでKIFを生成します。

KIF生成時にPVの不正手を検出した場合、該当枝を打ち切って他の枝を残し、`.json` とKIF末尾にwarningを記録します。研究候補や既存reportは上書きしません。

## Response-set calibration review

`.venv/bin/surprise response-set-review` は、既存の `reports/human_e2e` と
`exports/human_e2e` を変更せず、`exports/response_set_review/` の下へ
`actual_candidate`、`diagnostic_counterexample`、`control` 別にKIF/JSONをコピーします。
HTMLとmanifestは `reports/response_set_review/` に出力されます。分類は
`surprise/response_review.py` の明示的なレビュー指定に限り、モデルスコアから自動決定しません。
actual candidate が0件の場合も空のmanifest、HTML、export先ディレクトリを生成します。
