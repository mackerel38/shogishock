# ShogiHome確認導線

この環境ではShogiHome本体は未導入です。`command -v shogihome ShogiHome tsshogi` による確認で実行可能な既存コマンドはありませんでした。

確認対象は公式のLinux配布物を使います。2026-09-09に公式GitHub Releases APIで確認した最新リリースは `v1.29.0` で、Linux AppImageとLinux deb zipが公開されています。

- 公式リポジトリ: https://github.com/sunfish-shogi/shogihome
- 公式リリース: https://github.com/sunfish-shogi/shogihome/releases/tag/v1.29.0
- 推奨取得物: `release-v1.29.0-linux-appimage.zip`
- 導入方法: AppImageを `tools/shogihome/` などプロジェクト内へ展開し、システムパッケージとしてインストールしない
- 確認対象バージョン: ShogiHome v1.29.0

## この環境への導入

公式Linux AppImageをプロジェクト内へ展開済みです。

```bash
scripts/shogihome.sh
```

または、直接 `tools/shogihome/ShogiHome-1.29.0.AppImage` を実行できます。AppImageの `--appimage-version` は `Version: effcebc` を返しました。システム全体へのdebインストールは行っていません。

KIFはUTF-8で出力し、公式ShogiHomeで開くための手順を `exports/README.md` に記載しています。sandboxには表示サーバーがないため、実際の画面操作を伴うvisual QAは未実施です。

## 2026-09-09 研究再開後

`exports/human_e2e/` に先後各3件の研究用分岐KIFを追加。Human Policy確率・P_good・human_gap・応手評価をコメントに保存。
主PV末尾の手数を分岐開始手数に誤使用していたexporterのバグを修正した。旧生成済みKIFは上書きしていないため、
旧ファイルで分岐が合わない場合は修正版exporterで別出力先へ再生成する。
新KIFは全分岐の手数と合法性を再パース検証済み。ただしGUIの見た目はユーザー確認が必要。
