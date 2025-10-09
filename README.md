# MOE Geoportal Loader

## 概要

- 環境省が運営する地理空間情報ポータルサイト「[環境ジオポータル](https://geoportal.env.go.jp)」で公開されているデータのうち、タイプが「Feature Service」で、ライセンスが「CC BY 4.0」のものを QGIS に直接読み込めるプラグインです（＊各ブロックの現存植生図 2024 を除く）。

## インストール

- [Releases](https://github.com/Geo-Jagaimo/qgis-plugin-moe-geoportal-loader/releases) ページから最新の「moe-geoportal-loader」パッケージをダウンロードします。
- QGIS の［プラグインの管理とインストール...］で［ZIP からインストール］を選択し、ダウンロードした ZIP ファイルを解凍せずにそのまま指定してインストールしてください。

<img src='./imgs/install_from_zip.png' alt="ZIPからインストール" width="70%">

## 使用方法

- 環境省が提供する地理空間情報ポータルサイト「環境ジオポータル」のデータを QGIS に直接読み込むためのプラグインです。
- データセットを選択すると、ArcGIS Feature Service レイヤとしてスタイル付きで読み込まれ、必要に応じてファイル保存も同時に行えます。

<img src='./imgs/usage.png' alt="ZIPからインストール" width="70%">

## Authors

- [Keita Uemori](@Geo-Jagaimo)
