"""
Funções auxiliares da carteira
"""

# Removidos imports não utilizados após limpeza de funções duplicadas
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)



def calcular_estoque_data_especifica(projecao_29_dias, data_target):
    """
    Calcula estoque para uma data específica baseado na projeção
    """
    try:
        data_hoje = datetime.now().date()
        diff_dias = (data_target - data_hoje).days
        
        # Se data é passado ou muito futuro, usar fallbacks
        if diff_dias < 0:
            return 0  # Data no passado = sem estoque
        if diff_dias >= len(projecao_29_dias):
            return 0  # Além da projeção = sem estoque
        
        # Buscar estoque final do dia específico na projeção
        dia_especifico = projecao_29_dias[diff_dias]
        return dia_especifico.get('estoque_final', 0)
        
    except Exception as e:
        logger.warning(f"Erro ao calcular estoque para data {data_target}: {e}")
        return 0


def encontrar_proxima_data_com_estoque(projecao_29_dias, qtd_necessaria):
    """
    Encontra a próxima data com estoque suficiente para atender a quantidade
    """
    try:
        data_hoje = datetime.now().date()
        qtd_necessaria = float(qtd_necessaria or 0)
        
        if qtd_necessaria <= 0:
            return data_hoje  # Se não precisa de nada, qualquer data serve
        
        # Procurar primeiro dia com estoque suficiente
        for i, dia in enumerate(projecao_29_dias):
            estoque_final = dia.get('estoque_final', 0)
            if estoque_final >= qtd_necessaria:
                data_disponivel = data_hoje + timedelta(days=i)
                return data_disponivel.strftime('%d/%m/%Y')
        
        # Se não encontrou em 29 dias, retornar informação
        return "Sem estoque em 29 dias"
        
    except Exception as e:
        logger.warning(f"Erro ao encontrar próxima data com estoque: {e}")
        return None