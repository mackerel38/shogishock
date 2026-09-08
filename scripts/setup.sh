#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m venv .venv 2>/dev/null || true
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
mkdir -p engines/yaneuraou assets/eval
ln -sfn ../../assets/eval engines/yaneuraou/eval
if [[ ! -x engines/yaneuraou/yaneuraou ]]; then
  make -C third_party/yaneuraou/source -j"$(nproc)" tournament COMPILER=clang++ \
    YANEURAOU_EDITION=YANEURAOU_ENGINE_NNUE TARGET_CPU=SSE42 ENGINE_NAME=ShogiShock-YaneuraOu
  cp third_party/yaneuraou/source/YaneuraOu-by-gcc engines/yaneuraou/yaneuraou
fi
if [[ ! -f assets/eval/nn.bin ]]; then
  tmp="$(mktemp -d)"
  curl -L --fail -o "$tmp/Suisho5.7z" https://github.com/yaneurao/YaneuraOu/releases/download/suisho5/Suisho5.7z
  bsdtar -xf "$tmp/Suisho5.7z" -C assets/eval
  rm -rf "$tmp"
fi
chmod +x engines/yaneuraou/yaneuraou
python -m surprise.cli engine-test
echo '[OK] dependency setup'; echo '[OK] YaneuraOu'; echo '[OK] evaluation function'; echo '[OK] USI handshake'
