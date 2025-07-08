"""
🎓 LEARNING MODULE - Sistemas de Aprendizado

Este módulo gerencia os sistemas de aprendizado:
- Aprendizado vitalício
- Aprendizado humano-no-loop
"""

from .lifelong_learning import LifelongLearningSystem
from .human_in_loop_learning import HumanInLoopLearning

__all__ = [
    'LifelongLearningSystem',
    'HumanInLoopLearning',
]
