"""
Mapeadores - Transformação de dados Odoo ↔ Sistema
==================================================

Responsabilidades:
- Mapeamento centralizado de campos
- Transformação de dados bidirecionais
- Validação de estruturas
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Importar mapeamentos do arquivo de configuração
try:
    from ..config.field_mappings import CARTEIRA_MAPPING, FATURAMENTO_MAPPING
    _mappings_available = True
except ImportError:
    logger.warning("⚠️ Arquivos de mapeamento não disponíveis")
    _mappings_available = False

class BaseMapper:
    """Classe base para mapeadores"""
    
    def __init__(self, mapping: Dict[str, str]):
        """
        Inicializar mapeador
        
        Args:
            mapping: Dicionário de mapeamento (campo_sistema: campo_odoo)
        """
        self.mapping = mapping
        self.reverse_mapping = {v: k for k, v in mapping.items()}
    
    def get_odoo_fields(self) -> List[str]:
        """
        Obter lista de campos do Odoo
        
        Returns:
            Lista de campos do Odoo
        """
        return list(self.mapping.values())
    
    def get_system_fields(self) -> List[str]:
        """
        Obter lista de campos do sistema
        
        Returns:
            Lista de campos do sistema
        """
        return list(self.mapping.keys())
    
    def odoo_to_system(self, odoo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transformar dados do Odoo para formato do sistema
        
        Args:
            odoo_data: Dados do Odoo
            
        Returns:
            Dados no formato do sistema
        """
        system_data = {}
        
        for system_field, odoo_field in self.mapping.items():
            value = odoo_data.get(odoo_field)
            
            # Aplicar transformações específicas
            transformed_value = self._transform_odoo_value(system_field, value)
            
            system_data[system_field] = transformed_value
        
        return system_data
    
    def system_to_odoo(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transformar dados do sistema para formato do Odoo
        
        Args:
            system_data: Dados do sistema
            
        Returns:
            Dados no formato do Odoo
        """
        odoo_data = {}
        
        for system_field, value in system_data.items():
            if system_field in self.mapping:
                odoo_field = self.mapping[system_field]
                
                # Aplicar transformações específicas
                transformed_value = self._transform_system_value(system_field, value)
                
                odoo_data[odoo_field] = transformed_value
        
        return odoo_data
    
    def _transform_odoo_value(self, system_field: str, value: Any) -> Any:
        """
        Transformar valor do Odoo para formato do sistema
        
        Args:
            system_field: Nome do campo no sistema
            value: Valor original do Odoo
            
        Returns:
            Valor transformado para o sistema
        """
        if value is None:
            return None
        
        # Transformações específicas por tipo de campo
        if 'data' in system_field:
            return self._transform_date_from_odoo(value)
        elif 'qtd' in system_field or 'preco' in system_field or 'valor' in system_field:
            return self._transform_number_from_odoo(value)
        elif 'cnpj' in system_field:
            return self._transform_cnpj_from_odoo(value)
        else:
            return self._transform_string_from_odoo(value)
    
    def _transform_system_value(self, system_field: str, value: Any) -> Any:
        """
        Transformar valor do sistema para formato do Odoo
        
        Args:
            system_field: Nome do campo no sistema
            value: Valor original do sistema
            
        Returns:
            Valor transformado para o Odoo
        """
        if value is None:
            return None
        
        # Transformações específicas por tipo de campo
        if 'data' in system_field:
            return self._transform_date_to_odoo(value)
        elif 'qtd' in system_field or 'preco' in system_field or 'valor' in system_field:
            return self._transform_number_to_odoo(value)
        elif 'cnpj' in system_field:
            return self._transform_cnpj_to_odoo(value)
        else:
            return self._transform_string_to_odoo(value)
    
    def _transform_date_from_odoo(self, value: Any) -> Optional[datetime]:
        """Transformar data do Odoo para datetime"""
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return None
        return value
    
    def _transform_date_to_odoo(self, value: Any) -> Optional[str]:
        """Transformar datetime para formato do Odoo"""
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return str(value) if value else None
    
    def _transform_number_from_odoo(self, value: Any) -> Optional[float]:
        """Transformar número do Odoo para float"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            try:
                # Tratar formato brasileiro (1.234,56)
                if ',' in value:
                    value = value.replace('.', '').replace(',', '.')
                return float(value)
            except ValueError:
                return None
        return None
    
    def _transform_number_to_odoo(self, value: Any) -> Optional[float]:
        """Transformar número do sistema para formato do Odoo"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None
    
    def _transform_cnpj_from_odoo(self, value: Any) -> Optional[str]:
        """Transformar CNPJ do Odoo para formato brasileiro"""
        if not value:
            return None
        
        # Remover formatação
        cnpj = str(value).replace('.', '').replace('/', '').replace('-', '')
        
        # Aplicar formatação brasileira
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        
        return str(value)
    
    def _transform_cnpj_to_odoo(self, value: Any) -> Optional[str]:
        """Transformar CNPJ do sistema para formato do Odoo"""
        if not value:
            return None
        
        # Manter formatação brasileira
        return str(value)
    
    def _transform_string_from_odoo(self, value: Any) -> Optional[str]:
        """Transformar string do Odoo para formato do sistema"""
        if value is None:
            return None
        return str(value).strip()
    
    def _transform_string_to_odoo(self, value: Any) -> Optional[str]:
        """Transformar string do sistema para formato do Odoo"""
        if value is None:
            return None
        return str(value).strip()

class CarteiraMapper(BaseMapper):
    """Mapeador específico para carteira"""
    
    def __init__(self):
        """Inicializar mapeador de carteira"""
        # Mapeamento usando arquivo de configuração ou fallback
        if _mappings_available:
            mapping = CARTEIRA_MAPPING
        else:
            # Mapeamento básico de fallback
            mapping = {
                'num_pedido': 'order_id/name',
                'cod_produto': 'product_id/default_code',
                'nome_produto': 'product_id/name',
                'qtd_produto_pedido': 'product_uom_qty',
                'cnpj_cpf': 'order_id/partner_id/l10n_br_cnpj'
            }
        
        super().__init__(mapping)
        logger.info("🗂️ CarteiraMapper inicializado")
    
    def _transform_odoo_value(self, system_field: str, value: Any) -> Any:
        """Transformações específicas da carteira"""
        # Aplicar transformações base
        transformed = super()._transform_odoo_value(system_field, value)
        
        # Transformações específicas da carteira
        if system_field == 'status_pedido':
            return self._transform_status_pedido(transformed)
        elif system_field == 'nome_cidade':
            return self._transform_cidade_uf(transformed)
        
        return transformed
    
    def _transform_status_pedido(self, value: Any) -> Optional[str]:
        """Transformar status do pedido"""
        if not value:
            return None
        
        # Mapeamento de status Odoo → Sistema
        status_mapping = {
            'draft': 'Rascunho',
            'sent': 'Enviado',
            'sale': 'Pedido de venda',
            'done': 'Concluído',
            'cancel': 'Cancelado'
        }
        
        return status_mapping.get(str(value), str(value))
    
    def _transform_cidade_uf(self, value: Any) -> Optional[str]:
        """Extrair cidade do formato "Cidade (UF)" """
        if not value:
            return None
        
        value_str = str(value)
        
        # Formato "Cidade (UF)" → "Cidade"
        if '(' in value_str and ')' in value_str:
            return value_str.split('(')[0].strip()
        
        return value_str

class FaturamentoMapper(BaseMapper):
    """Mapeador específico para faturamento"""
    
    def __init__(self):
        """Inicializar mapeador de faturamento"""
        # Mapeamento usando arquivo de configuração ou fallback
        if _mappings_available:
            mapping = FATURAMENTO_MAPPING
        else:
            # Mapeamento básico de fallback
            mapping = {
                'numero_nf': 'invoice_line_ids/x_studio_nf_e',
                'cnpj_cliente': 'invoice_line_ids/partner_id/l10n_br_cnpj',
                'nome_cliente': 'invoice_line_ids/partner_id',
                'cod_produto': 'invoice_line_ids/product_id/code',
                'qtd_produto_faturado': 'invoice_line_ids/quantity'
            }
        
        super().__init__(mapping)
        logger.info("📊 FaturamentoMapper inicializado")
    
    def _transform_odoo_value(self, system_field: str, value: Any) -> Any:
        """Transformações específicas do faturamento"""
        # Aplicar transformações base
        transformed = super()._transform_odoo_value(system_field, value)
        
        # Transformações específicas do faturamento
        if system_field == 'status_nf':
            return self._transform_status_nf(transformed)
        elif system_field == 'numero_nf':
            return self._transform_numero_nf(transformed)
        
        return transformed
    
    def _transform_status_nf(self, value: Any) -> Optional[str]:
        """Transformar status da NF"""
        if not value:
            return None
        
        # Mapeamento de status Odoo → Sistema
        status_mapping = {
            'draft': 'Rascunho',
            'posted': 'Lançado',
            'cancel': 'Cancelado'
        }
        
        return status_mapping.get(str(value), str(value))
    
    def _transform_numero_nf(self, value: Any) -> Optional[str]:
        """Transformar número da NF"""
        if not value:
            return None
        
        # Garantir que é string
        return str(value).strip()

# Funções de conveniência
def get_carteira_mapper() -> CarteiraMapper:
    """Obter instância do mapeador de carteira"""
    return CarteiraMapper()

def get_faturamento_mapper() -> FaturamentoMapper:
    """Obter instância do mapeador de faturamento"""
    return FaturamentoMapper()

logger.info("🔄 Mapeadores Odoo carregados") 