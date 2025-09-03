"""
Utilitário centralizado para geração de IDs de lote
Data: 2025-01-29

Padronização única da geração de separacao_lote_id
"""

from datetime import datetime
import random
import hashlib
from app import db
import logging

logger = logging.getLogger(__name__)

def gerar_lote_id():
    """
    Gera ID único para lotes de separação
    
    FORMATO PADRÃO: LOTE_YYYYMMDD_HHMMSS_XXX
    Exemplo: LOTE_20250129_143025_001
    
    Vantagens deste formato:
    - Ordenável cronologicamente
    - Informativo (mostra quando foi criado)
    - Garantidamente único
    - Útil para debug e auditoria
    
    Returns:
        String com o ID do lote único
    """
    try:
        agora = datetime.now()
        data_str = agora.strftime('%Y%m%d')
        hora_str = agora.strftime('%H%M%S')
        random_str = str(random.randint(1, 999)).zfill(3)
        
        lote_id = f"LOTE_{data_str}_{hora_str}_{random_str}"
        
        # Verificar unicidade no banco
        from app.separacao.models import Separacao
        existe = db.session.query(Separacao).filter(
            Separacao.separacao_lote_id == lote_id
        ).first()
        
        if existe:
            # Se existir (improvável), usar microsegundos
            microseg_str = str(agora.microsecond)[:3]
            lote_id = f"LOTE_{data_str}_{hora_str}_{microseg_str}"
        
        return lote_id
        
    except Exception as e:
        logger.error(f"Erro ao gerar lote ID: {e}")
        # Fallback com timestamp Unix (ainda único e ordenável)
        timestamp = int(datetime.now().timestamp())
        return f"LOTE_{timestamp}"

def calcular_hash_lote(lote_id):
    """
    Calcula hash MD5 determinístico para um lote_id
    Usado para gerar IDs inteiros consistentes na VIEW pedidos
    
    Args:
        lote_id: ID do lote
    
    Returns:
        Inteiro positivo baseado no hash
    """
    if not lote_id:
        return 0
    
    # Gera hash MD5 e converte para inteiro
    hash_md5 = hashlib.md5(lote_id.encode()).hexdigest()
    # Pega os primeiros 8 caracteres e converte para int
    hash_int = int(hash_md5[:8], 16)
    
    # Garante número positivo
    return abs(hash_int)