"""Extrator determinístico do recibo PDF da Motochefe (contra-prova de carga).

Layout do recibo (ex: HAROLDO SP 05.05):
- Header (página 1):
    RECIBO DO PEDIDO
    DD/MM/YYYY
    EMPRESA: <nome>
    ENDEREÇO: <rua>
    CNPJ: <cnpj>            CEP: <cep>             UF: <uf>
    TELEFONE: <fone>
    EMAIL DE CONTATO: <email>
    <REGIONAL/EQUIPE>           ← ex: HAROLDO SP
- Tabela (todas as páginas):
    PEDIDO | DESCRIÇÃO DO PRODUTO | CHASSI | MOTOR | COR
    (linhas: chassis com modelos DOT 1000W, MIA 1000W etc)
- Rodapé (última página):
    <total_motos>     ← número grande sozinho
    RETIRADA
    ___________________  ___________________
    CONFIRMAÇÃO DO CONFERENTE  CONFIRMAÇÃO DA EMPRESA
    EQUIPE
    CONFERENTE 1
    <NOME CONFERENTE>
    FEITO POR

Estratégia de extração:
- Header via regex em `extract_text()`
- Tabela via `extract_tables(table_settings={'vertical_strategy':'lines','horizontal_strategy':'lines'})`
- Filtra linhas com chassi não-vazio
"""

from __future__ import annotations

import re
from typing import Dict, List, Any, Optional

import pdfplumber

from app.pedidos.leitura.base import PDFExtractor


