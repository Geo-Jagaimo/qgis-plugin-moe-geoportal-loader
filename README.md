# MOE Geoportal Loader

## 概要

- 環境省が運営する地理空間情報ポータルサイト「[環境ジオポータル](https://geoportal.env.go.jp)」で公開されているデータのうち、タイプが「Feature Service」で、ライセンスが「CC BY 4.0」のものを QGIS に直接読み込めるプラグインです。

## インストール

- [Releases](https://github.com/Geo-Jagaimo/qgis-plugin-moe-geoportal-loader/releases) ページから最新の「moe-geoportal-loader」パッケージをダウンロードします。
- QGIS の［プラグインの管理とインストール...］で［ZIP からインストール］を選択し、ダウンロードした ZIP ファイルを解凍せずにそのまま指定してインストールしてください。

<img src='./imgs/install_from_zip.png' alt="ZIPからインストール" width="70%">

## 使用方法

- 環境省が提供する地理空間情報ポータルサイト「環境ジオポータル」のデータを QGIS に直接読み込むためのプラグインです。
- データセットと出力先を選択すると、ファイルとスタイル設定が自動的に保存されます。
- 必要に応じて、ArcGIS Feature Service レイヤとして読み込むことができます。
- 「現存植生図 2024」は非常に大きなデータセットです。利用の際は、処理負荷や動作環境にご注意ください。

<img src='./imgs/usage.png' alt="ZIPからインストール" width="70%">

## Authors

- [Keita Uemori](@Geo-Jagaimo)
