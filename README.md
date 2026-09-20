# Circa40 Plus — ZMK config

Circa40 Plus専用のZMK設定です。KiCadデータは変更していません。

## 構成

- XIAO nRF52840 **Plus** × 2。ZMKのビルドターゲットは `xiao_ble//zmk`。
- 左24キー（子機）、右23キー（親機）、合計47キー。SW47 / SW48は電源スイッチなのでキーに含めません。
- 左右間はBluetooth接続。PCには**右側**をUSBまたはBluetoothで接続します。
- 右側PAW3222、760 CPI。センサーを置くための空間に架空のキーは作成していません。
- 後からPCBに追加された実在のSW49（1.5u）はキーとして含めています。
- 17mmピッチ・実際のPCB上の並び順に対応。電気的には左右とも4行×6列です。
- 標準ZMK構成です。DYA Studio / ZMK Studio対応は今回含めていません。

## 現在の検証状況

GPIO、ダイオード方向、47キーの行列と順序を元PCB・回路図のMCU接続に照合しています。
**コンパイル・UF2生成・実機動作確認は未実施**です。ビルド環境は含みません。
GitHub Actionsを実行してから書き込んでください。GitHubへのアップロードは行っていません。
センサーの軸方向はケース内の取り付け方向に依存するため、実機で確認・調整してください。

## ビルドと書き込み

1. このディレクトリの内容をGitHubのリポジトリ直下に配置します（親ディレクトリで包まない）。
2. Actionsの `Build Circa40 Plus` を実行します。
3. 成功後、Artifactsの `firmware` をダウンロードします。
4. XIAOのリセットを素早く2回押してUF2ドライブを表示します。
5. 左に `Circa40plus-left.uf2`、右に `Circa40plus-right.uf2` をコピーします。

左右を同じ設定バージョンで書き込んでください。
左右ペアリングが不調な場合のみ、`Circa40plus-settings-reset.uf2` を**左右両方**に書き込み、
その後それぞれの通常ファームウェアを書き直します。設定リセットはペアリング情報等を消去します。
PC側の古い登録も削除して、右側の `Circa40 Plus` を再登録します。

既存のLinux / WSL / Docker等のZMKビルド環境では、このリポジトリ直下で次を実行します。

```sh
west init -l config
west update
west zephyr-export
west build -s zmk/app -d build/left -b xiao_ble//zmk -- -DZMK_CONFIG="$PWD/config" -DSHIELD=circa40plus_left
west build -s zmk/app -d build/right -b xiao_ble//zmk -- -DZMK_CONFIG="$PWD/config" -DSHIELD=circa40plus_right
```

## 初期キーマップ

提示されたKLEを基本にしています。空欄・Meta等の用途未指定箇所は次の仮割り当てです。
`config/circa40plus.keymap` で変更できます。OSの配列はUS配列を想定しています。

```text
Tab Q W E R T Esc       Y U I O P Del
Ctrl A S D F G          Tab H J K L Enter
Shift Z X C V B         B N M , . Fn
GUI Alt Space RAlt Sys  Space Enter Backspace Click-L Click-R
```

- SW45 = Esc、SW46 = Tab、SW44 = Sys、SW49 = Space。
- 左親指のSW18 = GUI、SW19 = Alt、SW20 = Space、SW21 = RAlt。
- 右親指のSW41 / SW42 = マウス左 / 右クリック。
- Fn（SW38）を押している間：数字・記号・F1〜F12・矢印・ページ移動。
- Sys（SW44）を押している間：Q/W/E/R/TでBluetoothスロット0〜4、YでUSB出力、UでBluetooth出力。
- **Sys + Delは選択中Bluetoothスロットの登録解除**です。
- Sys + N/M/,/. は前曲/再生停止/次曲/ミュート、Sys + 右親指のクリック2キーは音量下/上。
- Sys + SW49 はマウス中クリック。
- ディープスリープは15分。復帰はまずキーを押してください。

## 配線（nRF GPIO番号）

| 信号 | 左 `Left-XiaoPlus1` | 右 `U1` |
|---|---|---|
| Col0 | P0.02 | P0.02 |
| Col1 | P0.03 | P0.03 |
| Col2 | P0.28 | P0.28 |
| Col3 | P0.29 | P0.29 |
| Col4 | P0.15 | P0.04 |
| Col5 | P0.19 | P0.05 |
| Row0 | P1.01 | P1.11 |
| Row1 | P1.07 | P1.12 |
| Row2 | P1.05 | P1.13 |
| Row3 | P1.03 | P1.14 |

ダイオードは列→スイッチ→A→K→行なので `col2row` です。
通常版XIAOの端子だけでは左側配線を接続できません。Plusの追加端子を使用します。

右FFC J1は1:GND、2:MOTION(P1.15)、3:SDIO(P1.07)、4:CS(P1.05)、5:SCLK(P1.03)、6:3.3Vです。
PAW3222側J2と1対1で接続してください。5Vは接続しないでください。
SDIOはドライバ作者の設定例に従いMOSI/MISOを同じP1.07に割り当てています。
電源制御GPIOは実配線に存在しないため設定していません。

物理的な各行で左から右へ並べたSW番号（キーマップの順序）:

```text
1 2 3 4 5 6 45       | 22 23 24 25 26 27
7 8 9 10 11 12      | 46 28 29 30 31 32
13 14 15 16 17 43   | 33 34 35 36 37 38
18 19 20 21 44      | 49 39 40 41 42
```

SW45は上段にありますが電気的には左Row3/Col5です。
SW46は右Row1/Col5、SW49は右Row3/Col4で、見た目から行列を推定すると誤ります。

## 検証スクリプト

設定単独の検証（Python標準ライブラリのみ）:

```sh
python scripts/validate.py
```

元PCBまで含める場合、KiCad付属Pythonで実行します（読み取りのみ）:

```powershell
& 'C:\Program Files\KiCad\10.0\bin\python.exe' scripts/validate.py --pcb 'D:\OneDrive - スタッフマーケティング株式会社\KiCad\AroundForty\V3\Circa40_Plus\Circa40_Plus.kicad_pcb' --netlist "$env:TEMP\circa40plus-firmware.xml"
```

XMLは `kicad-cli sch export netlist --format kicadxml` によるトップ回路図の出力です。
PCBのGPIO・ダイオード・全キーマップ位置を確認し、XML指定時は回路図のMCU接続も照合します。
この検証はビルドや実機テストの代わりにはなりません。

## 参照・固定バージョン

- [ZMK](https://github.com/zmkfirmware/zmk)：`9ebbeff0a8b69a42f14aec022cdf16c7a107b9e0`
- [PAW3222ドライバ](https://github.com/sekigon-gonnoc/zmk-driver-paw3222)：`df652881be2520bde4f64ab6ca35e4c5708f4f9b`
- [ZMKのポインティングデバイス設定](https://zmk.dev/docs/hardware-integration/pointing)

元PCBのSHA-256（作成時）:
`CA10D04B0719323029F035691D8F4EBE18BF031D9C243115CC9CE4F19E290FEC`