class MotochefeReciboPdfExtractor(PDFExtractor):
    """Parseia recibo PDF da Motochefe."""

    REGEX_DATA = re.compile(r'(\d{2}/\d{2}/\d{4})')
    REGEX_EMPRESA = re.compile(r'EMPRESA:\s*([^\n]+)')
    REGEX_ENDERECO = re.compile(r'ENDERE[ÇC]O:\s*([^\n]+)')
    REGEX_CNPJ = re.compile(r'CNPJ:\s*([\d\.\-/]+)')
    REGEX_CEP = re.compile(r'CEP:\s*([\d\-]+)')
    REGEX_UF = re.compile(r'UF:\s*([A-Z]{2})')
    REGEX_TELEFONE = re.compile(r'TELEFONE:\s*([^\n]+)')
    REGEX_EMAIL = re.compile(r'EMAIL[^:]*:\s*([\w@.\-]+)')
    REGEX_CONFERENTE = re.compile(r'CONFERENTE\s*1?\s*\n([A-ZÀ-Ÿ ]+)\s*\n\s*FEITO\s+POR', re.IGNORECASE)

    # Total de motos: número grande sozinho na última página
    REGEX_TOTAL = re.compile(r'^(\d{1,4})\s*$', re.MULTILINE)

    def __init__(self):
        super().__init__()
        self.formato = 'MOTOCHEFE_RECIBO_PDF'

    def extract(self, pdf_path: str, texto_pre_extraido: str = None) -> List[Dict[str, Any]]:
        """Retorna lista de chassis. Header é colocado em cada item.

        Cada item:
            {
                'data_recibo': str (DD/MM/YYYY),
                'empresa_motochefe': str,
                'cnpj_motochefe': str,
                'equipe': str,
                'conferente': str,
                'total_motos_declarado': int,
                'chassi': str,
                'modelo_texto': str,
                'motor': str,
                'cor': str,
            }
        """
        items: List[Dict[str, Any]] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # ============== Header ==============
                texto_total = '\n'.join((p.extract_text() or '') for p in pdf.pages)
                header = self._extract_header(texto_total)

                # ============== Tabela ==============
                linhas_chassi: List[Dict[str, str]] = []
                for page in pdf.pages:
                    tabelas = page.extract_tables({
                        'vertical_strategy': 'lines',
                        'horizontal_strategy': 'lines',
                    }) or []
                    for tabela in tabelas:
                        linhas_chassi.extend(self._parse_tabela(tabela))
                    page.flush_cache()

                # ============== Combina ==============
                for ln in linhas_chassi:
                    if not ln.get('chassi'):
                        continue
                    items.append({**header, **ln})

        except Exception as e:
            import traceback
            self.errors.append(f'Erro ao processar recibo PDF: {e}')
            self.errors.append(traceback.format_exc())

        return items

    def validate(self, data: Dict[str, Any]) -> bool:
        chassi = data.get('chassi', '').strip()
        if len(chassi) < 5:
            return False
        return True

    # ============== helpers ==============

    def _extract_header(self, texto: str) -> Dict[str, Any]:
        """Extrai campos do header. Tolerante: campos faltantes ficam None."""
        def _m(rx):
            r = rx.search(texto)
            return r.group(1).strip() if r else None

        # Total: pega o maior número que aparece sozinho em uma linha
        total_motos = None
        for m in self.REGEX_TOTAL.finditer(texto):
            n = int(m.group(1))
            if 10 <= n <= 9999:  # heurística: total real está nesse range
                if total_motos is None or n > total_motos:
                    total_motos = n

        # Equipe: linha logo antes da tabela ou no header
        # Tipicamente "HAROLDO SP" sozinho após EMAIL DE CONTATO
        equipe = None
        m_equipe = re.search(
            r'EMAIL[^:]*:\s*[\w@.\-]+\s*\n([A-ZÀ-Ÿ ]+?)\s*\n',
            texto,
        )
        if m_equipe:
            equipe = m_equipe.group(1).strip()

        return {
            'data_recibo': _m(self.REGEX_DATA),
            'empresa_motochefe': _m(self.REGEX_EMPRESA),
            'endereco_motochefe': _m(self.REGEX_ENDERECO),
            'cnpj_motochefe': self.sanitize_cnpj(_m(self.REGEX_CNPJ)) if _m(self.REGEX_CNPJ) else None,
            'cep_motochefe': _m(self.REGEX_CEP),
            'uf_motochefe': _m(self.REGEX_UF),
            'telefone_motochefe': _m(self.REGEX_TELEFONE),
            'email_motochefe': _m(self.REGEX_EMAIL),
            'equipe': equipe,
            'conferente': _m(self.REGEX_CONFERENTE),
            'total_motos_declarado': total_motos,
        }

    def _parse_tabela(self, tabela: List[List[Optional[str]]]) -> List[Dict[str, str]]:
        """Mapeia a tabela do recibo por NOME de coluna (header), nunca por posicao fixa.

        Layouts conhecidos (a ordem das colunas VARIA entre recibos):
        - [PEDIDO | DESCRICAO DO PRODUTO | CHASSI | MOTOR | COR]   (ex: HAROLDO SP)
        - [PRODUTO | CHASSI | COR | PALETE | LOCAL]                (ex: RECEBIMENTO 20.05)

        Estrategia robusta:
        - Detecta o header procurando cada coluna pelo seu nome (substring tolerante a
          capitalizacao). So a coluna CHASSI e obrigatoria; PRODUTO/DESCRICAO, MOTOR e COR
          sao opcionais (ausencia => campo vazio, nao quebra mapeamento).
        - O nome do produto pode estar como 'DESCRICAO...' ou 'PRODUTO'.
        - Sem header detectavel (paginas sem ruling no topo), aplica fallback posicional
          [DESCRICAO=1 | CHASSI=2 | MOTOR=3 | COR=4] APENAS se a coluna candidata a chassi
          tiver formato de chassi (contem digito). Isso evita o bug de inversao silenciosa
          (mapear COR->chassi) quando o layout difere — nesse caso retorna [] e a baixa
          cobertura aciona o fallback LLM no recibo_service.
        """
        if not tabela or len(tabela) < 2:
            return []

        # Busca o header nas primeiras 3 linhas (tolera linha extra antes do header)
        header_row_idx = None
        idx_chassi = idx_descricao = idx_motor = idx_cor = None
        for search_idx in range(min(3, len(tabela))):
            header = [str(c or '').strip().upper() for c in tabela[search_idx]]
            if 'CHASSI' not in ' '.join(header):
                continue
            try:
                idx_chassi = next(i for i, c in enumerate(header) if 'CHASSI' in c)
            except StopIteration:
                continue
            # Produto: aceita 'DESCRICAO...' OU 'PRODUTO'. Demais opcionais.
            idx_descricao = next(
                (i for i, c in enumerate(header) if 'DESCRI' in c or 'PRODUTO' in c),
                None,
            )
            idx_motor = next((i for i, c in enumerate(header) if 'MOTOR' in c), None)
            idx_cor = next((i for i, c in enumerate(header) if 'COR' in c), None)
            header_row_idx = search_idx
            break

        # Fallback posicional (paginas 2+ sem header): so confia se a coluna 2 parecer chassi.
        # Formato assumido: PEDIDO(0) | DESCRICAO(1) | CHASSI(2) | MOTOR(3) | COR(4)
        if header_row_idx is None:
            first_row = tabela[0]
            if len(first_row) >= 4:
                candidate_chassi = (first_row[2] or '').strip()
                if self._parece_chassi(candidate_chassi):
                    idx_chassi, idx_descricao, idx_motor, idx_cor = 2, 1, 3, 4
                    header_row_idx = -1  # sentinela: dados começam na linha 0
            if header_row_idx is None:
                return []

        data_start = header_row_idx + 1 if header_row_idx >= 0 else 0

        def _cell(row: List[Optional[str]], idx: Optional[int]) -> str:
            if idx is None or idx >= len(row):
                return ''
            return (row[idx] or '').strip()

        linhas: List[Dict[str, str]] = []
        for row in tabela[data_start:]:
            if not row or all(not c for c in row):
                continue
            chassi = _cell(row, idx_chassi).upper()
            if not chassi or len(chassi) < 5:
                continue
            linhas.append({
                'chassi': chassi,
                'modelo_texto': _cell(row, idx_descricao),
                'motor': _cell(row, idx_motor),
                'cor': _cell(row, idx_cor),
            })
        return linhas

    @staticmethod
    def _parece_chassi(valor: str) -> bool:
        """Heuristica anti-inversao: um chassi real e alfanumerico longo COM digito.

        Nomes de cor/local ('BRANCO', 'GP SENDAS') sao puramente alfabeticos e nao
        passam neste teste — protege o fallback posicional de mapear a coluna errada.
        """
        v = (valor or '').strip()
        if len(v) < 5:
            return False
        if v.upper() != v:
            return False
        return any(ch.isdigit() for ch in v)
