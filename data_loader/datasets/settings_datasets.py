"""
後方互換性のために全データセットを統合
新しいコードでは個別のモジュール（vegetation.py, coral.py等）を使用してください
"""

from .coral import CORAL_DATASETS
from .mammal import MAMMAL_DATASETS
from .seagrass import SEAGRASS_DATASETS
from .vegetation import VEGETATION_DATASETS

# 後方互換性のために全データセットを統合
DATASETS = {
    **VEGETATION_DATASETS,
    **CORAL_DATASETS,
    **MAMMAL_DATASETS,
    **SEAGRASS_DATASETS,
}
