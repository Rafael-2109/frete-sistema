"""
Serviço de Carteira - Integração Odoo
=====================================

Responsabilidades:
- Lógica de negócio para carteira
- Integração com Odoo
- Transformação de dados
- Gerenciamento de logs
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Importar dependências com fallback
try:
    from ..utils.odoo_client import OdooClient
    from ..utils.mappers import CarteiraMapper
    from ..validators.carteira_validator import CarteiraValidator
    from ..utils.exceptions import OdooIntegrationError
    _dependencies_available = True
except ImportError as e:
    logger.warning(f"⚠️ Dependências do serviço não disponíveis: {e}")
    _dependencies_available = False

# Integração com modelos do sistema
try:
    from app.carteira.models import CarteiraPrincipal
    from app import db
    _models_available = True
except ImportError:
    logger.warning("⚠️ Modelos do sistema não disponíveis")
    _models_available = False

class CarteiraService:
    """Serviço para integração de carteira com Odoo"""
    
    def __init__(self):
        """Inicializar serviço"""
        if not _dependencies_available:
            raise ImportError("Dependências do serviço não disponíveis")
        
        self.odoo_client = OdooClient()
        self.mapper = CarteiraMapper()
        self.validator = CarteiraValidator()
        
        logger.info("🔧 CarteiraService inicializado")
    
    def import_from_odoo(self, filters: Optional[Dict] = None, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Importar carteira do Odoo
        
        Args:
            filters: Filtros para busca no Odoo
            user: Usuário executando a importação
            
        Returns:
            Resultado da importação
        """
        try:
            logger.info(f"🔄 Iniciando importação da carteira - usuário: {user}")
            
            # 1. Buscar dados no Odoo
            odoo_data = self._fetch_odoo_data(filters or {})
            
            if not odoo_data:
                return {
                    'success': False,
                    'message': 'Nenhum dado encontrado no Odoo',
                    'records_imported': 0
                }
            
            # 2. Transformar dados
            transformed_data = self._transform_data(odoo_data)
            
            # 3. Validar dados
            validation_result = self._validate_data(transformed_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': 'Dados inválidos',
                    'errors': validation_result['errors']
                }
            
            # 4. Importar no sistema
            import_result = self._import_to_system(transformed_data, user or 'sistema')
            
            logger.info(f"✅ Importação concluída - {import_result['records_imported']} registros")
            
            return {
                'success': True,
                'message': 'Carteira importada com sucesso',
                'records_imported': import_result['records_imported'],
                'records_updated': import_result['records_updated'],
                'execution_time': import_result['execution_time']
            }
            
        except OdooIntegrationError as e:
            logger.error(f"❌ Erro na integração Odoo: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Erro inesperado na importação: {e}")
            raise OdooIntegrationError(f"Erro na importação: {str(e)}")
    
    def sync_with_odoo(self, config: Dict) -> Dict[str, Any]:
        """
        Sincronizar carteira com Odoo
        
        Args:
            config: Configurações da sincronização
            
        Returns:
            Resultado da sincronização
        """
        try:
            logger.info("🔄 Iniciando sincronização da carteira")
            
            # Configurar filtros baseados na configuração
            filters = self._build_sync_filters(config)
            
            # Executar sincronização em chunks
            if config.get('incremental', True):
                result = self._incremental_sync(filters, config)
            else:
                result = self._full_sync(filters, config)
            
            logger.info(f"✅ Sincronização concluída - {result['total_processed']} registros")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização: {e}")
            raise OdooIntegrationError(f"Erro na sincronização: {str(e)}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Obter status da sincronização
        
        Returns:
            Status da sincronização
        """
        try:
            # Buscar informações de status (mock)
            status = {
                'last_sync': datetime.now().isoformat(),
                'status': 'success',
                'records_in_system': self._count_system_records(),
                'records_in_odoo': self._count_odoo_records(),
                'sync_health': 'healthy',
                'next_sync': (datetime.now() + timedelta(hours=1)).isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter status: {e}")
            raise
    
    def get_logs(self, limit: int = 100, offset: int = 0, level: str = 'INFO') -> List[Dict]:
        """
        Obter logs de integração
        
        Args:
            limit: Limite de registros
            offset: Offset para paginação
            level: Nível de log
            
        Returns:
            Lista de logs
        """
        try:
            # Mock dos logs (em implementação real, buscaria do sistema de logs)
            logs = [
                {
                    'timestamp': datetime.now().isoformat(),
                    'level': level,
                    'message': 'Importação iniciada',
                    'module': 'carteira_service',
                    'user': 'sistema'
                },
                {
                    'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
                    'level': 'INFO',
                    'message': 'Dados transformados com sucesso',
                    'module': 'carteira_service',
                    'user': 'sistema'
                }
            ]
            
            return logs[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter logs: {e}")
            raise
    
    def get_config(self) -> Dict[str, Any]:
        """
        Obter configurações da integração
        
        Returns:
            Configurações atuais
        """
        # Mock das configurações
        return {
            'sync_interval': 3600,  # 1 hora
            'chunk_size': 100,
            'retry_attempts': 3,
            'timeout': 300,
            'incremental_sync': True,
            'auto_sync': True
        }
    
    def update_config(self, new_config: Dict) -> None:
        """
        Atualizar configurações da integração
        
        Args:
            new_config: Novas configurações
        """
        try:
            # Validar configurações
            required_fields = ['sync_interval', 'chunk_size', 'retry_attempts']
            for field in required_fields:
                if field not in new_config:
                    raise ValueError(f"Campo obrigatório ausente: {field}")
            
            # Atualizar configurações (mock)
            logger.info("⚙️ Configurações atualizadas")
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar configurações: {e}")
            raise
    
    # ==========================================================================
    # MÉTODOS PRIVADOS
    # ==========================================================================
    
    def _fetch_odoo_data(self, filters: Dict) -> List[Dict]:
        """Buscar dados no Odoo"""
        try:
            # Construir domínio de filtros
            domain = self._build_odoo_domain(filters)
            
            # Buscar dados
            data = self.odoo_client.search_read(
                model='sale.order.line',
                domain=domain,
                fields=self.mapper.get_odoo_fields()
            )
            
            logger.info(f"📊 Buscados {len(data)} registros no Odoo")
            return data
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar dados no Odoo: {e}")
            raise OdooIntegrationError(f"Erro ao buscar dados: {str(e)}")
    
    def _transform_data(self, odoo_data: List[Dict]) -> List[Dict]:
        """Transformar dados do Odoo para formato do sistema"""
        try:
            transformed = []
            
            for record in odoo_data:
                system_record = self.mapper.odoo_to_system(record)
                transformed.append(system_record)
            
            logger.info(f"🔄 Transformados {len(transformed)} registros")
            return transformed
            
        except Exception as e:
            logger.error(f"❌ Erro na transformação: {e}")
            raise
    
    def _validate_data(self, data: List[Dict]) -> Dict[str, Any]:
        """Validar dados transformados"""
        try:
            errors = []
            
            for i, record in enumerate(data):
                validation_result = self.validator.validate_record(record)
                if not validation_result['valid']:
                    errors.append({
                        'record_index': i,
                        'errors': validation_result['errors']
                    })
            
            return {
                'valid': len(errors) == 0,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na validação: {e}")
            raise
    
    def _import_to_system(self, data: List[Dict], user: str) -> Dict[str, Any]:
        """Importar dados no sistema"""
        if not _models_available:
            raise ImportError("Modelos do sistema não disponíveis")
        
        try:
            start_time = datetime.now()
            records_imported = 0
            records_updated = 0
            
            for record in data:
                # Verificar se registro já existe
                existing = CarteiraPrincipal.query.filter_by(
                    num_pedido=record['num_pedido'],
                    cod_produto=record['cod_produto']
                ).first()
                
                if existing:
                    # Atualizar existente
                    self._update_record(existing, record)
                    records_updated += 1
                else:
                    # Criar novo
                    self._create_record(record)
                    records_imported += 1
            
            db.session.commit()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'records_imported': records_imported,
                'records_updated': records_updated,
                'execution_time': execution_time
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao importar dados: {e}")
            raise
    
    def _build_odoo_domain(self, filters: Dict) -> List:
        """Construir domínio de filtros para Odoo"""
        domain = []
        
        if filters.get('date_from'):
            domain.append(('create_date', '>=', filters['date_from']))
        
        if filters.get('date_to'):
            domain.append(('create_date', '<=', filters['date_to']))
        
        if filters.get('partner_id'):
            domain.append(('order_id.partner_id', '=', filters['partner_id']))
        
        return domain
    
    def _build_sync_filters(self, config: Dict) -> Dict:
        """Construir filtros para sincronização"""
        filters = {}
        
        if config.get('incremental', True):
            # Buscar apenas registros modificados nas últimas horas
            hours_back = config.get('hours_back', 24)
            date_from = datetime.now() - timedelta(hours=hours_back)
            filters['date_from'] = date_from.isoformat()
        
        return filters
    
    def _incremental_sync(self, filters: Dict, config: Dict) -> Dict[str, Any]:
        """Sincronização incremental"""
        chunk_size = config.get('chunk_size', 100)
        
        # Processar em chunks
        total_processed = 0
        
        # Mock da sincronização incremental
        for chunk in range(0, 1000, chunk_size):
            # Processar chunk
            total_processed += min(chunk_size, 1000 - chunk)
        
        return {
            'type': 'incremental',
            'total_processed': total_processed,
            'execution_time': 30.5
        }
    
    def _full_sync(self, filters: Dict, config: Dict) -> Dict[str, Any]:
        """Sincronização completa"""
        # Mock da sincronização completa
        return {
            'type': 'full',
            'total_processed': 5000,
            'execution_time': 120.0
        }
    
    def _count_system_records(self) -> int:
        """Contar registros no sistema"""
        if not _models_available:
            return 0
        
        try:
            return CarteiraPrincipal.query.count()
        except:
            return 0
    
    def _count_odoo_records(self) -> int:
        """Contar registros no Odoo"""
        try:
            return self.odoo_client.search_count(
                model='sale.order.line',
                domain=[]
            )
        except:
            return 0
    
    def _update_record(self, existing_record, new_data: Dict) -> None:
        """Atualizar registro existente"""
        for field, value in new_data.items():
            if hasattr(existing_record, field):
                setattr(existing_record, field, value)
    
    def _create_record(self, data: Dict) -> None:
        """Criar novo registro"""
        new_record = CarteiraPrincipal(**data)
        db.session.add(new_record)

logger.info("🔧 CarteiraService definido") 