from qgis.core import (
    QgsFeatureSink,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsVectorLayer,
    QgsFields,
    QgsField,
)
from qgis.PyQt.QtCore import QCoreApplication

from .datasets import DATASETS
from .prefecture import PREFECTURES


class MOELoaderAlgorithm(QgsProcessingAlgorithm):
    DATASET = "DATASET"
    CATEGORY = "CATEGORY"
    PREFECTURE = "PREFECTURE"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config=None):
        """
        URL指定のためのパラメータ（データセット/カテゴリ/都道府県）
        """
        # 全カテゴリをフラット化してリスト作成（データセット名をプレフィックスとして含む）
        self._category_mapping = []  # (dataset_key, category_key, display_name, has_prefecture)
        category_options = []

        for dataset_key, dataset in DATASETS.items():
            for category_key, category in dataset["categories"].items():
                display_name = f"{dataset['name']} - {category['name']}"
                self._category_mapping.append(
                    (
                        dataset_key,
                        category_key,
                        display_name,
                        category["has_prefecture"],
                    )
                )
                category_options.append(display_name)

        # カテゴリ選択（すべてのデータセット×カテゴリの組み合わせ）
        self.addParameter(
            QgsProcessingParameterEnum(
                self.CATEGORY,
                self.tr("データセット"),
                options=category_options,
                defaultValue=0,
            )
        )

        # 都道府県
        prefecture_names = [name for name in PREFECTURES.values()]
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PREFECTURE,
                self.tr("都道府県"),
                options=prefecture_names,
                defaultValue=0,
            )
        )

        # 出力レイヤ
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("出力レイヤ"),
                optional=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        ArcGIS REST FeatureServerからレイヤをロードしてFeatureSinkに出力
        """
        # 選択されたカテゴリインデックスからデータセットとカテゴリ情報を取得
        category_idx = self.parameterAsEnum(parameters, self.CATEGORY, context)
        dataset_key, category_key, display_name, has_prefecture = (
            self._category_mapping[category_idx]
        )

        # データセットとカテゴリを取得
        dataset = DATASETS[dataset_key]
        category = dataset["categories"][category_key]

        # URLを構築
        url = category["url"]

        # レイヤ名を構築（マッピングの表示名を使用）
        layer_name = display_name

        # 都道府県別データの場合、都道府県コードを置換
        if has_prefecture:
            pref_idx = self.parameterAsEnum(parameters, self.PREFECTURE, context)
            if pref_idx is None or pref_idx == 0:
                # pref_idx が 0 は「都道府県を選択してください」が選択されている
                feedback.reportError("都道府県を選択してください")
                return {"OUTPUT": None}

            pref_code = list(PREFECTURES.keys())[pref_idx]
            url = url.format(pref_code=pref_code)
            layer_name = f"{layer_name} ({PREFECTURES[pref_code]})"

        feedback.pushInfo(f"Loading from: {url}")

        # ArcGIS FeatureServerからレイヤをロードしてsinkに出力
        result = self._load_and_write_layers(
            url, layer_name, parameters, context, feedback
        )

        return {"OUTPUT": result}

    def _load_and_write_layers(self, url, layer_name, parameters, context, feedback):
        """
        ArcGIS REST FeatureServerからレイヤをロードし、FeatureSinkに書き込む（最適化版）
        """
        try:
            import json
            from urllib.error import URLError
            from urllib.request import urlopen

            # FeatureServerのメタデータを取得
            try:
                with urlopen(f"{url}?f=json") as response:
                    data = json.loads(response.read().decode())
            except URLError as e:
                feedback.reportError(
                    f"Failed to fetch FeatureServer metadata: {str(e)}"
                )
                return None

            # レイヤリストを取得
            layers = data.get("layers", [])

            if not layers:
                feedback.reportError(f"No layers found in FeatureServer: {url}")
                return None

            # 最初のレイヤのみを処理
            first_layer = layers[0]
            layer_id = first_layer.get("id")
            layer_title = first_layer.get("name", f"Layer {layer_id}")

            # レイヤURLを構築（レイヤIDを含む）
            layer_url = f"{url}/{layer_id}"

            # ArcGIS FeatureServerレイヤを作成
            uri = f"crs='EPSG:4612' url='{layer_url}'"
            full_layer_name = f"{layer_name} - {layer_title}"

            vector_layer = QgsVectorLayer(uri, full_layer_name, "arcgisfeatureserver")

            if not vector_layer.isValid():
                feedback.reportError(
                    f"Failed to load layer: {full_layer_name} (ID: {layer_id})"
                )
                return None

            # フィールドのメタデータをクリア（別名とコメントを削除して警告を抑制）
            cleaned_fields = QgsFields()
            for field in vector_layer.fields():
                # 新しいフィールドを作成（別名とコメントなし）
                new_field = QgsField(field)
                new_field.setAlias("")  # 別名をクリア
                new_field.setComment("")  # コメントをクリア
                cleaned_fields.append(new_field)

            # FeatureSinkを作成（CRSを確実に設定）
            output_crs = vector_layer.crs()

            # QgsProcessingParameterFeatureSinkを使用してsinkを作成
            (sink, dest_id) = self.parameterAsSink(
                parameters,
                self.OUTPUT,
                context,
                cleaned_fields,
                vector_layer.wkbType(),
                output_crs,
                QgsFeatureSink.SinkFlags(),
            )

            if sink is None:
                feedback.reportError("Failed to create output sink")
                return None

            feedback.pushInfo(f"Output CRS: {output_crs.authid()}")

            # フィーチャをバッチで書き込む（高速化）
            total = vector_layer.featureCount()
            feedback.pushInfo(f"Writing {total} features to output...")

            # バッチサイズを設定（メモリ使用量とパフォーマンスのバランス）
            BATCH_SIZE = 1000
            features_batch = []
            processed = 0

            for feature in vector_layer.getFeatures():
                if feedback.isCanceled():
                    break

                features_batch.append(feature)

                # バッチサイズに達したら一括書き込み
                if len(features_batch) >= BATCH_SIZE:
                    sink.addFeatures(features_batch, QgsFeatureSink.FastInsert)
                    processed += len(features_batch)
                    features_batch = []

                    # 進捗更新
                    if total > 0:
                        feedback.setProgress(int((processed / total) * 100))

            # 残りのフィーチャを書き込む
            if features_batch:
                sink.addFeatures(features_batch, QgsFeatureSink.FastInsert)
                processed += len(features_batch)

            feedback.pushInfo(f"Successfully wrote {processed} features")

            return dest_id

        except Exception as e:
            feedback.reportError(f"Error loading layers: {str(e)}")
            import traceback

            feedback.reportError(traceback.format_exc())
            return None

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "MOEGeoportalLoader"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return ""

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return MOELoaderAlgorithm()
