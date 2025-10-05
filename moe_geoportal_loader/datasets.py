DATASETS = {
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
    "tokunoshima_5th": {
        "name": "徳之島_第5回andR01Coralmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_union_tokunoshima_5thandR01Coralmap/FeatureServer",
        "has_prefecture": True,
    },
    "amami_4th": {
        "name": "奄美大島_第4回andR01Coralmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_union_amamiooshima_4thandR01Coralmap/FeatureServer",
        "has_prefecture": True,
    },
}
