from .datasets.coral import CORAL_DATASETS
from .loader_algorithm_base import MOELoaderAlgorithmBase


class CoralLoaderAlgorithm(MOELoaderAlgorithmBase):
    """サンゴ礁調査データ読み込みアルゴリズム"""

    def get_datasets(self):
        return CORAL_DATASETS

    def name(self):
        return "moe_coral_loader"

    def displayName(self):
        return self.tr("サンゴ礁調査データを読み込む")

    def shortHelpString(self):
        return self.tr(
            "環境省が提供するサンゴ礁調査データをQGISに直接読み込むためのツールです。\n"
            "サンゴ浅海生態系現況把握調査、第4回・第5回調査、変化域データなどが含まれます。\n"
            "データセットと出力先を選択すると、ファイルとスタイル設定が自動的に保存されます。"
        )

    def createInstance(self):
        return CoralLoaderAlgorithm()
