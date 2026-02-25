"""
Extrator específico para PDFs de Pedidos/Lotes de Compra do Assaí (Sendas)

Formato do PDF:
- Página 1: Header com dados do lote/pedido
  - Lote: XXXXX NACOM GOYA...
  - Pedido: XXXXXXX
  - Data Pedido: DD/MM/YYYY
  - Prev. Entrega: DD/MM/YYYY

- Páginas 2+: Produtos agrupados por código
  - Código e descrição do produto
  - Linhas por loja com: Número | Nome | Data | Qtd | Emb | Preço | Valor Total
  - Ex: 007 Santos    20/02/2026    3,000    30    144,4500    433,3500

Fluxo de conversão:
1. ProdutoDeParaSendas: codigo_sendas -> nosso_codigo
2. FilialDeParaSendas: numero_loja -> cnpj, uf
3. CadastroPalletizacao: nosso_codigo -> nome_produto
4. RegiaoTabelaRede: uf -> regiao (para validação de preço)
5. TabelaRede: (ASSAI, regiao, cod_produto) -> preco esperado
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import pdfplumber
from .base import PDFExtractor


class AssaiExtractor(PDFExtractor):
    """Extrator para formato de Pedidos/Lotes de Compra do Assaí (Sendas)"""

    def __init__(self):
        super().__init__()
        self.formato = "ASSAI_PEDIDO"
        self.depara_cache = {}  # Cache para conversões de código de produto
        self.filial_cache = {}  # Cache para conversões de filial
        self.produto_cache = {}  # Cache para dados de produto (nome)

    def extract(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extrai dados do PDF do Assaí/Sendas
        Retorna lista de dicionários com os dados extraídos, um por item/filial
        """
        all_data = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extrai header da primeira página
                header_info = self._extract_header(pdf.pages[0])

                # Processa todas as páginas para extrair produtos
                produtos_por_loja = self._extract_all_products(pdf)

                # Combina header com produtos
                for item in produtos_por_loja:
                    item_completo = {**header_info, **item}
                    if self.validate(item_completo):
                        all_data.append(item_completo)
                    else:
                        self.warnings.append(
                            f"Item inválido: {item.get('codigo', 'sem código')} - "
                            f"Loja: {item.get('numero_loja', 'sem loja')}"
                        )

        except Exception as e:
            import traceback
            self.errors.append(f"Erro ao processar PDF: {str(e)}")
            self.errors.append(traceback.format_exc())

        return all_data

    def _extract_header(self, page) -> Dict[str, Any]:
        """
        Extrai informações do cabeçalho da primeira página
        """
        header = {}
        text = page.extract_text() or ""

        # Número do Pedido - "Pedido:21046597" ou "Pedido: 21046597"
        pedido_match = re.search(r'Pedido:?\s*(\d+)', text)
        if pedido_match:
            header['numero_pedido'] = pedido_match.group(1)

        # Número do Lote - "Lote: 104093"
        lote_match = re.search(r'Lote:\s*(\d+)', text)
        if lote_match:
            header['numero_lote'] = lote_match.group(1)

        # Data do Pedido
        data_pedido_match = re.search(r'Data\s+Pedido:\s*(\d{2}/\d{2}/\d{4})', text)
        if data_pedido_match:
            header['data_pedido'] = data_pedido_match.group(1)

        # Previsão de Entrega
        prev_entrega_match = re.search(r'Prev\.\s*Entrega:\s*(\d{2}/\d{2}/\d{4})', text)
        if prev_entrega_match:
            header['previsao_entrega'] = prev_entrega_match.group(1)

        # Condição de Pagamento
        cond_pagto_match = re.search(r'Cond\.\s*Pagto:\s*(\d+)', text)
        if cond_pagto_match:
            header['prazo_pagamento'] = int(cond_pagto_match.group(1))

        # CNPJ do Fornecedor (nosso)
        cnpj_match = re.search(r'CNPJ:\s*([\d\.\-/]+)', text)
        if cnpj_match:
            header['cnpj_fornecedor'] = cnpj_match.group(1)

        # Fornecedor
        fornecedor_match = re.search(r'Fornecedor:\s*(\d+)([A-Z\s]+)', text)
        if fornecedor_match:
            header['cod_fornecedor'] = fornecedor_match.group(1)
            header['nome_fornecedor'] = fornecedor_match.group(2).strip()

        return header

    def _extract_all_products(self, pdf) -> List[Dict[str, Any]]:
        """
        Extrai todos os produtos e suas linhas de lojas de todas as páginas
        """
        items = []
        current_product = None
        current_product_desc = None

        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Verifica se é linha de cabeçalho de produto
                # Formato: "69354 COGUMELO CAMPO BELO INT SACHET 100G"
                # ou "91007 AZEITONA VDE CAMPO BELO C/C 500G"
                product_header = self._parse_product_header(line)
                if product_header:
                    current_product = product_header['codigo']
                    current_product_desc = product_header['descricao']
                    continue

                # Se temos um produto atual, verifica se é linha de loja
                if current_product:
                    loja_data = self._parse_loja_line(line)
                    if loja_data:
                        # Busca informações da filial pelo número
                        filial_info = self._get_filial_info(loja_data['numero_loja'])

                        # Busca nosso código via De-Para
                        depara = self._get_nosso_codigo(current_product)

                        # Busca nome do produto via CadastroPalletizacao
                        produto_info = self._get_produto_info(depara['nosso_codigo'])

                        item = {
                            # Dados do produto
                            'codigo': current_product,
                            'codigo_sendas': current_product,
                            'descricao': current_product_desc,
                            'descricao_sendas': current_product_desc,

                            # De-Para
                            'nosso_codigo': depara['nosso_codigo'],
                            'nossa_descricao': produto_info.get('nome_produto') or depara['nossa_descricao'],
                            'fator_conversao': depara['fator_conversao'],

                            # Dados da loja/filial
                            'numero_loja': loja_data['numero_loja'],
                            'nome_loja_pdf': loja_data['nome_loja'],
                            'cnpj_filial': filial_info.get('cnpj'),
                            'nome_cliente': filial_info.get('nome_filial') or loja_data['nome_loja'],
                            'cidade': filial_info.get('cidade'),
                            'uf': filial_info.get('uf'),
                            'estado': filial_info.get('uf'),

                            # Dados da linha
                            'data_entrega': loja_data['data_entrega'],
                            'quantidade': loja_data['quantidade'],
                            'embalagem': loja_data['embalagem'],
                            'valor_unitario': loja_data['valor_unitario'],
                            'valor_total': loja_data['valor_total'],
                        }

                        # Avisos se não encontrou De-Para ou Filial
                        if not item['nosso_codigo']:
                            self.warnings.append(
                                f"Código Sendas {current_product} não tem De-Para configurado"
                            )

                        if not item['cnpj_filial']:
                            self.warnings.append(
                                f"Loja {loja_data['numero_loja']} não tem De-Para de filial configurado"
                            )

                        items.append(item)

                # Verifica se é linha de totais (reset produto)
                if line.startswith('Totais:'):
                    current_product = None
                    current_product_desc = None

        return items

    def _parse_product_header(self, line: str) -> Optional[Dict[str, str]]:
        """
        Identifica e parseia linha de cabeçalho de produto
        Formato: "69354 COGUMELO CAMPO BELO INT SACHET 100G"
        """
        # Padrão: código numérico seguido de descrição em maiúsculas
        # O código pode ter 5-7 dígitos
        # [A-ZÀ-Ÿ] inclui maiúsculas acentuadas (Á, É, Í, Ó, Ú, Ã, Õ, Ç, etc.)
        # Inclui vírgula para pesos como "1,8KG"
        pattern = r'^(\d{5,7})\s+([A-ZÀ-Ÿ][A-ZÀ-Ÿ\s\./\-0-9,]+)$'
        match = re.match(pattern, line)

        if match:
            codigo = match.group(1)
            descricao = match.group(2).strip()

            # Verifica se não é uma linha de loja (que começa com número de 3 dígitos)
            # e tem uma estrutura diferente
            if len(codigo) >= 5:  # Códigos de produto têm 5+ dígitos
                return {
                    'codigo': codigo,
                    'descricao': descricao
                }

        return None

    def _parse_loja_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parseia linha de dados de uma loja
        Formato: "007 Santos    20/02/2026    3,000    30    144,4500    433,3500"
        Colunas: Número Loja | Nome | Data | Qtd | Emb | Preço Unit | Valor Total
        """
        # Padrão para linha de loja
        # Número de 3 dígitos, nome alfanumérico (incluindo acentos), data, números separados por espaços
        # [A-Za-zÀ-ÿ\s] inclui caracteres acentuados (Taboão, Taubaté, Tietê, etc.)
        pattern = r'^(\d{3})\s+([A-Za-zÀ-ÿ\s]+?)\s+(\d{2}/\d{2}/\d{4})\s+([\d\.,]+)\s+(\d+)\s+([\d\.,]+)\s+([\d\.,]+)$'
        match = re.match(pattern, line)

        if match:
            return {
                'numero_loja': match.group(1),
                'nome_loja': match.group(2).strip(),
                'data_entrega': match.group(3),
                'quantidade': self._parse_quantity(match.group(4)),
                'embalagem': int(match.group(5)),
                'valor_unitario': self.sanitize_decimal(match.group(6)),
                'valor_total': self.sanitize_decimal(match.group(7)),
            }

        return None

    def _parse_quantity(self, qty_str: str) -> int:
        """
        Converte quantidade no formato "3,000" ou "3.000" para inteiro 3
        """
        if not qty_str:
            return 0

        # Remove espaços
        qty_str = qty_str.strip()

        # Se tem vírgula como separador decimal (ex: "3,000" = 3)
        if ',' in qty_str:
            # Assume formato brasileiro onde vírgula é decimal
            qty_str = qty_str.split(',')[0]
        elif '.' in qty_str:
            # Verifica se é milhar ou decimal
            parts = qty_str.split('.')
            if len(parts[-1]) == 3:  # Ex: "3.000" = 3000 (milhar)
                qty_str = qty_str.replace('.', '')
            else:  # Ex: "3.5" = 3 (decimal)
                qty_str = parts[0]

        try:
            return int(qty_str)
        except ValueError:
            return 0

    def _get_filial_info(self, numero_loja: str) -> Dict[str, Any]:
        """
        Busca informações da filial pelo número
        Usa FilialDeParaSendas.obter_info_por_numero() ou busca manual
        """
        # Verifica cache primeiro
        if numero_loja in self.filial_cache:
            return self.filial_cache[numero_loja]

        result = {
            'cnpj': None,
            'nome_filial': None,
            'cidade': None,
            'uf': None
        }

        try:
            from app.portal.sendas.models import FilialDeParaSendas

            # Usa o novo método otimizado
            info = FilialDeParaSendas.obter_info_por_numero(numero_loja)

            if info:
                result = {
                    'cnpj': info.get('cnpj'),
                    'nome_filial': info.get('nome_filial'),
                    'cidade': info.get('cidade'),
                    'uf': info.get('uf')
                }

            # Adiciona ao cache
            self.filial_cache[numero_loja] = result

        except Exception as e:
            self.warnings.append(f"Erro ao buscar filial {numero_loja}: {e}")

        return result

    def _get_nosso_codigo(self, codigo_sendas: str) -> Dict[str, Any]:
        """
        Busca nosso código interno baseado no código do Sendas
        Usa cache para evitar múltiplas consultas ao banco
        """
        # Verifica cache primeiro
        if codigo_sendas in self.depara_cache:
            return self.depara_cache[codigo_sendas]

        result = {
            'nosso_codigo': None,
            'nossa_descricao': None,
            'fator_conversao': 1.0
        }

        try:
            from app.portal.sendas.models import ProdutoDeParaSendas
            from app import db

            # Busca no De-Para
            depara = ProdutoDeParaSendas.query.filter_by(
                codigo_sendas=codigo_sendas,
                ativo=True
            ).first()

            if depara:
                result = {
                    'nosso_codigo': depara.codigo_nosso,
                    'nossa_descricao': depara.descricao_nosso,
                    'fator_conversao': float(depara.fator_conversao) if depara.fator_conversao else 1.0
                }

            # Adiciona ao cache
            self.depara_cache[codigo_sendas] = result

        except Exception as e:
            self.warnings.append(f"Erro ao buscar De-Para para código {codigo_sendas}: {e}")

        return result

    def _get_produto_info(self, nosso_codigo: str) -> Dict[str, Any]:
        """
        Busca informações do produto no CadastroPalletizacao
        """
        if not nosso_codigo:
            return {}

        # Verifica cache primeiro
        if nosso_codigo in self.produto_cache:
            return self.produto_cache[nosso_codigo]

        result = {}

        try:
            from app.producao.models import CadastroPalletizacao
            from app import db

            produto = CadastroPalletizacao.query.filter_by(
                cod_produto=nosso_codigo,
                ativo=True
            ).first()

            if produto:
                result = {
                    'nome_produto': produto.nome_produto,
                    'palletizacao': produto.palletizacao,
                    'peso_bruto': produto.peso_bruto
                }

            # Adiciona ao cache
            self.produto_cache[nosso_codigo] = result

        except Exception as e:
            self.warnings.append(f"Erro ao buscar produto {nosso_codigo}: {e}")

        return result

    def validate(self, data: Dict[str, Any]) -> bool:
        """Valida os dados extraídos"""
        # Validações obrigatórias
        required = ['codigo', 'quantidade', 'valor_unitario']

        for field in required:
            if field not in data or data.get(field) is None:
                return False

        # Valida se quantidade é positiva
        if data.get('quantidade', 0) <= 0:
            return False

        # Valida se valor é positivo
        valor = data.get('valor_unitario', 0)
        if isinstance(valor, Decimal):
            valor = float(valor)
        if valor <= 0:
            return False

        return True

    def to_dataframe(self, data: List[Dict[str, Any]]):
        """Converte dados para DataFrame do pandas"""
        import pandas as pd

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Ordena colunas
        column_order = [
            'cnpj_filial', 'nome_cliente', 'cidade', 'uf',
            'numero_loja', 'nome_loja_pdf',
            'codigo', 'descricao', 'nosso_codigo', 'nossa_descricao',
            'quantidade', 'valor_unitario', 'valor_total',
            'data_entrega', 'numero_pedido', 'numero_lote'
        ]

        # Reordena apenas colunas que existem
        existing_cols = [col for col in column_order if col in df.columns]
        other_cols = [col for col in df.columns if col not in column_order]

        df = df[existing_cols + other_cols]

        return df
