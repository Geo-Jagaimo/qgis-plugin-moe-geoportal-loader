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
    "tokara_21_code1": {
        "name": "サンゴ浅海生態系現況把握調査（トカラ列島周辺2021, CODE1）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/tokara_2021_code1/FeatureServer",
        "has_prefecture": False,
    },
    "tokara_21_code2": {
        "name": "サンゴ浅海生態系現況把握調査（トカラ列島周辺2021, CODE2）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/tokara_2021_code2/FeatureServer",
        "has_prefecture": False,
    },
    "kume_18_code1": {
        "name": "サンゴ浅海生態系現況把握調査（久米島2018, CODE1）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/kume_code1/FeatureServer",
        "has_prefecture": False,
    },
    "kume_18_code2": {
        "name": "サンゴ浅海生態系現況把握調査（久米島2018, CODE2）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/kume_code2/FeatureServer",
        "has_prefecture": False,
    },
    "tarama_18_code1": {
        "name": "サンゴ浅海生態系現況把握調査（多良間島2018, CODE1）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/tarama_code1/FeatureServer",
        "has_prefecture": False,
    },
    "tarama_18_code2": {
        "name": "サンゴ浅海生態系現況把握調査（多良間島2018, CODE2）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/tarama_code2/FeatureServer",
        "has_prefecture": False,
    },
    "osumi_18_code1": {
        "name": "サンゴ浅海生態系現況把握調査（大隅諸島周辺2021, CODE1）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/oosumi_2021_code1/FeatureServer",
        "has_prefecture": False,
    },
    "osumi_18_code2": {
        "name": "サンゴ浅海生態系現況把握調査（大隅諸島周辺2021, CODE2）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/oosumi_2021_code2/FeatureServer",
        "has_prefecture": False,
    },
    "amami_1819_code1": {
        "name": "サンゴ浅海生態系現況把握調査（奄美群島2018-2019, CODE1）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/amami_all_code1/FeatureServer",
        "has_prefecture": False,
    },
    "amami_1819_code2": {
        "name": "サンゴ浅海生態系現況把握調査（奄美群島2018-2019, CODE2）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/amami_all_code2/FeatureServer",
        "has_prefecture": False,
    },
    "miyako_18_code1": {
        "name": "サンゴ浅海生態系現況把握調査（宮古島2018, CODE1）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/miyako_code1/FeatureServer",
        "has_prefecture": False,
    },
    "miyako_18_code2": {
        "name": "サンゴ浅海生態系現況把握調査（宮古島2018, CODE2）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/miyako_code2/FeatureServer",
        "has_prefecture": False,
    },
    "ogasawara_20_code1": {
        "name": "サンゴ浅海生態系現況把握調査（小笠原周辺2020, CODE1）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/ogasawara_v3_code1/FeatureServer",
        "has_prefecture": False,
    },
    "ogasawara_20_code2": {
        "name": "サンゴ浅海生態系現況把握調査（小笠原周辺2020, CODE2）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/ogasawara_v3_code2/FeatureServer",
        "has_prefecture": False,
    },
    "sekisei_17": {
        "name": "サンゴ浅海生態系現況把握調査（石西礁湖2017）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/sekiseishoko_2017/FeatureServer",
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
