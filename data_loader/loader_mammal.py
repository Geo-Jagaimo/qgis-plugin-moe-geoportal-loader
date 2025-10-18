from .datasets.mammal import MAMMAL_DATASETS
from .loader_algorithm_base import MOELoaderAlgorithmBase


class MammalLoaderAlgorithm(MOELoaderAlgorithmBase):
    """中大型哺乳類分布調査データ読み込みアルゴリズム"""

    def get_datasets(self):
        return MAMMAL_DATASETS

    def name(self):
        return "moe_mammal_loader"

    def displayName(self):
        return self.tr("哺乳類分布調査データを読み込む")

    def shortHelpString(self):
        return self.tr(
            "環境省が提供する中大型哺乳類分布調査データをQGISに直接読み込むためのツールです。\n"
            "アナグマ、キツネ、タヌキの分布調査データが含まれます。\n"
            "データセットと出力先を選択すると、ファイルとスタイル設定が自動的に保存されます。"
        )

    def createInstance(self):
        return MammalLoaderAlgorithm()
