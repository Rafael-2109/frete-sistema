"""
🚚 TRANSPORTADORAS MAPPER - Mapeamentos para Modelo Transportadora
================================================================

Mapper especializado para o modelo Transportadora.

Campos mapeados:
- Identificação: razao_social, cnpj, codigo
- Localização: cidade, uf, endereco
- Contato: telefone, email
- Operação: freteiro, ativo
"""

from typing import Dict, Any
from .base_mapper import BaseMapper

class TransportadorasMapper(BaseMapper):
    """
    Mapper específico para o modelo Transportadora.
    
    Responsável por mapear termos naturais para campos
    da tabela 'transportadoras' no banco de dados.
    """
    
    def __init__(self):
        super().__init__('Transportadora')
    
    def _criar_mapeamentos(self) -> Dict[str, Dict[str, Any]]:
        """
        Cria mapeamentos específicos para o modelo Transportadora.
        
        Returns:
            Dict com mapeamentos de campos de Transportadora
        """
        return {
            # 🔢 IDENTIFICAÇÃO
            'razao_social': {
                'campo_principal': 'razao_social',
                'termos_naturais': [
                    'transportadora', 'nome da transportadora', 'razão social',
                    'razao social', 'empresa', 'nome da empresa',
                    'transportadora nome', 'empresa transportadora'
                ],
                'tipo': 'string',
                'observacao': 'Razão social da transportadora'
            },
            
            'cnpj': {
                'campo_principal': 'cnpj',
                'termos_naturais': [
                    'cnpj', 'cnpj da transportadora', 'documento',
                    'documento da transportadora', 'cnpj transportadora'
                ],
                'tipo': 'string',
                'observacao': 'CNPJ da transportadora'
            },
            
            'codigo': {
                'campo_principal': 'codigo',
                'termos_naturais': [
                    'codigo', 'código', 'codigo da transportadora',
                    'código da transportadora', 'id transportadora',
                    'identificador'
                ],
                'tipo': 'string',
                'observacao': 'Código identificador da transportadora'
            },
            
            # 🏠 LOCALIZAÇÃO
            'cidade': {
                'campo_principal': 'cidade',
                'termos_naturais': [
                    'cidade', 'cidade da transportadora', 'municipio',
                    'município', 'localidade', 'onde fica'
                ],
                'tipo': 'string',
                'observacao': 'Cidade da transportadora'
            },
            
            'uf': {
                'campo_principal': 'uf',
                'termos_naturais': [
                    'uf', 'estado', 'uf da transportadora',
                    'estado da transportadora', 'sigla do estado'
                ],
                'tipo': 'string',
                'observacao': 'Estado da transportadora'
            },
            
            'endereco': {
                'campo_principal': 'endereco',
                'termos_naturais': [
                    'endereço', 'endereco', 'rua', 'logradouro',
                    'endereço da transportadora', 'endereco da transportadora'
                ],
                'tipo': 'string',
                'observacao': 'Endereço da transportadora'
            },
            
            # 📞 CONTATO
            'telefone': {
                'campo_principal': 'telefone',
                'termos_naturais': [
                    'telefone', 'telefone da transportadora', 'fone',
                    'contato', 'número de contato', 'numero de contato'
                ],
                'tipo': 'string',
                'observacao': 'Telefone de contato da transportadora'
            },
            
            'email': {
                'campo_principal': 'email',
                'termos_naturais': [
                    'email', 'e-mail', 'email da transportadora',
                    'e-mail da transportadora', 'contato email'
                ],
                'tipo': 'string',
                'observacao': 'E-mail da transportadora'
            },
            
            # 🎯 OPERAÇÃO
            'freteiro': {
                'campo_principal': 'freteiro',
                'termos_naturais': [
                    'freteiro', 'é freteiro', 'transportadora freteiro',
                    'autônomo', 'autonomo', 'pessoa física',
                    'pessoa fisica', 'pf'
                ],
                'tipo': 'boolean',
                'observacao': 'Indica se é freteiro (pessoa física)'
            },
            
            'ativo': {
                'campo_principal': 'ativo',
                'termos_naturais': [
                    'ativo', 'ativa', 'está ativo', 'esta ativo',
                    'status ativo', 'habilitado', 'habilitada'
                ],
                'tipo': 'boolean',
                'observacao': 'Indica se a transportadora está ativa'
            },
            
            # 🎯 CAMPOS ESPECÍFICOS
            'observacoes': {
                'campo_principal': 'observacoes',
                'termos_naturais': [
                    'observações', 'observacoes', 'obs', 'comentários',
                    'comentarios', 'notas', 'anotações', 'anotacoes'
                ],
                'tipo': 'string',
                'observacao': 'Observações sobre a transportadora'
            }
        } 