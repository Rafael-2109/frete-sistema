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
        Divide o texto em seções por filial usando a paginação "PG: X".

        IMPORTANTE: O PDF do Atacadão usa paginação por filial:
        - Quando "PG: 1" aparece, é o início de uma nova filial
        - Uma filial pode ter múltiplas páginas (PG: 1, PG: 2, PG: 3...)
        - Quando PG volta para 1, é uma nova filial

        Estrutura do PDF:
            [PG: 1] Filial JACAREI - Numero: 322506 - página 1 de 3
            [PG: 2] Filial JACAREI - continuação
            [PG: 3] Filial JACAREI - continuação
            [PG: 1] Filial SAO PAULO - Numero: 322507 - página 1 de 1
            [PG: 1] Filial RIBEIRAO PRETO - Numero: 322508 - página 1 de 1
        """
        # Encontra todas as ocorrências de "PG: X" (paginação)
        # Padrão: "PG: 1", "PG: 2", etc.
        pg_pattern = r'PG:\s*(\d+)'
        pg_matches = list(re.finditer(pg_pattern, text, re.IGNORECASE))

        if not pg_matches:
            # Fallback: se não encontrar paginação, retorna texto completo
            return [text]

        # Encontra onde cada "PG: 1" aparece (início de nova filial)
        pg1_positions = []
        for match in pg_matches:
            page_num = int(match.group(1))
            if page_num == 1:
                pg1_positions.append(match.start())

        if not pg1_positions:
            return [text]

        # Cria seções baseadas nas posições de "PG: 1"
        sections = []
        for i, start_pos in enumerate(pg1_positions):
            # O fim é o início da próxima "PG: 1" ou o fim do texto
            if i + 1 < len(pg1_positions):
                end_pos = pg1_positions[i + 1]
            else:
                end_pos = len(text)

            section = text[start_pos:end_pos]
            if section.strip():
                sections.append(section)

        return sections if sections else [text]

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

            # Atualiza local_entrega com dados do cliente (Odoo) se disponíveis
            if dados_cliente.get('municipio') or dados_cliente.get('estado'):
                cidade = dados_cliente.get('municipio') or header_info.get('cidade', '')
                uf = dados_cliente.get('estado') or header_info.get('uf', '')
                header_info['local_entrega'] = f"{cidade} - {uf}".strip(' -')

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
        """
        Busca dados do cliente com fallback:
        1. Primeiro tenta RelatorioFaturamentoImportado (local)
        2. Se não encontrar, busca no Odoo (res.partner)
        3. Nunca retorna None - usa valores padrão se necessário
        """
        resultado = {
            'nome_cliente': None,
            'municipio': None,
            'estado': None,
            'codigo_ibge': None
        }

        # 1. Tenta buscar no RelatorioFaturamentoImportado
        try:
            from app.faturamento.models import RelatorioFaturamentoImportado
            from app import db

            cliente = db.session.query(RelatorioFaturamentoImportado).filter(
                RelatorioFaturamentoImportado.cnpj_cliente == cnpj,
                RelatorioFaturamentoImportado.ativo == True
            ).order_by(RelatorioFaturamentoImportado.criado_em.desc()).first()

            if cliente and cliente.nome_cliente:
                resultado = {
                    'nome_cliente': cliente.nome_cliente,
                    'municipio': cliente.municipio,
                    'estado': cliente.estado,
                    'codigo_ibge': cliente.codigo_ibge
                }
                return resultado

        except Exception as e:
            self.warnings.append(f"Erro ao buscar cliente local {cnpj}: {e}")

        # 2. Fallback: Busca no Odoo (res.partner)
        try:
            resultado_odoo = self._get_dados_cliente_odoo(cnpj)
            if resultado_odoo.get('nome_cliente'):
                return resultado_odoo
        except Exception as e:
            self.warnings.append(f"Erro ao buscar cliente no Odoo {cnpj}: {e}")

        # 3. Se não encontrou em nenhum lugar, retorna com valores padrão
        if not resultado.get('nome_cliente'):
            resultado['nome_cliente'] = f"CLIENTE {cnpj}"
            self.warnings.append(f"Cliente {cnpj} não encontrado - usando nome padrão")

        return resultado

    def _get_dados_cliente_odoo(self, cnpj: str) -> Dict[str, Any]:
        """
        Busca dados do cliente no Odoo via res.partner
        Usa OdooConnection com Circuit Breaker para maior estabilidade
        """
        from app.odoo.utils.connection import get_odoo_connection

        resultado = {
            'nome_cliente': None,
            'municipio': None,
            'estado': None,
            'codigo_ibge': None
        }

        client = get_odoo_connection()

        # Limpa CNPJ para busca (remove formatação)
        cnpj_limpo = re.sub(r'\D', '', cnpj)

        # Formata CNPJ para padrão XX.XXX.XXX/XXXX-XX (como está no Odoo)
        # O Odoo armazena CNPJ FORMATADO e só aceita busca exata nesse formato
        if len(cnpj_limpo) == 14:
            cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"
        else:
            cnpj_formatado = cnpj  # Usa o original se não tiver 14 dígitos

        # Busca no res.partner pelo CNPJ formatado (único formato que funciona no Odoo)
        domain = [('l10n_br_cnpj', '=', cnpj_formatado)]

        partners = client.search_read(
            'res.partner',
            domain=domain,
            fields=['name', 'state_id', 'l10n_br_municipio_id', 'l10n_br_cnpj'],
            limit=1
        )

        if partners:
            partner = partners[0]
            resultado['nome_cliente'] = partner.get('name')

            # Cidade - campo l10n_br_municipio_id (brasileiro)
            # Retorna [id, "Nome da Cidade (UF)"] - Ex: [5570, "Brasília (DF)"]
            if partner.get('l10n_br_municipio_id'):
                municipio_id = partner.get('l10n_br_municipio_id')
                if isinstance(municipio_id, (list, tuple)) and len(municipio_id) > 1:
                    # Extrai apenas o nome da cidade (sem a UF entre parênteses)
                    nome_completo = municipio_id[1]  # "Brasília (DF)"
                    # Remove a UF entre parênteses se existir
                    if '(' in nome_completo:
                        resultado['municipio'] = nome_completo.split('(')[0].strip()
                    else:
                        resultado['municipio'] = nome_completo

            # Estado - state_id retorna [id, "Nome do Estado (BR)"]
            # Exemplo: [77, "Distrito Federal (BR)"]
            if partner.get('state_id'):
                state_id = partner.get('state_id')
                if isinstance(state_id, (list, tuple)) and len(state_id) > 1:
                    # Busca o código UF do estado
                    states = client.search_read(
                        'res.country.state',
                        domain=[('id', '=', state_id[0])],
                        fields=['code', 'name'],
                        limit=1
                    )
                    if states:
                        resultado['estado'] = states[0].get('code')

        return resultado

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
