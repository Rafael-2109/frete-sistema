#!/usr/bin/env python3

"""
Utilitário centralizado para geração de números de embarque.
Evita duplicações e problemas de concorrência.

VERSÃO CORRIGIDA: Sincroniza números com IDs para resolver dessincronização
- Se ID estiver à frente do número, usa ID como base
- Resolve problema onde Embarque #254 tinha ID 278
"""

from app import db
from app.embarques.models import Embarque
import threading

# Lock para operações thread-safe
_lock = threading.Lock()

def obter_proximo_numero_embarque():
    """
    Obtém o próximo número de embarque de forma thread-safe.
    
    Esta função centralizada substitui as múltiplas implementações
    inconsistentes espalhadas pelo código.
    
    Returns:
        int: Próximo número de embarque disponível
    """
    with _lock:
        try:
            # Query otimizada para obter o maior número atual
            ultimo_numero = db.session.query(
                db.func.coalesce(db.func.max(Embarque.numero), 0)
            ).scalar()
            
            # 🔧 CORREÇÃO: Sincronizar com IDs se necessário
            ultimo_id = db.session.query(
                db.func.coalesce(db.func.max(Embarque.id), 0)
            ).scalar()
            
            # Se ID está à frente, usar ID como base para próximo número
            if ultimo_id > ultimo_numero:
                ultimo_numero = ultimo_id
            
            proximo_numero = ultimo_numero + 1
            
            # Verifica se já existe um embarque com este número (safety check)
            while Embarque.query.filter_by(numero=proximo_numero).first():
                proximo_numero += 1
            
            return proximo_numero
            
        except Exception as e:
            # Fallback: se der erro, conta todos os embarques + 1
            total_embarques = Embarque.query.count()
            return total_embarques + 1 