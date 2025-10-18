"""サンゴ礁調査データセット定義"""

CORAL_DATASETS = {
    # サンゴ浅海生態系現況把握調査
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
    "sekiseishoko_17": {
        "name": "サンゴ浅海生態系現況把握調査（石西礁湖2017）",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/sekiseishoko_2017/FeatureServer",
        "has_prefecture": False,
    },
    # サンゴ礁調査（第4回・第5回）
    "sb4_v2": {
        "name": "サンゴ第４回（1988-1993）サンゴ礁地域分布地域",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/sb4_v2/FeatureServer",
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
    # 変化 union データ
    "amamiooshima_H20andR01Coralmap": {
        "name": "変化 union 奄美大島 H20andR01Coralmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_union_amamiooshima_H20andR01Coralmap/FeatureServer",
        "has_prefecture": False,
    },
    "amamiooshima_4thandR01Coralmap": {
        "name": "変化 union 奄美大島 第4回andR01Coralmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_union_amamiooshima_4thandR01Coralmap/FeatureServer",
        "has_prefecture": False,
    },
    "amamiooshima_5thandR01Coralmap": {
        "name": "変化 union 奄美大島 第5回andR01Coralmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_union_amamiooshima_5thandR01Coralmap/FeatureServer",
        "has_prefecture": False,
    },
    "tokunoshima_H20andR01Coralmap": {
        "name": "変化 union 徳之島 H20andR01Coralmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_union_tokunoshima_H20andR01Coralmap/FeatureServer",
        "has_prefecture": False,
    },
    "tokunoshima_4thandR01Coralmap": {
        "name": "変化 union 徳之島 第4回andR01Coralmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_union_tokunoshima_4thandR01Coralmap/FeatureServer",
        "has_prefecture": False,
    },
    "tokunoshima_5thandR01Coralmap": {
        "name": "変化 union 徳之島 第5回andR01Coralmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_union_tokunoshima_5thandR01Coralmap/FeatureServer",
        "has_prefecture": False,
    },
    # 変化域データ
    "kume_H20vsH30corlalmap": {
        "name": "変化域 kume H20vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_kume_H20vsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "kume_4thvsH30corlalmap": {
        "name": "変化域 kume 第4回vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_kume_4thvsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "miyako_H20vsH30corlalmap": {
        "name": "変化域 miyako H20vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_miyako_H20vsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "miyako_4thvsH30corlalmap": {
        "name": "変化域 miyako 第4回vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_miyako_4thvsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "ogasawara_H20vsH30corlalmap": {
        "name": "変化域 ogasawara H20vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_ogasawara_H20vsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "ogasawara_4thvsR02corlalmap": {
        "name": "変化域 ogasawara 第4回vsR02corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_ogasawara_4thvsR02corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "ogasawara_5thvsR02corlalmap": {
        "name": "変化域 ogasawara 第5回vsR02corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_ogasawara_5thvsR02corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "okinoerabu_H20vsH30corlalmap": {
        "name": "変化域 okinoerabu H20vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_okinoerabu_H20vsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "okinoerabu_4thvsH30corlalmap": {
        "name": "変化域 okinoerabu 第4回vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_okinoerabu_4thvsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "tarama_H20vsH30corlalmap": {
        "name": "変化域 tarama H20vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_tarama_H20vsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "tarama_4thvsH30corlalmap": {
        "name": "変化域 tarama 第4回vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_tarama_4thvsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "yoron_H20vsH30corlalmap": {
        "name": "変化域 yoron H20vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_yoron_H20vsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "yoron_4thvsH30corlalmap": {
        "name": "変化域 yoron 第4回vsH30corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_yoron_4thvsH30corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "takarajima_kodakarajima_H20vsR03corlalmap": {
        "name": "変化域 宝島 小宝島 H20vsR03corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_takarajima_kodakarajima_H20vsR03corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "takarajima_kodakarajima_4thvsR03corlalmap": {
        "name": "変化域 宝島 小宝島 第4回vsR03corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_takarajima_kodakarajima_4thvsR03corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "tanegashima_yakushima_H20vsR03corlalmap": {
        "name": "変化域 種子島 屋久島 H20vsR03corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_tanegashima_yakushima_H20vsR03corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "tanegashima_yakushima_4thvsR03corlalmap": {
        "name": "変化域 種子島 屋久島 第4回vsR03corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_tanegashima_yakushima_4thvsR03corlalmap/FeatureServer",
        "has_prefecture": False,
    },
    "tanegashima_yakushima_5thvsR03corlalmap": {
        "name": "変化域 種子島 屋久島 第5回vsR03corlalmap",
        "url": "https://svr-moej.gisservice.jp/arcgis/rest/services/Hosted/change_tanegashima_yakushima_5thvsR03corlalmap/FeatureServer",
        "has_prefecture": False,
    },
}
