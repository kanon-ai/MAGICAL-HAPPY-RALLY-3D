# ビルド / Building

## 日本語

Python 3、SDCC、Pasmoが必要です。対応ツールをPATHに置くか、SDCC/PASMO環境変数で実行ファイルを指定します。ビルドにはBIOSもエミュレーターも不要です。

```powershell
$env:SDCC = "C:/tools/sdcc/bin/sdcc.exe"
$env:PASMO = "C:/tools/pasmo/pasmo.exe"
python tools/build.py --pack-only
```

出力は `outputs/MAGICAL_HAPPY_RALLY_3D.rom`。`rom/` の配布済みROMは上書きしません。ランチャーの `--rom outputs/MAGICAL_HAPPY_RALLY_3D.rom` で生成版を指定できます。

この公開版はC/アセンブリのソースと、再ビルドに必要な生成済み画像・コースデータを含みます。原画や試行中の素材生成・撮影ツール一式は含みません。生成済み素材は別ライセンスです。異なるコンパイラー版では配置・コードサイズが変わり、ビルド時の領域検査に失敗する場合があります。

## English

Install Python 3, SDCC and Pasmo. Put them on PATH or set SDCC and PASMO to the executable paths, then run `python tools/build.py --pack-only` (the PowerShell example above applies). No BIOS or emulator is needed to build.

Output: `outputs/MAGICAL_HAPPY_RALLY_3D.rom`; the distributed ROM in `rom/` is preserved. Pass `--rom outputs/MAGICAL_HAPPY_RALLY_3D.rom` to the launcher to run your build.

This release includes C/assembly sources and the pre-generated graphics/course data required to rebuild. Original artwork and the experimental asset-generation/capture tool collection are not included. Generated assets retain their separate terms. Compiler versions can change code size/layout and trigger the build's memory-range checks.

検証ツール / Verified compiler: SDCC 4.6.0 #16555 (MINGW64).
Verified ROM SHA-256: `3ef176403cb7ad752196dca81f877b99ffddaefd508315676bddcd159c345ea6`.
