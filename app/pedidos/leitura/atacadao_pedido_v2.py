"""
Extrator para PDFs de Pedido de Compra do Atacadao — layout CCPMERM02 (tabular).

Herda de AtacadaoPedidoExtractor (layout CCPMERM01 matricial) sobrescrevendo
apenas os 4 metodos com regex especifico de layout:
- _split_por_filial        (split por cabecalho CCPMERM02 em vez de PG: 1)
- _coletar_identificadores (CNPJ com pontuacao + codigo com hifen)
- _extract_header          (Pedido:XXXXX inline, Dt Elab:DD/MM/YYYY)
- _extract_produtos        (1 linha por produto em formato tabular)

Todos os helpers de batch preload, De-Para, cache de cliente, validacao e
formatacao sao herdados sem modificacao:
- extract(), _preload_clientes, _preload_depara, _preload_clientes_odoo
- _extract_filial_data, _get_dados_cliente, _get_nosso_codigo
- _format_cnpj, validate, to_dataframe, sanitize_*

Motivo da heranca de segunda ordem (primeira no modulo leitura):
CCPMERM01 e CCPMERM02 compartilham 100% do pipeline de banco de dados
(~350 linhas). Duplicar essa logica seria risco sem beneficio.

Pressuposto: cada pagina do PDF CCPMERM02 contem UM pedido para UMA filial.
Validado contra PDF de referencia (13/04/2026) com 2 pedidos / 2 paginas /
25 itens. Se aparecer PDF multi-pagina por filial, _split_por_filial precisa
ser revisto para mesclar secoes com mesmo numero de pedido.
"""
import re
from typing import Dict, List, Any

from .atacadao_pedido import AtacadaoPedidoExtractor


