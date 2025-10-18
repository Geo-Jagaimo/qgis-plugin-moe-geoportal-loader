from .datasets.vegetation import VEGETATION_DATASETS
from .loader_algorithm_base import MOELoaderAlgorithmBase


class VegetationLoaderAlgorithm(MOELoaderAlgorithmBase):
    """植生図データ読み込みアルゴリズム"""

    def get_datasets(self):
        return VEGETATION_DATASETS

    def has_prefecture_parameter(self):
        return True

    def name(self):
        return "moe_vegetation_loader"

    def displayName(self):
        return self.tr("植生図データを読み込む")

    def shortHelpString(self):
        return self.tr(
            "環境省が提供する植生図データをQGISに直接読み込むためのツールです。\n"
            "現存植生図、自然度区分図、ブロック別植生図などが含まれます。\n"
            "データセットと出力先を選択すると、ファイルとスタイル設定が自動的に保存されます。"
        )

    def createInstance(self):
        return VegetationLoaderAlgorithm()
