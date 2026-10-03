DATASETS = {
    "vg_50000": {
        "name": "現存植生図（1/50,000）- 都道府県別",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg50000_{pref_code}{pref_name}/FeatureServer",
        "has_prefecture": True,
        "style": "veg50000style.qml",
    },
    "veg2024bk1": {
        "name": "現存植生図2024 北海道ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk1gdb/FeatureServer",
        "has_prefecture": False,
        "style": "veg2024style.qml",
    },
    "veg2024bk2": {
        "name": "現存植生図2024 東北ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk2gdb/FeatureServer",
        "has_prefecture": False,
        "style": "veg2024style.qml",
    },
    "veg2024bk3": {
        "name": "現存植生図2024 関東ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk3/FeatureServer",
        "has_prefecture": False,
        "style": "veg2024style.qml",
    },
    "veg2024bk4": {
        "name": "現存植生図2024 北陸ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk4/FeatureServer",
        "has_prefecture": False,
        "style": "veg2024style.qml",
    },
    "veg2024bk5": {
        "name": "現存植生図2024 中部ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk5/FeatureServer",
        "has_prefecture": False,
        "style": "veg2024style.qml",
    },
    "veg2024bk6": {
        "name": "現存植生図2024 近畿ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk6/FeatureServer",
        "has_prefecture": False,
        "style": "veg2024style.qml",
    },
    "veg2024bk7": {
        "name": "現存植生図2024 中四国ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk7gdb/FeatureServer",
        "has_prefecture": False,
        "style": "veg2024style.qml",
    },
    "veg2024bk8": {
        "name": "現存植生図2024 九州沖縄ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk8gdb/FeatureServer",
        "has_prefecture": False,
        "style": "veg2024style.qml",
    },
    "anaguma": {
        "name": "中大型哺乳類分布調査（アナグマ）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/anaguma/FeatureServer",
        "has_prefecture": False,
    },
    "kitune": {
        "name": "中大型哺乳類分布調査（キツネ）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/kitune/FeatureServer",
        "has_prefecture": False,
    },
    "tanuki": {
        "name": "中大型哺乳類分布調査（タヌキ）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/tanuki/FeatureServer",
        "has_prefecture": False,
    },
    "kiso2nd_bear5k": {
        "name": "基礎調査1980 クマ類全国分布メッシュ",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/kiso2nd_bear5k/FeatureServer",
        "has_prefecture": False,
    },
    "so4": {
        "name": "サンゴ第４回（1988-1993）小笠原の小規模サンゴ礁分布地域",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/so4/FeatureServer",
        "has_prefecture": False,
    },
    "sa4": {
        "name": "サンゴ第４回（1988-1993）非サンゴ礁地域の分布地域",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/sa4/FeatureServer",
        "has_prefecture": False,
    },
    "sb5": {
        "name": "サンゴ第５回（1993-1999）分布地域",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/sa5/FeatureServer",
        "has_prefecture": False,
    },
    "NtVeg2024": {
        "name": "北方領土植生概況図",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/NtVeg2024/FeatureServer",
        "has_prefecture": False,
    },
    "mo4_v2": {
        "name": "藻場調査第４回（1988-1993）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/mo4_v2/FeatureServer",
        "has_prefecture": False,
    },
    "mo5_v5": {
        "name": "藻場調査第５回（1993-1999）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/mo5_v5/FeatureServer",
        "has_prefecture": False,
    },
}