class AtacadaoPedidoV2Extractor(AtacadaoPedidoExtractor):
    """Extrator para formato CCPMERM02 (tabular, 1 linha por produto)."""

    # Regex pre-compilado — validado contra PDF real (25 matches exatos,
    # 0 falsos positivos). Unidades fechadas por enquanto (todos os itens do
    # PDF de referencia sao CXA). Se aparecer unidade nova, adicionar aqui.
    # Descricao aceita digitos e virgula (produtos reais Atacadao frequentemente
    # tem gramatura no nome: 'AZEITONA 200G CAMPO BELO').
    PRODUTO_PATTERN = re.compile(
        r'^(\d+)\s+'                                           # Seq
        r'(\d{4,6})-(\d+)\s+'                                  # Codigo-SubCod
        r'([A-Z0-9][A-Z0-9\s\./\(\)\-,]+?)\s+'                 # Descricao
        r'((?:CXA|FD|PCT|CX|UN|GL|SC|BD|KG|LT)'                # Embalagem inicio
        r'\s+\d+\s+[Xx]\s+[\d,]+\s*[\w,\.]+)\s+'               # Embalagem restante
        r'([SN])\s+'                                           # Pr.F (S/N)
        r'(\d{2}/\d{2}/\d{2})\s+'                              # Dt Entr DD/MM/AA
        r'([\d\.]+)\s+'                                        # Qtde
        r'([\d,\.]+)',                                          # Vlr. Unit
        re.MULTILINE
    )

    # Detector leve para contar linhas candidatas a produto (sem parsear todos os
    # campos). Usado em _extract_produtos para sanity check contra PRODUTO_PATTERN.
    CANDIDATE_LINE_PATTERN = re.compile(
        r'^\d+\s+\d{4,6}-\d+\s+',
        re.MULTILINE
    )

    def __init__(self):
        super().__init__()
        self.formato = "ATACADAO_PEDIDO_V2"

    def _split_por_filial(self, text: str) -> List[str]:
        """
        Divide o texto em secoes por filial usando o cabecalho CCPMERM02.

        Cada ocorrencia de 'CCPMERM02 <OPERADOR> DD/MM/YYYY' marca o inicio
        de uma nova pagina/filial. Fallback para texto completo se nao
        encontrar nenhum marcador.
        """
        pattern = r'CCPMERM02\s+\w+\s+\d{2}/\d{2}/\d{4}'
        positions = [m.start() for m in re.finditer(pattern, text)]
        if not positions:
            return [text]

        sections = []
        for i, start in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(text)
            sec = text[start:end]
            if sec.strip():
                sections.append(sec)

        return sections if sections else [text]

    def _coletar_identificadores(self, filiais: List[str]):
        """
        Primeira passada leve: extrai CNPJs e codigos base de todas as filiais.

        Formato CCPMERM02:
        - CNPJ: 'Local deEntrega: 75.315.333/0111-43' (com pontuacao)
        - Codigo: inicio de linha com 'Seq NNNNN-NNN'

        O label 'Local de Entrega:' aparece sem espaco entre 'de' e 'Entrega'
        no CCPMERM02 ('Local deEntrega:'). O regex '\\s+de\\s*Entrega:' cobre
        ambos os casos.
        """
        cnpjs = set()
        codigos = set()

        for filial_text in filiais:
            cnpj_match = re.search(
                r'Local\s+de\s*Entrega:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
                filial_text, re.IGNORECASE
            )
            if cnpj_match:
                # Normaliza via _format_cnpj para garantir shape identico ao V1
                # (idempotente para CNPJs ja formatados).
                cnpjs.add(self._format_cnpj(cnpj_match.group(1)))

            for m in re.finditer(
                r'^\d+\s+(\d{4,6})-\d+\s+', filial_text, re.MULTILINE
            ):
                codigos.add(m.group(1))

        return list(cnpjs), list(codigos)

    def _extract_header(self, text: str) -> Dict[str, Any]:
        """
        Extrai cabecalho do formato CCPMERM02.

        Campos diferentes de CCPMERM01:
        - numero_pedido / numero_comprador = 'Pedido:NNNNNN' (inline, sem espaco)
        - data_pedido                      = 'Dt Elab:DD/MM/YYYY' (4 digitos)
        - cnpj_filial                      = 'Local deEntrega: XX.XXX.XXX/XXXX-XX'
        - cidade/uf/cep                    = 'CIDADE - UF CEP: XXXXX-XXX'

        O alias numero_comprador e necessario porque _generate_summary em
        processor.py usa a cadeia 'numero_comprador or pedido_edi or ...'
        para popular o sumario de filial.
        """
        header = {}

        # Negative lookbehind previne match dentro de palavras (ex: 'SubPedido:').
        # 'Pedido Anterior:' ja e seguro pois tem espaco antes do numero,
        # mas mantemos a protecao como defesa em profundidade.
        m = re.search(r'(?<![A-Za-z])Pedido:(\d+)', text, re.IGNORECASE)
        if m:
            header['numero_pedido'] = m.group(1)
            header['numero_comprador'] = m.group(1)

        m = re.search(r'Dt\s+Elab:(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
        if m:
            header['data_pedido'] = m.group(1)

        m = re.search(
            r'Local\s+de\s*Entrega:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
            text, re.IGNORECASE
        )
        if m:
            # Normaliza via _format_cnpj para consistencia com V1 e com
            # o cache preenchido por _coletar_identificadores.
            header['cnpj_filial'] = self._format_cnpj(m.group(1))

        # [A-Z ] (espaco literal, NAO \s) — impede que non-greedy backtrack
        # cruze newlines e contamine cidade com linhas anteriores.
        # Ancoragem (?m)^ garante match por linha independente.
        m = re.search(
            r'(?m)^\s*([A-Z][A-Z ]+?)\s*-\s*([A-Z]{2})\s+CEP:\s*(\d{5}-?\d{3})',
            text
        )
        if m:
            header['cidade'] = m.group(1).strip()
            header['uf'] = m.group(2).upper()
            header['cep'] = m.group(3)
            header['local_entrega'] = f"{header['cidade']} - {header['uf']}"

        m = re.search(r'Prazos\s+de\s+Pgto:\s*(\d+)', text, re.IGNORECASE)
        if m:
            header['prazo_pagamento'] = int(m.group(1))

        m = re.search(r'Frete:\s*(CIF|FOB)', text, re.IGNORECASE)
        if m:
            header['tipo_frete'] = m.group(1).upper()

        return header

    def _extract_produtos(self, text: str) -> List[Dict[str, Any]]:
        """
        Extrai produtos do formato tabular CCPMERM02.

        Cada produto ocupa UMA linha:
        Seq Codigo-SubCod Descricao Embalagem Pr.F DtEntr Qtde VlrUnit ...

        Exemplo real:
        1 46625-133 AZEITONA VERDE CAMPO BELO FAT.POUCH CXA 1 X 18 150G N 14/04/26 1.344 80,32 ...

        NAO chama _extract_produtos_regex_alternativo do pai — o fallback
        do V1 busca formato matricial com barra '/' e geraria falsos
        positivos contra CCPMERM02. Se o regex principal nao casar
        nenhum item, loga warning descritivo e retorna lista vazia.
        """
        produtos = []

        for m in self.PRODUTO_PATTERN.finditer(text):
            codigo_base = m.group(2)
            codigo_sub = m.group(3)
            quantidade = self.sanitize_quantity(m.group(8))
            valor_unitario = self.sanitize_decimal(m.group(9))

            if quantidade <= 0 or float(valor_unitario) <= 0:
                continue

            produto = {
                'seq': int(m.group(1)),
                'codigo': codigo_base,
                'codigo_completo': f"{codigo_base}-{codigo_sub}",
                'descricao': m.group(4).strip(),
                'embalagem': m.group(5).strip(),
                'prazo_fixo': m.group(6) == 'S',
                'data_entrega': m.group(7),
                'quantidade': quantidade,
                'valor_unitario': valor_unitario,
                'valor_total': quantidade * valor_unitario,
            }

            depara = self._get_nosso_codigo(codigo_base)
            produto['nosso_codigo'] = depara['nosso_codigo']
            produto['nossa_descricao'] = depara['nossa_descricao']
            produto['fator_conversao'] = depara['fator_conversao']

            if not produto['nosso_codigo']:
                self.warnings.append(
                    f"Codigo Atacadao {codigo_base} nao tem De-Para configurado"
                )

            produtos.append(produto)

        # Sanity check: compara numero de linhas candidatas vs produtos extraidos.
        # Dispara warning se houver perda parcial silenciosa (ex: descricao com
        # caractere nao previsto, unidade de embalagem nova, etc).
        candidatos = len(self.CANDIDATE_LINE_PATTERN.findall(text))
        if candidatos > len(produtos):
            diff = candidatos - len(produtos)
            self.warnings.append(
                f"ATENCAO: {candidatos} linha(s) candidata(s) a produto encontrada(s) "
                f"mas apenas {len(produtos)} extraida(s). {diff} produto(s) "
                f"pode(m) ter sido silenciosamente ignorado(s) por formato nao previsto "
                f"(descricao com caractere especial, unidade de embalagem nova, etc)."
            )

        if not produtos:
            self.warnings.append(
                "Nenhum produto CCPMERM02 casou o regex — "
                "verificar layout do PDF com pdfplumber"
            )

        return produtos
