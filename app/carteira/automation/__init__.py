# 🤖 MÓDULO DE AUTOMAÇÃO DA CARTEIRA
# Sistema inteligente para gestão automática de carteira de pedidos

from app.carteira.automation.classification_engine import ClassificationEngine
from app.carteira.automation.stock_analyzer import StockAnalyzer  
from app.carteira.automation.scheduling_optimizer import SchedulingOptimizer
from app.carteira.automation.cargo_optimizer import CargoOptimizer 

__all__ = [
    'ClassificationEngine',
    'StockAnalyzer', 
    'SchedulingOptimizer',
    'CargoOptimizer'
] 