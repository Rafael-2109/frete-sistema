"""
Extrator específico para PDFs de Pedido de Compra do Atacadão
Formato: Texto matricial (diferente da Proposta que é tabular)

Formato do PDF:
- Header: ATACADAO S.A., PEDIDO DE COMPRA
- Fornecedor: 61724241/0003-30 NACOM GOYA...
- Local de Entrega: 93209765/0599-44 SP Cep: 15014-050
- Pedido EDI: N 111988186
- Produtos: 35642/114 CXA 0001X0006X2KG  15  199,48
"""

import re
from typing import Dict, List, Any, Optional
from decimal import Decimal
from .base import PDFExtractor


class AtacadaoPedidoExtractor(PDFExtractor):
    """Extrator para formato de Pedido de Compra do Atacadão (matricial)"""

    def __init__(self):
        super().__init__()
        self.formato = "ATACADAO_PEDIDO"
        self.depara_cache = {}

    def extract(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extrai dados do PDF de Pedido do Atacadão
        """
        # Extrai texto do PDF
        text = self.extract_text_with_pdfplumber(pdf_path)

        if not text:
            text = self.extract_text_with_pypdf2(pdf_path)

        if not text:
            self.errors.append("Não foi possível extrair texto do PDF")
            return []

        # Divide o texto por filiais (Local de Entrega)
        filiais = self._split_por_filial(text)

        all_data = []
        for filial_text in filiais:
            filial_data = self._extract_filial_data(filial_text)
            if filial_data:
                all_data.extend(filial_data)

        return all_data

    def _split_por_filial(self, text: str) -> List[str]:
        """
        Divide o texto em seções por Local de Entrega
        O PDF pode ter múltiplas filiais, cada uma começa com "Local de Entrega:"
        """
        # Padrão para encontrar Local de Entrega
        # Local de Entrega: 93209765/0599-44 SP Cep: 15014-050
        pattern = r'Local\s+de\s+Entrega:'

        # Encontra todas as posições
        matches = list(re.finditer(pattern, text, re.IGNORECASE))

        if not matches:
            return [text]

        sections = []
        for i, match in enumerate(matches):
            start = match.start()
            # Pega até o próximo Local de Entrega ou fim do texto
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append(text[start:end])

        return sections

    def _extract_filial_data(self, text: str) -> List[Dict[str, Any]]:
        """Extrai dados de uma filial específica"""
        data = []

        # Extrai informações do cabeçalho
        header_info = self._extract_header(text)
        if not header_info:
            return data

        # Busca dados do cliente se tiver CNPJ
        if 'cnpj_filial' in header_info:
            dados_cliente = self._get_dados_cliente(header_info['cnpj_filial'])
            header_info.update(dados_cliente)

        # Extrai linhas de produtos
        produtos = self._extract_produtos(text)

        # Combina header com cada produto
        for produto in produtos:
            item = {**header_info, **produto}
            if self.validate(item):
                data.append(item)
            else:
                self.warnings.append(f"Item inválido: {produto.get('codigo', 'sem código')}")

        return data

    def _extract_header(self, text: str) -> Dict[str, Any]:
        """Extrai informações do cabeçalho do pedido"""
        header = {}

        # CNPJ da filial (Local de Entrega) - formato: 93209765/0599-44
        # O PDF tem formato multi-linha:
        # Local de Entrega: 93209765/0599-44
        # R SILVA JARDIM 4141
        # SAO JOSE DO RIO PRETO   SP   Cep: 15014-050

        # Primeiro extrai o CNPJ da linha "Local de Entrega:"
        cnpj_pattern = r'Local\s+de\s+Entrega:\s*(\d{8}/\d{4}-\d{2})'
        cnpj_match = re.search(cnpj_pattern, text, re.IGNORECASE)
        if cnpj_match:
            cnpj_raw = cnpj_match.group(1)
            header['cnpj_filial'] = self._format_cnpj(cnpj_raw)

        # Depois busca UF e CEP em qualquer linha próxima (formato: CIDADE   UF   Cep: XXXXX-XXX)
        uf_cep_pattern = r'([A-Z\s]+)\s+([A-Z]{2})\s+Cep:\s*(\d{5}-?\d{3})'
        uf_cep_match = re.search(uf_cep_pattern, text, re.IGNORECASE)
        if uf_cep_match:
            header['cidade'] = uf_cep_match.group(1).strip()
            header['uf'] = uf_cep_match.group(2).upper()
            header['cep'] = uf_cep_match.group(3)
            header['local_entrega'] = f"{header.get('cidade', '')} - {header.get('uf', '')}"

        # Endereço (linha entre Local de Entrega e Cidade)
        endereco_pattern = r'Local\s+de\s+Entrega:[^\n]+\n\|?\s*([^\n|]+)'
        endereco_match = re.search(endereco_pattern, text, re.IGNORECASE)
        if endereco_match:
            endereco = endereco_match.group(1).strip()
            # Remove prefixos como "R " que podem ter sido capturados
            if not endereco.startswith('Desc') and not endereco.startswith('Observ'):
                header['endereco'] = endereco

        # Número do Pedido EDI
        # Padrão: Pedido EDI.: N 111988186
        pedido_pattern = r'Pedido\s+EDI\.?:?\s*N?\s*(\d+)'
        pedido_match = re.search(pedido_pattern, text, re.IGNORECASE)
        if pedido_match:
            header['numero_pedido'] = pedido_match.group(1)
            header['pedido_edi'] = pedido_match.group(1)

        # Condição de Pagamento (em dias)
        # Padrão: Condicoes de Pagto (em dias)\n60
        pagto_pattern = r'Condicoes\s+de\s+Pagto\s+\(em\s+dias\)\s*\n?\s*(\d+)'
        pagto_match = re.search(pagto_pattern, text, re.IGNORECASE)
        if pagto_match:
            header['prazo_pagamento'] = int(pagto_match.group(1))

        # Data do documento (geralmente no topo)
        data_pattern = r'(\d{2}/\d{2}/\d{2})\s+\d{2}:\d{2}'
        data_match = re.search(data_pattern, text)
        if data_match:
            header['data_pedido'] = data_match.group(1)

        # Número na página (PG: X)
        pg_pattern = r'PG:\s*(\d+)'
        pg_match = re.search(pg_pattern, text)
        if pg_match:
            header['pagina'] = int(pg_match.group(1))

        # Número do comprador (Numero: XXXXX)
        numero_pattern = r'Numero:\s*(\d+)'
        numero_match = re.search(numero_pattern, text)
        if numero_match:
            header['numero_comprador'] = numero_match.group(1)

        # Frete: CIF ou FOB
        frete_pattern = r'Frete:\s*(CIF|FOB)'
        frete_match = re.search(frete_pattern, text, re.IGNORECASE)
        if frete_match:
            header['tipo_frete'] = frete_match.group(1).upper()

        return header

    def _format_cnpj(self, cnpj: str) -> str:
        """
        Formata CNPJ para padrão XX.XXX.XXX/XXXX-XX

        Args:
            cnpj: CNPJ no formato 93209765/0599-44

        Returns:
            CNPJ formatado: 93.209.765/0599-44
        """
        # Remove caracteres não numéricos
        cnpj_limpo = re.sub(r'\D', '', cnpj)

        if len(cnpj_limpo) == 14:
            return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"

        # Se já tem alguma formatação, retorna como está
        return cnpj

    def _extract_produtos(self, text: str) -> List[Dict[str, Any]]:
        """
        Extrai linhas de produtos do formato matricial do Atacadão

        Formato REAL do PDF (baseado no documento):
        Linha 1: DESCRICAO                    DD/MM    QTD    PRECO    0,  0,00  ...
        Linha 2: CODIGO/SEQ CXA BARCODE       EAN      Pr Final N

        Exemplo:
        | AZEITONA VERDE CAMPO BELO BALDE    26/08    15    199,48    0,  0,00 ...
        | 35642/114 CXA 0001X0006X2KG        17898075641781 Pr Final N
        """
        produtos = []
        lines = text.split('\n')

        i = 0
        while i < len(lines) - 1:
            line = lines[i].strip()
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

            # Verifica se a próxima linha contém código de produto
            # Formato: XXXXX/YYY CXA ...
            codigo_match = re.match(r'^\|?\s*(\d{5,6})/(\d+)\s+CXA\s+(\S+)', next_line)

            if codigo_match:
                codigo = codigo_match.group(1)
                seq = codigo_match.group(2)
                barcode = codigo_match.group(3)

                # Extrai dados da linha atual (descrição + valores)
                # Formato: | DESCRICAO    DD/MM    QTD    PRECO    ...
                # Remove pipes e espaços iniciais
                linha_dados = re.sub(r'^\|?\s*', '', line)

                # Padrão para extrair: DESCRICAO  DATA  QTD  PRECO
                # Exemplo: "AZEITONA VERDE CAMPO BELO BALDE    26/08    15    199,48"
                dados_match = re.match(
                    r'^([A-Z][A-Z\s\./\-\(\)]+?)\s+(\d{2}/\d{2})\s+(\d+)\s+([\d,\.]+)',
                    linha_dados
                )

                if dados_match:
                    descricao = dados_match.group(1).strip()
                    data_entrega = dados_match.group(2)
                    quantidade = self.sanitize_quantity(dados_match.group(3))
                    valor_unitario = self.sanitize_decimal(dados_match.group(4))

                    if quantidade > 0 and float(valor_unitario) > 0:
                        produto = {
                            'codigo': codigo,
                            'codigo_completo': f"{codigo}/{seq}",
                            'descricao': descricao,
                            'barcode': barcode,
                            'data_entrega': data_entrega,
                            'quantidade': quantidade,
                            'valor_unitario': valor_unitario,
                            'valor_total': quantidade * valor_unitario
                        }

                        # Busca De-Para
                        depara = self._get_nosso_codigo(codigo)
                        produto['nosso_codigo'] = depara['nosso_codigo']
                        produto['nossa_descricao'] = depara['nossa_descricao']
                        produto['fator_conversao'] = depara['fator_conversao']

                        if not produto['nosso_codigo']:
                            self.warnings.append(
                                f"Código Atacadão {codigo} não tem De-Para configurado"
                            )

                        produtos.append(produto)

                        # Pula a linha do código
                        i += 1

            i += 1

        # Se não encontrou com o método acima, tenta regex alternativo
        if not produtos:
            produtos = self._extract_produtos_regex_alternativo(text)

        return produtos

    def _extract_produtos_regex_alternativo(self, text: str) -> List[Dict[str, Any]]:
        """
        Método alternativo para extrair produtos quando o formato principal falha
        Busca blocos de texto que contenham código/seq e valores
        """
        produtos = []

        # Padrão que captura blocos completos de produto
        # Busca linhas que terminam com "Pr Final N" ou similar
        blocos = re.split(r'(?=\|?\s*[A-Z][A-Z\s\./\-]+\s+\d{2}/\d{2})', text)

        for bloco in blocos:
            if not bloco.strip():
                continue

            # Busca código no bloco
            codigo_match = re.search(r'(\d{5,6})/(\d+)\s+CXA\s+(\S+)', bloco)
            if not codigo_match:
                continue

            codigo = codigo_match.group(1)
            seq = codigo_match.group(2)
            barcode = codigo_match.group(3)

            # Busca descrição e valores no início do bloco
            dados_match = re.search(
                r'([A-Z][A-Z\s\./\-\(\)]+?)\s+(\d{2}/\d{2})\s+(\d+)\s+([\d,\.]+)',
                bloco
            )

            if dados_match:
                descricao = dados_match.group(1).strip()
                data_entrega = dados_match.group(2)
                quantidade = self.sanitize_quantity(dados_match.group(3))
                valor_unitario = self.sanitize_decimal(dados_match.group(4))

                if quantidade > 0 and float(valor_unitario) > 0:
                    produto = {
                        'codigo': codigo,
                        'codigo_completo': f"{codigo}/{seq}",
                        'descricao': descricao,
                        'barcode': barcode,
                        'data_entrega': data_entrega,
                        'quantidade': quantidade,
                        'valor_unitario': valor_unitario,
                        'valor_total': quantidade * valor_unitario
                    }

                    # Busca De-Para
                    depara = self._get_nosso_codigo(codigo)
                    produto['nosso_codigo'] = depara['nosso_codigo']
                    produto['nossa_descricao'] = depara['nossa_descricao']
                    produto['fator_conversao'] = depara['fator_conversao']

                    produtos.append(produto)

        return produtos

    def _get_dados_cliente(self, cnpj: str) -> Dict[str, Any]:
        """Busca dados do cliente"""
        try:
            from app.faturamento.models import RelatorioFaturamentoImportado
            from app import db

            cliente = db.session.query(RelatorioFaturamentoImportado).filter(
                RelatorioFaturamentoImportado.cnpj_cliente == cnpj,
                RelatorioFaturamentoImportado.ativo == True
            ).order_by(RelatorioFaturamentoImportado.criado_em.desc()).first()

            if cliente:
                return {
                    'nome_cliente': cliente.nome_cliente,
                    'municipio': cliente.municipio,
                    'estado': cliente.estado,
                    'codigo_ibge': cliente.codigo_ibge
                }

        except Exception as e:
            self.warnings.append(f"Erro ao buscar dados do cliente {cnpj}: {e}")

        return {
            'nome_cliente': None,
            'municipio': None,
            'estado': None,
            'codigo_ibge': None
        }

    def _get_nosso_codigo(self, codigo_atacadao: str) -> Dict[str, Any]:
        """
        Busca nosso código via De-Para

        IMPORTANTE: Normaliza códigos removendo zeros à esquerda para garantir
        compatibilidade entre formatos (ex: '082545' vs '82545')
        """
        if codigo_atacadao in self.depara_cache:
            return self.depara_cache[codigo_atacadao]

        try:
            from app.portal.atacadao.models import ProdutoDeParaAtacadao
            from app import db

            # Normaliza código removendo zeros à esquerda
            codigo_normalizado = codigo_atacadao.lstrip('0') if codigo_atacadao else ''

            # Busca no banco - primeiro tenta código normalizado (sem zeros à esquerda)
            depara = db.session.query(ProdutoDeParaAtacadao).filter(
                ProdutoDeParaAtacadao.codigo_atacadao == codigo_normalizado,
                ProdutoDeParaAtacadao.ativo == True
            ).first()

            # Se não encontrou, tenta com código original (com zeros)
            if not depara and codigo_normalizado != codigo_atacadao:
                depara = db.session.query(ProdutoDeParaAtacadao).filter(
                    ProdutoDeParaAtacadao.codigo_atacadao == codigo_atacadao,
                    ProdutoDeParaAtacadao.ativo == True
                ).first()

            if depara:
                result = {
                    'nosso_codigo': depara.codigo_nosso,
                    'nossa_descricao': depara.descricao_nosso,
                    'fator_conversao': float(depara.fator_conversao) if depara.fator_conversao else 1.0
                }
            else:
                result = {
                    'nosso_codigo': None,
                    'nossa_descricao': None,
                    'fator_conversao': 1.0
                }

            self.depara_cache[codigo_atacadao] = result
            return result

        except Exception as e:
            self.warnings.append(f"Erro ao buscar De-Para para código {codigo_atacadao}: {e}")
            return {
                'nosso_codigo': None,
                'nossa_descricao': None,
                'fator_conversao': 1.0
            }

    def validate(self, data: Dict[str, Any]) -> bool:
        """Valida os dados extraídos"""
        required = ['codigo', 'quantidade', 'valor_unitario']

        for field in required:
            if field not in data or not data[field]:
                return False

        if data.get('quantidade', 0) <= 0:
            return False

        if float(data.get('valor_unitario', 0)) <= 0:
            return False

        return True

    def to_dataframe(self, data: List[Dict[str, Any]]):
        """Converte dados para DataFrame"""
        import pandas as pd

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        column_order = [
            'cnpj_filial', 'local_entrega', 'cidade', 'uf',
            'codigo', 'descricao', 'quantidade', 'valor_unitario', 'valor_total',
            'data_entrega', 'numero_pedido', 'pedido_edi', 'prazo_pagamento'
        ]

        existing_cols = [col for col in column_order if col in df.columns]
        other_cols = [col for col in df.columns if col not in column_order]

        return df[existing_cols + other_cols]
