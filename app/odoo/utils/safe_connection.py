"""
Conexão Segura com Odoo - Wrapper com Fallback Automático
==========================================================

Este módulo fornece uma camada de segurança sobre a conexão Odoo
que trata automaticamente erros de campos inexistentes.

Quando um campo não existe no banco (como l10n_br_gnre_ok),
o sistema automaticamente ajusta a consulta para funcionar.

Autor: Sistema de Fretes
Data: 2025-08-03
"""

import logging
import re
from typing import List, Dict, Any, Optional
from .connection import OdooConnection

logger = logging.getLogger(__name__)


class SafeOdooConnection:
    """
    Wrapper seguro para conexão Odoo com fallback automático
    """
    
    def __init__(self, connection: OdooConnection):
        self.connection = connection
        self._problematic_fields_cache = {}
        
    def _extract_missing_field_from_error(self, error_str: str) -> Optional[str]:
        """
        Extrai o nome do campo problemático da mensagem de erro
        
        Exemplo de erro:
        'não existe a coluna account_move.l10n_br_gnre_ok'
        """
        patterns = [
            r'não existe a coluna [\w_]+\.([\w_]+)',
            r'column [\w_]+\.([\w_]+) does not exist',
            r'field [\'"]([\w_]+)[\'"] does not exist',
            r'Unknown column [\'"]([\w_]+)[\'"]',
        ]
        
        error_text = str(error_str)
        for pattern in patterns:
            match = re.search(pattern, error_text, re.IGNORECASE)
            if match:
                field_name = match.group(1)
                logger.info(f"🔍 Campo problemático identificado: {field_name}")
                return field_name
        
        return None
    
    def _simplify_query_for_related_fields(self, model: str, domain: list, fields: list) -> tuple:
        """
        Simplifica queries que envolvem campos relacionados (com /)
        Retorna (use_ids_only, simplified_fields)
        """
        # Se há campos com move_id, partner_id, etc, que podem causar problemas
        related_fields = ['move_id', 'partner_id', 'product_id', 'user_id', 'team_id']
        has_related = any(field in fields for field in related_fields if field in fields)
        
        if has_related and model == 'account.move.line':
            # Para account.move.line, usar estratégia de IDs apenas
            logger.info("⚠️ Detectado campos relacionados em account.move.line - usando estratégia segura")
            return True, None
            
        return False, fields
    
    def search_read_safe(self, model: str, domain: list, fields: Optional[list] = None, 
                        limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict]:
        """
        Versão segura de search_read com fallback automático
        
        Estratégia:
        1. Tenta consulta normal
        2. Se falhar com erro de campo, usa estratégia alternativa
        3. Se necessário, faz consultas separadas
        """
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        if offset:
            kwargs['offset'] = offset
            
        # Verificar se precisamos simplificar a query
        use_ids_only, safe_fields = self._simplify_query_for_related_fields(model, domain, fields or [])
        
        if use_ids_only:
            # Estratégia alternativa: buscar IDs primeiro, depois dados básicos
            return self._search_read_with_ids_strategy(model, domain, fields, limit, offset)
        
        try:
            # Tentar consulta normal primeiro
            result = self.connection.execute_kw(model, 'search_read', [domain], kwargs)
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"⚠️ Erro na consulta normal: {error_msg[:200]}")
            
            # Verificar se é erro de campo inexistente
            missing_field = self._extract_missing_field_from_error(error_msg)
            
            if missing_field or 'UndefinedColumn' in error_msg or 'não existe a coluna' in error_msg:
                logger.info("🔄 Usando estratégia alternativa devido a campo problemático")
                return self._search_read_with_ids_strategy(model, domain, fields, limit, offset)
            else:
                # Se não é erro de campo, propagar o erro original
                raise
    
    def _search_read_with_ids_strategy(self, model: str, domain: list, 
                                      fields: Optional[list] = None, 
                                      limit: Optional[int] = None,
                                      offset: Optional[int] = None) -> List[Dict]:
        """
        Estratégia alternativa: buscar IDs primeiro, depois ler dados
        Isso evita problemas com campos computados que referenciam campos inexistentes
        """
        try:
            logger.info(f"🔄 Estratégia alternativa para {model}")
            
            # Passo 1: Buscar apenas IDs
            kwargs_search = {}
            if limit:
                kwargs_search['limit'] = limit
            if offset:
                kwargs_search['offset'] = offset
                
            ids = self.connection.execute_kw(model, 'search', [domain], kwargs_search)
            
            if not ids:
                return []
            
            logger.info(f"📊 {len(ids)} IDs encontrados")
            
            # Passo 2: Ler dados básicos (sem campos relacionados complexos)
            if model == 'account.move.line':
                # Para account.move.line, usar campos seguros
                safe_fields = self._get_safe_fields_for_model(model, fields)
                basic_data = self._read_in_batches(model, ids, safe_fields)
                
                # Passo 3: Enriquecer com dados relacionados se necessário
                if fields and 'move_id' in fields:
                    basic_data = self._enrich_with_move_data(basic_data)
                if fields and 'partner_id' in fields:
                    basic_data = self._enrich_with_partner_data(basic_data)
                if fields and 'product_id' in fields:
                    basic_data = self._enrich_with_product_data(basic_data)
                    
                return basic_data
            else:
                # Para outros modelos, tentar ler normalmente
                kwargs_read = {}
                if fields:
                    kwargs_read['fields'] = fields
                    
                return self.connection.execute_kw(model, 'read', [ids], kwargs_read)
                
        except Exception as e:
            logger.error(f"❌ Erro na estratégia alternativa: {e}")
            # Retornar lista vazia em vez de falhar completamente
            return []
    
    def _get_safe_fields_for_model(self, model: str, requested_fields: Optional[list] = None) -> list:
        """
        Retorna lista de campos seguros para um modelo
        """
        if model == 'account.move.line':
            # Campos básicos seguros que não causam problemas
            # IMPORTANTE: Não incluir display_name pois ele computa campos problemáticos
            safe_fields = [
                'id', 'quantity', 'price_unit', 'price_total', 
                'date', 'name'
            ]
            
            # Adicionar campos numéricos de IDs (não objetos completos)
            # Vamos buscar apenas os IDs, não os objetos relacionados
            if requested_fields:
                for field in requested_fields:
                    if field in ['move_id', 'partner_id', 'product_id', 'display_name']:
                        # Não incluir campos relacionados ou computados problemáticos
                        # Eles serão tratados separadamente
                        continue
                    elif field not in safe_fields:
                        # Tentar incluir outros campos solicitados
                        safe_fields.append(field)
            
            return safe_fields
        
        # Para outros modelos, retornar campos solicitados
        return requested_fields or []
    
    def _read_in_batches(self, model: str, ids: list, fields: list, batch_size: int = 100) -> list:
        """
        Lê registros em lotes para evitar timeout
        """
        results = []
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            try:
                batch_data = self.connection.execute_kw(
                    model, 'read', [batch_ids], {'fields': fields}
                )
                # Adicionar display_name construído manualmente se necessário
                if model == 'account.move.line':
                    for record in batch_data:
                        # Construir display_name manualmente
                        # Formato típico: "Invoice Line: [name or product]"
                        display_name = record.get('name', '')
                        if not display_name:
                            display_name = f"Line {record.get('id', '')}"
                        record['display_name'] = display_name
                
                results.extend(batch_data)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao ler lote {i}-{i+batch_size}: {e}")
                # Continuar com próximo lote
                continue
        
        return results
    
    def _enrich_with_move_data(self, records: list) -> list:
        """
        Enriquece registros com dados de move_id (fatura)
        """
        # Coletar move_ids únicos
        move_ids = set()
        for record in records:
            # Buscar o move_id através de uma query separada
            try:
                move_data = self.connection.execute_kw(
                    'account.move.line', 
                    'read', 
                    [[record['id']]], 
                    {'fields': ['move_id']}
                )
                if move_data and move_data[0].get('move_id'):
                    move_id_data = move_data[0]['move_id']
                    if isinstance(move_id_data, (list, tuple)):
                        record['move_id'] = move_id_data
                        move_ids.add(move_id_data[0])
            except:
                record['move_id'] = False
        
        # Buscar dados das faturas de forma segura
        if move_ids:
            try:
                safe_move_fields = ['id', 'name', 'state', 'date']
                moves = self.connection.execute_kw(
                    'account.move',
                    'read',
                    [list(move_ids)],
                    {'fields': safe_move_fields}
                )
                move_dict = {m['id']: m for m in moves}
                
                # Atualizar registros com dados adicionais
                for record in records:
                    if record.get('move_id') and isinstance(record['move_id'], (list, tuple)):
                        move_id = record['move_id'][0]
                        if move_id in move_dict:
                            # Manter formato [id, name]
                            record['move_id'] = [move_id, move_dict[move_id].get('name', '')]
                            # Adicionar campos extras se necessário
                            record['_move_data'] = move_dict[move_id]
            except Exception as e:
                logger.warning(f"⚠️ Erro ao enriquecer com dados de fatura: {e}")
        
        return records
    
    def _enrich_with_partner_data(self, records: list) -> list:
        """
        Enriquece registros com dados de partner_id (cliente)
        """
        # Similar ao _enrich_with_move_data
        partner_ids = set()
        for record in records:
            try:
                partner_data = self.connection.execute_kw(
                    'account.move.line',
                    'read',
                    [[record['id']]],
                    {'fields': ['partner_id']}
                )
                if partner_data and partner_data[0].get('partner_id'):
                    partner_id_data = partner_data[0]['partner_id']
                    if isinstance(partner_id_data, (list, tuple)):
                        record['partner_id'] = partner_id_data
                        partner_ids.add(partner_id_data[0])
            except:
                record['partner_id'] = False
        
        return records
    
    def _enrich_with_product_data(self, records: list) -> list:
        """
        Enriquece registros com dados de product_id (produto)
        """
        # Similar aos outros métodos de enriquecimento
        product_ids = set()
        for record in records:
            try:
                product_data = self.connection.execute_kw(
                    'account.move.line',
                    'read',
                    [[record['id']]],
                    {'fields': ['product_id']}
                )
                if product_data and product_data[0].get('product_id'):
                    product_id_data = product_data[0]['product_id']
                    if isinstance(product_id_data, (list, tuple)):
                        record['product_id'] = product_id_data
                        product_ids.add(product_id_data[0])
            except:
                record['product_id'] = False
        
        return records

    # Métodos de conveniência que delegam para a conexão original
    def authenticate(self):
        return self.connection.authenticate()
    
    def search(self, model: str, domain: list, limit: Optional[int] = None):
        return self.connection.search(model, domain, limit)
    
    def read(self, model: str, ids: list, fields: Optional[list] = None):
        return self.connection.read(model, ids, fields)
    
    def execute_kw(self, model: str, method: str, args: list, kwargs: Optional[dict] = None):
        return self.connection.execute_kw(model, method, args, kwargs)
    
    def search_read(self, model: str, domain: list, fields: Optional[list] = None, limit: Optional[int] = None):
        """Usa a versão segura por padrão"""
        return self.search_read_safe(model, domain, fields, limit)
    
    def buscar_registro_por_id(self, model: str, record_id: int, fields: Optional[list] = None):
        return self.connection.buscar_registro_por_id(model, record_id, fields)


def get_safe_odoo_connection():
    """Retorna uma conexão Odoo segura com fallback automático"""
    from .connection import get_odoo_connection
    base_connection = get_odoo_connection()
    return SafeOdooConnection(base_connection)