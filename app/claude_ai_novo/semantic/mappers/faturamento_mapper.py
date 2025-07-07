"""
💰 FATURAMENTO MAPPER - Mapeamentos para Modelo RelatorioFaturamentoImportado
============================================================================

Mapper especializado para o modelo RelatorioFaturamentoImportado,
contendo campos críticos de faturamento e vendas.

CAMPO CRÍTICO: 'origem' = num_pedido (NÃO é localização!)

Campos mapeados:
- Identificação: numero_nf, origem (num_pedido)
- Cliente: nome_cliente, cnpj_cliente
- Valores: valor_total, valor_frete
- Logística: incoterm, transportadora
"""

from typing import Dict, Any
from .base_mapper import BaseMapper

class FaturamentoMapper(BaseMapper):
    """
    Mapper específico para o modelo RelatorioFaturamentoImportado.
    
    Responsável por mapear termos naturais para campos
    da tabela 'relatorio_faturamento_importado' no banco de dados.
    """
    
    def __init__(self):
        super().__init__('RelatorioFaturamentoImportado')
    
    def _criar_mapeamentos(self) -> Dict[str, Dict[str, Any]]:
        """
        Cria mapeamentos específicos para o modelo RelatorioFaturamentoImportado.
        
        Returns:
            Dict com mapeamentos de campos de RelatorioFaturamentoImportado
        """
        return {
            # 🔢 IDENTIFICAÇÃO
            'numero_nf': {
                'campo_principal': 'numero_nf',
                'termos_naturais': [
                    'nf', 'nota fiscal', 'numero da nf', 'número da nf',
                    'numero da nota', 'número da nota', 'nota',
                    'nf número', 'nf numero', 'numero nf'
                ],
                'tipo': 'string',
                'observacao': 'Número da nota fiscal'
            },
            
            # ⚠️ CAMPO CRÍTICO - ORIGEM = NUM_PEDIDO
            'origem': {
                'campo_principal': 'origem',
                'termos_naturais': [
                    'pedido', 'número do pedido', 'numero do pedido',
                    'num pedido', 'nº pedido', 'pedido número',
                    'pedido numero', 'código do pedido', 'id do pedido',
                    'origem do pedido', 'num de pedido', 'numero de pedido'
                ],
                'tipo': 'string',
                'observacao': 'CRÍTICO: origem = num_pedido (relacionamento essencial, NÃO é localização!)'
            },
            
            # 🏢 CLIENTE
            'nome_cliente': {
                'campo_principal': 'nome_cliente',
                'termos_naturais': [
                    'cliente', 'nome do cliente', 'nome cliente',
                    'razão social', 'razao social', 'empresa',
                    'cliente nome', 'razão social do cliente'
                ],
                'tipo': 'string',
                'observacao': 'Nome/Razão social do cliente'
            },
            
            'cnpj_cliente': {
                'campo_principal': 'cnpj_cliente',
                'termos_naturais': [
                    'cnpj', 'cnpj do cliente', 'cnpj cliente',
                    'documento', 'documento do cliente', 'cpf cnpj'
                ],
                'tipo': 'string',
                'observacao': 'CNPJ do cliente'
            },
            
            # 💰 VALORES
            'valor_total': {
                'campo_principal': 'valor_total',
                'termos_naturais': [
                    'valor total', 'valor da nf', 'valor da nota',
                    'valor nota fiscal', 'valor da nota fiscal',
                    'preço total', 'preco total', 'montante',
                    'valor faturado', 'faturamento'
                ],
                'tipo': 'decimal',
                'observacao': 'Valor total da nota fiscal em reais'
            },
            
            'valor_frete': {
                'campo_principal': 'valor_frete',
                'termos_naturais': [
                    'frete', 'valor do frete', 'valor frete',
                    'custo do frete', 'custo frete', 'preço do frete',
                    'preco do frete', 'valor transporte'
                ],
                'tipo': 'decimal',
                'observacao': 'Valor do frete em reais'
            },
            
            # 📅 DATAS
            'data_fatura': {
                'campo_principal': 'data_fatura',
                'termos_naturais': [
                    'data da fatura', 'data fatura', 'data da nf',
                    'data da nota', 'data nota fiscal', 'data emissão',
                    'data emissao', 'quando foi faturado'
                ],
                'tipo': 'datetime',
                'observacao': 'Data de emissão da nota fiscal'
            },
            
            'data_vencimento': {
                'campo_principal': 'data_vencimento',
                'termos_naturais': [
                    'vencimento', 'data vencimento', 'data de vencimento',
                    'vence em', 'prazo de pagamento', 'quando vence'
                ],
                'tipo': 'datetime',
                'observacao': 'Data de vencimento da nota fiscal'
            },
            
            # 🚛 LOGÍSTICA
            'incoterm': {
                'campo_principal': 'incoterm',
                'termos_naturais': [
                    'incoterm', 'fob', 'cif', 'tipo de frete',
                    'modalidade de frete', 'responsabilidade frete',
                    'quem paga o frete', 'frete por conta'
                ],
                'tipo': 'string',
                'observacao': 'Incoterm da operação (FOB, CIF, etc.)'
            },
            
            'transportadora': {
                'campo_principal': 'transportadora',
                'termos_naturais': [
                    'transportadora', 'nome da transportadora',
                    'empresa transportadora', 'quem entregou',
                    'responsável pela entrega', 'responsavel pela entrega'
                ],
                'tipo': 'string',
                'observacao': 'Nome da transportadora responsável'
            },
            
            # 🏠 LOCALIZAÇÃO
            'cidade': {
                'campo_principal': 'cidade',
                'termos_naturais': [
                    'cidade', 'cidade destino', 'cidade de entrega',
                    'municipio', 'município', 'localidade'
                ],
                'tipo': 'string',
                'observacao': 'Cidade de destino'
            },
            
            'uf': {
                'campo_principal': 'uf',
                'termos_naturais': [
                    'uf', 'estado', 'uf destino', 'estado destino',
                    'uf de entrega', 'estado de entrega'
                ],
                'tipo': 'string',
                'observacao': 'Estado de destino'
            },
            
            'endereco': {
                'campo_principal': 'endereco',
                'termos_naturais': [
                    'endereço', 'endereco', 'endereço de entrega',
                    'endereco de entrega', 'rua', 'logradouro'
                ],
                'tipo': 'string',
                'observacao': 'Endereço de entrega'
            },
            
            # 📦 PRODUTOS
            'peso': {
                'campo_principal': 'peso',
                'termos_naturais': [
                    'peso', 'peso da nota', 'peso total',
                    'peso bruto', 'peso líquido', 'peso liquido',
                    'quantos kg', 'quilos', 'quilogramas'
                ],
                'tipo': 'decimal',
                'observacao': 'Peso total da nota fiscal em quilogramas'
            },
            
            'volumes': {
                'campo_principal': 'volumes',
                'termos_naturais': [
                    'volumes', 'quantidade de volumes', 'qtd volumes',
                    'número de volumes', 'numero de volumes',
                    'quantos volumes', 'qtd de itens'
                ],
                'tipo': 'integer',
                'observacao': 'Quantidade de volumes da nota fiscal'
            },
            
            # 📊 STATUS
            'status': {
                'campo_principal': 'status',
                'termos_naturais': [
                    'status', 'status da nf', 'situação da nota',
                    'situacao da nota', 'como está a nota',
                    'como esta a nota', 'status da fatura'
                ],
                'tipo': 'string',
                'observacao': 'Status da nota fiscal'
            },
            
            # 🎯 CAMPOS ESPECÍFICOS
            'observacoes': {
                'campo_principal': 'observacoes',
                'termos_naturais': [
                    'observações', 'observacoes', 'obs', 'comentários',
                    'comentarios', 'notas', 'anotações', 'anotacoes'
                ],
                'tipo': 'string',
                'observacao': 'Observações da nota fiscal'
            },
            
            'vendedor': {
                'campo_principal': 'vendedor',
                'termos_naturais': [
                    'vendedor', 'nome do vendedor', 'vendedor responsável',
                    'vendedor responsavel', 'quem vendeu', 'representante'
                ],
                'tipo': 'string',
                'observacao': 'Nome do vendedor responsável'
            },
            
            'comissao': {
                'campo_principal': 'comissao',
                'termos_naturais': [
                    'comissão', 'comissao', 'comissão do vendedor',
                    'comissao do vendedor', 'percentual comissão',
                    'percentual comissao', '% comissão'
                ],
                'tipo': 'decimal',
                'observacao': 'Comissão do vendedor'
            }
        } 