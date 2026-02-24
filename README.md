# MOE Geoportal Loader

[日本語](README.ja.md)

## Overview

- This plugin allows you to directly load datasets published on [MOE GeoPortal](https://geoportal.env.go.jp), a geospatial information portal operated by Japan's Ministry of the Environment, into QGIS.
- It targets datasets with the type "Feature Service" and licensed under CC BY 4.0.

## Features

- Load environmental datasets directly from MOE GeoPortal into QGIS.
- Automatic file and style saving when selecting a dataset and output destination.
- Optional loading as ArcGIS Feature Service layers.
- Integrated into the QGIS Processing Toolbox.

## Datasets

#### Vegetation Maps（11 datasets）

- Existing Vegetation Map（1:50,000）：by prefecture.
- Naturalness Classification Map（1:50,000）：by prefecture.
- Existing Vegetation Map 2024：Hokkaido, Tohoku, Kanto, Hokuriku, Chubu, Kinki, Chushikoku, Kyushu-Okinawa.
- Northern Territory Vegetation Overview Map.

#### Mammal Distribution Surveys（4 datasets）

- Medium/Large Mammal Distribution Survey：Badger, Fox, Raccoon Dog.
- National Bear Distribution Mesh（Basic Survey 1980）.

#### Coral Reef Ecosystem Surveys（19 datasets）

- Shallow Coral Ecosystem Survey：Tokara Islands（2021）, Kume Island（2018）, Tarama Island（2018）, Osumi Islands（2021）, Amami Islands（2018–2019）, Miyako Island（2018）, Ogasawara Islands（2020）, Sekisei Lagoon（2017）.
- 4th Coral Survey（1988–1993）：Coral Reef Distribution Area, Small-scale Ogasawara Coral Reef Area, Non-Coral Reef Distribution Area.
- 5th Coral Survey（1993–1999）：Distribution Area.

#### Coral Reef Change Detection（24 datasets）

- Amami-Oshima：H20 vs R01, 4th vs R01, 5th vs R01.
- Tokunoshima：H20 vs R01, 4th vs R01, 5th vs R01.
- Kume Island：H20 vs H30, 4th vs H30.
- Miyako Island：H20 vs H30, 4th vs H30.
- Ogasawara Islands：H20 vs H30, 4th vs R02, 5th vs R02.
- Okinoerabu Island：H20 vs H30, 4th vs H30.
- Tarama Island：H20 vs H30, 4th vs H30.
- Yoron Island：H20 vs H30, 4th vs H30.
- Takarajima & Kodakarajima：H20 vs R03, 4th vs R03.
- Tanegashima & Yakushima：H20 vs R03, 4th vs R03, 5th vs R03.

#### Seaweed Bed Surveys（7 datasets）

- 4th Seaweed Bed Survey（1988–1993）.
- 5th Seaweed Bed Survey（1993–1999）.
- Seaweed Bed Survey（2018–2020）：UTM Zone 51, 52, 53, 54, 55.

## Requirements

- QGIS 3.40 or later

## License

- This plugin is licensed under the [GNU General Public License v2.0](LICENSE).
- The datasets loaded by this plugin are provided by MOE GeoPortal under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Authors

- [Keita Uemori](@Geo-Jagaimo)
