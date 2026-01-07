"""
Processador principal para pedidos em PDF de redes de atacarejo
Coordena extração, validação e inserção no banco

Fluxo:
1. Upload PDF → Armazena no S3
2. Identificador → Detecta Rede + Tipo
3. Extrator específico → Extrai dados
4. Conversão De-Para → Código Nacom
5. Validação de preços → vs TabelaRede
6. Revisão/Aprovação → Interface
7. Inserção Odoo → sale.order via XML-RPC
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from decimal import Decimal

from .atacadao import AtacadaoExtractor
from .atacadao_pedido import AtacadaoPedidoExtractor
from .assai import AssaiExtractor
from .identificador import identificar_documento, IdentificacaoDocumento


class PedidoProcessor:
    """Processador principal de pedidos de redes de atacarejo"""

    # Mapeamento de formatos para extratores
    # Chave: REDE_TIPO (ex: ATACADAO_PROPOSTA)
    EXTRACTORS = {
        # Atacadão
        'atacadao_proposta': AtacadaoExtractor,
        'atacadao_pedido': AtacadaoPedidoExtractor,
        # Aliases para compatibilidade
        'atacadao': AtacadaoExtractor,  # Default para proposta
        'atacadão': AtacadaoExtractor,
        # Assaí/Sendas
        'assai_pedido': AssaiExtractor,
        'assai_proposta': AssaiExtractor,  # Usa mesmo extractor
        'assai': AssaiExtractor,  # Default
        'sendas': AssaiExtractor,  # Alias
        'sendas_pedido': AssaiExtractor,
        # Futuros extratores
        # 'tenda_proposta': TendaPropostaExtractor,
        # 'tenda_pedido': TendaPedidoExtractor,
    }

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.processed_count = 0
        self.failed_count = 0
        self.identificacao: Optional[IdentificacaoDocumento] = None

    def process_file(self,
                     file_path: str,
                     formato: str = 'auto',
                     validate: bool = True) -> Dict[str, Any]:
        """
        Processa um arquivo PDF de rede de atacarejo

        Args:
            file_path: Caminho do arquivo PDF
            formato: Formato do PDF ('atacadao_proposta', 'atacadao_pedido', etc) ou 'auto' para detectar
            validate: Se deve validar os dados

        Returns:
            Dict com resultado do processamento incluindo identificação
        """
        result = {
            'success': False,
            'data': [],
            'errors': [],
            'warnings': [],
            'summary': {},
            'identificacao': None  # Novo: informações de identificação
        }

        try:
            # Detecta formato se necessário
            if formato == 'auto':
                self.identificacao = identificar_documento(file_path)
                result['identificacao'] = {
                    'rede': self.identificacao.rede,
                    'tipo': self.identificacao.tipo,
                    'numero_documento': self.identificacao.numero_documento,
                    'confianca': self.identificacao.confianca
                }

                # Monta chave do extrator
                formato = f"{self.identificacao.rede.lower()}_{self.identificacao.tipo.lower()}"

                if self.identificacao.rede == 'DESCONHECIDA':
                    result['errors'].append("Não foi possível identificar a rede do documento")
                    return result

                if self.identificacao.tipo == 'DESCONHECIDO':
                    result['errors'].append("Não foi possível identificar o tipo do documento (Proposta/Pedido)")
                    return result

            # Obtém extrator apropriado
            extractor_class = self.EXTRACTORS.get(formato.lower())
            if not extractor_class:
                # Tenta fallback para formato sem tipo
                formato_base = formato.split('_')[0] if '_' in formato else formato
                extractor_class = self.EXTRACTORS.get(formato_base.lower())

            if not extractor_class:
                result['errors'].append(f"Formato '{formato}' não suportado")
                return result

            # Extrai dados
            extractor = extractor_class()
            data = extractor.extract(file_path)

            if not data:
                result['errors'].append("Nenhum dado foi extraído do PDF")
                result['errors'].extend(extractor.errors)
                return result

            # Valida dados se necessário
            if validate:
                data = self._validate_data(data)

            # Prepara resultado
            result['success'] = True
            result['data'] = data
            result['errors'] = extractor.errors
            result['warnings'] = extractor.warnings
            result['summary'] = self._generate_summary(data)

            # Adiciona informações de identificação ao summary
            if self.identificacao:
                result['summary']['rede'] = self.identificacao.rede
                result['summary']['tipo_documento'] = self.identificacao.tipo
                result['summary']['numero_documento'] = self.identificacao.numero_documento

        except Exception as e:
            import traceback
            result['errors'].append(f"Erro ao processar arquivo: {str(e)}")
            result['traceback'] = traceback.format_exc()

        return result

    def _validate_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Valida e limpa os dados extraídos
        """
        validated = []

        for item in data:
            # Remove valores None
            item = {k: v for k, v in item.items() if v is not None}

            # Validações básicas
            if not item.get('codigo'):
                self.warnings.append(f"Item sem código: {item.get('descricao', 'sem descrição')}")
                continue

            if item.get('quantidade', 0) <= 0:
                self.warnings.append(f"Quantidade inválida para {item['codigo']}")
                continue

            valor_unitario = item.get('valor_unitario', 0)
            if isinstance(valor_unitario, Decimal):
                valor_unitario = float(valor_unitario)
            if valor_unitario <= 0:
                self.warnings.append(f"Valor inválido para {item['codigo']}")
                continue

            validated.append(item)

        return validated

    def _generate_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Gera resumo dos dados processados agrupados por CNPJ
        """
        try:
            if not data:
                return {}

            df = pd.DataFrame(data)

            summary = {
                'total_itens': len(data),
                'total_filiais': df['cnpj_filial'].nunique() if 'cnpj_filial' in df else 0,
                'total_produtos': df['codigo'].nunique() if 'codigo' in df else 0,
                'quantidade_total': int(df['quantidade'].sum()) if 'quantidade' in df else 0,
                'valor_total': float(df['valor_total'].sum()) if 'valor_total' in df else 0.0
            }

            # Conta itens sem De-Para
            if 'nosso_codigo' in df.columns:
                sem_depara = df['nosso_codigo'].isna().sum()
                summary['sem_depara'] = int(sem_depara)
                summary['com_depara'] = len(df) - int(sem_depara)

            # Resumo por filial com dados completos do cliente
            if 'cnpj_filial' in df:
                summary['por_filial'] = []
                for cnpj in df['cnpj_filial'].unique():
                    # Sanitiza CNPJ - se for NaN, converte para None
                    if pd.isna(cnpj):
                        cnpj = None
                        # Filtra itens sem CNPJ
                        filial_df = df[df['cnpj_filial'].isna()]
                    else:
                        filial_df = df[df['cnpj_filial'] == cnpj]

                    # Pega os dados do primeiro item
                    if not filial_df.empty:
                        primeiro_item = filial_df.iloc[0].to_dict()
                        # Sanitiza valores NaN no primeiro_item também
                        primeiro_item = {k: (None if pd.isna(v) else v) for k, v in primeiro_item.items()}
                    else:
                        primeiro_item = {}

                    # Converte produtos para garantir que Decimals sejam float
                    produtos_list = []
                    for produto in filial_df.to_dict('records'):
                        produto_clean = {}
                        for k, v in produto.items():
                            if hasattr(v, 'quantize'):  # É Decimal
                                produto_clean[k] = float(v)
                            elif pd.isna(v):  # É NaN/None
                                produto_clean[k] = None
                            else:
                                produto_clean[k] = v
                        produtos_list.append(produto_clean)

                    # Conta itens sem De-Para nesta filial
                    sem_depara_filial = filial_df['nosso_codigo'].isna().sum() if 'nosso_codigo' in filial_df.columns else 0

                    # Busca número do pedido (Atacadão: por filial, Assaí: mesmo para todas)
                    numero_pedido = (
                        primeiro_item.get('numero_pedido') or      # Assaí e Atacadão Pedido
                        primeiro_item.get('pedido_edi') or         # Atacadão Pedido
                        primeiro_item.get('proposta') or           # Atacadão Proposta
                        primeiro_item.get('numero_comprador') or   # Fallback
                        ''
                    )

                    filial_info = {
                        'cnpj': cnpj,
                        'numero_loja': primeiro_item.get('numero_loja', ''),  # Número da filial (ex: "007")
                        'numero_pedido_cliente': numero_pedido,  # Número do pedido/proposta
                        'nome_cliente': primeiro_item.get('nome_cliente', ''),
                        'local': primeiro_item.get('local_entrega', ''),
                        'municipio': primeiro_item.get('municipio', '') or primeiro_item.get('cidade', ''),
                        'estado': primeiro_item.get('estado', '') or primeiro_item.get('uf', ''),
                        'itens': len(filial_df),
                        'sem_depara': int(sem_depara_filial),
                        'quantidade': int(filial_df['quantidade'].sum()) if 'quantidade' in filial_df else 0,
                        'valor': float(filial_df['valor_total'].sum()) if 'valor_total' in filial_df else 0.0,
                        'produtos': produtos_list
                    }
                    summary['por_filial'].append(filial_info)

            return summary
        except Exception as e:
            import traceback
            print(f"Erro ao gerar summary: {e}")
            print(traceback.format_exc())
            return {
                'total_itens': len(data) if data else 0,
                'total_filiais': 0,
                'total_produtos': 0,
                'quantidade_total': 0,
                'valor_total': 0.0,
                'por_filial': [],
                'error': str(e)
            }

    def export_to_excel(self, data: List[Dict[str, Any]], output_path: str):
        """
        Exporta dados para Excel
        """
        if not data:
            raise ValueError("Sem dados para exportar")

        df = pd.DataFrame(data)

        # Formata colunas monetárias
        if 'valor_unitario' in df.columns:
            df['valor_unitario'] = df['valor_unitario'].apply(
                lambda x: f"R$ {float(x):,.2f}" if x else "R$ 0,00"
            )
        if 'valor_total' in df.columns:
            df['valor_total'] = df['valor_total'].apply(
                lambda x: f"R$ {float(x):,.2f}" if x else "R$ 0,00"
            )

        # Salva Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Pedidos', index=False)

            # Ajusta largura das colunas
            worksheet = writer.sheets['Pedidos']
            from openpyxl.utils import get_column_letter

            for idx, column in enumerate(df.columns, 1):
                column_length = max(df[column].astype(str).map(len).max(), len(column))
                column_letter = get_column_letter(idx)
                worksheet.column_dimensions[column_letter].width = min(column_length + 2, 50)

        return output_path

    def export_to_csv(self, data: List[Dict[str, Any]], output_path: str):
        """
        Exporta dados para CSV
        """
        if not data:
            raise ValueError("Sem dados para exportar")

        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        return output_path
