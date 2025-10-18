from .datasets.seagrass import SEAGRASS_DATASETS
from .loader_algorithm_base import MOELoaderAlgorithmBase


class SeagrassLoaderAlgorithm(MOELoaderAlgorithmBase):
    """藻場調査データ読み込みアルゴリズム"""

    def get_datasets(self):
        return SEAGRASS_DATASETS

    def name(self):
        return "moe_seagrass_loader"

    def displayName(self):
        return self.tr("藻場調査データを読み込む")

    def shortHelpString(self):
        return self.tr(
            "環境省が提供する藻場調査データをQGISに直接読み込むためのツールです。\n"
            "第4回・第5回調査、2018-2020年調査（UTM別）などが含まれます。\n"
            "データセットと出力先を選択すると、ファイルとスタイル設定が自動的に保存されます。"
        )

    def createInstance(self):
        return SeagrassLoaderAlgorithm()
