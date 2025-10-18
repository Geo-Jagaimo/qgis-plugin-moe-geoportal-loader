"""植生図データセット定義"""

VEGETATION_DATASETS = {
    "vg_50000": {
        "name": "現存植生図（1/50,000）- 都道府県別",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/vg_{pref_code}/FeatureServer",
        "has_prefecture": True,
    },
    "vgsk_50000": {
        "name": "自然度区分図（1/50,000）- 都道府県別",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/vgsk_{pref_code}/FeatureServer",
        "has_prefecture": True,
    },
    "veg2024bk1": {
        "name": "現存植生図2024 北海道ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk1/FeatureServer",
        "has_prefecture": False,
    },
    "veg2024bk2": {
        "name": "現存植生図2024 東北ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk2/FeatureServer",
        "has_prefecture": False,
    },
    "veg2024bk3": {
        "name": "現存植生図2024 関東ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk3/FeatureServer",
        "has_prefecture": False,
    },
    "veg2024bk4": {
        "name": "現存植生図2024 北陸ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk4/FeatureServer",
        "has_prefecture": False,
    },
    "veg2024bk5": {
        "name": "現存植生図2024 中部ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk5/FeatureServer",
        "has_prefecture": False,
    },
    "veg2024bk6": {
        "name": "現存植生図2024 近畿ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk6/FeatureServer",
        "has_prefecture": False,
    },
    "veg2024bk7": {
        "name": "現存植生図2024 中四国ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk7/FeatureServer",
        "has_prefecture": False,
    },
    "veg2024bk8": {
        "name": "現存植生図2024 九州沖縄ブロック",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/veg2024bk8/FeatureServer",
        "has_prefecture": False,
    },
    "NtVeg2024": {
        "name": "北方領土植生概況図",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/NtVeg2024/FeatureServer",
        "has_prefecture": False,
    },
}