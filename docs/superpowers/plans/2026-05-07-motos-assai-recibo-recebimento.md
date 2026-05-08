# Motos Assaí — Plano 2B: Recibo Motochefe + Recebimento físico

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o final da Fase 3 (parser de recibo Motochefe PDF/Excel com fallback LLM) e a Fase 4 completa (wizard de recebimento físico A→B→C→D com QR/Barcode/manual, validação de chassi contra recibo, lock pessimista, captura de foto opcional, finalização com `MOTO_FALTANDO` em batch).

**Architecture:** Dois parsers determinísticos especializados (PDF via pdfplumber.extract_tables, Excel via openpyxl) com fallback LLM compartilhado. `recibo_service` orquestra ingestão. Wizard frontend é cópia adaptada de `app/templates/hora/recebimento_wizard.html` (727 linhas) — engenheiro deve **ler o original e adaptar** mantendo a estrutura A→B→C→D, trocando endpoints e modelos. Lock pessimista via `with_for_update()` + UNIQUE parcial `(recibo_id, chassi)`.

**Tech Stack:** pdfplumber 0.10+, openpyxl 3.1+, anthropic 0.98.1, html5-qrcode@2.3.8 (CDN), Bootstrap 5.

**Pré-requisitos**:
- Plano 1 (Foundation + Cadastros) implementado
- Plano 2A (Parser VOE + Pedido + Compra) implementado — recibo é vinculado a `assai_compra_motochefe`
- `ANTHROPIC_API_KEY` configurado
- Engenheiro tem acesso para LER `app/templates/hora/recebimento_wizard.html` (727 linhas) e adaptar

**Spec referência:** `docs/superpowers/specs/2026-05-07-motos-assai-design.md` §5.3, §5.4, §8.3

**Documento de exemplo do recibo**: `/mnt/c/Users/rafael.nascimento/Downloads/HAROLDO SP 05.05 (1).pdf` (115 motos, header com EQUIPE/CONFERENTE 1/FEITO POR, tabela com colunas PEDIDO|DESCRIÇÃO|CHASSI|MOTOR|COR).

---

## Visão de arquivos

```
app/motos_assai/
├── services/
│   ├── parsers/
│   │   ├── motochefe_recibo_pdf_extractor.py    # Task 1
│   │   ├── motochefe_recibo_xlsx_extractor.py   # Task 2
│   │   └── motochefe_recibo_llm_fallback.py     # Task 3
│   ├── recibo_service.py                        # Task 5
│   ├── chassi_validator.py                      # Task 10
│   ├── moto_evento_service.py                   # Task 11
│   └── recebimento_service.py                   # Task 12
├── routes/
│   ├── recibos.py                               # Tasks 6, 8, 9
│   └── recebimento.py                           # Tasks 13, 15
└── forms/
    └── recibo_forms.py                          # Task 6

app/static/motos_assai/js/
└── recebimento_wizard.js                        # Task 14

app/templates/motos_assai/
├── recibos/
│   ├── upload.html                              # Task 7
│   ├── detalhe.html                             # Task 8
│   └── lista.html                               # Task 9
└── recebimento/
    └── wizard.html                              # Task 13

scripts/migrations/
└── motos_assai_07_unique_recibo_item.sql        # Task 12 (UNIQUE parcial)

tests/motos_assai/
├── fixtures/
│   ├── recibo_motochefe_exemplo.pdf             # Task 4
│   └── recibo_motochefe_exemplo.xlsx            # Task 4 (gerar a partir do PDF)
├── test_motochefe_recibo_pdf_extractor.py       # Task 4
├── test_motochefe_recibo_xlsx_extractor.py      # Task 4
├── test_recibo_service.py                       # Task 5
├── test_chassi_validator.py                     # Task 10
├── test_moto_evento_service.py                  # Task 11
└── test_recebimento_service.py                  # Task 16
```

---

## Task 1: `MotochefeReciboPdfExtractor` (PDF determinístico)

**Files:**
- Create: `app/motos_assai/services/parsers/motochefe_recibo_pdf_extractor.py`

- [ ] **Step 1: Extractor**

`app/motos_assai/services/parsers/motochefe_recibo_pdf_extractor.py`:

```python
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
        """Tabela tem header [PEDIDO, DESCRIÇÃO DO PRODUTO, CHASSI, MOTOR, COR].

        Tolera variações de capitalização e espaços extras.
        """
        if not tabela or len(tabela) < 2:
            return []

        # Identifica colunas pelo header
        header = [str(c or '').strip().upper() for c in tabela[0]]
        try:
            idx_chassi = next(i for i, c in enumerate(header) if 'CHASSI' in c)
            idx_descricao = next(i for i, c in enumerate(header) if 'DESCRI' in c)
            idx_motor = next(i for i, c in enumerate(header) if 'MOTOR' in c)
            idx_cor = next(i for i, c in enumerate(header) if 'COR' in c)
        except StopIteration:
            return []

        linhas: List[Dict[str, str]] = []
        for row in tabela[1:]:
            if not row or all(not c for c in row):
                continue
            chassi = (row[idx_chassi] or '').strip().upper()
            if not chassi or len(chassi) < 5:
                continue
            linhas.append({
                'chassi': chassi,
                'modelo_texto': (row[idx_descricao] or '').strip(),
                'motor': (row[idx_motor] or '').strip(),
                'cor': (row[idx_cor] or '').strip(),
            })
        return linhas
```

- [ ] **Step 2: Commit**

```bash
git add app/motos_assai/services/parsers/motochefe_recibo_pdf_extractor.py
git commit -m "feat(motos_assai): MotochefeReciboPdfExtractor (header + tabela via pdfplumber)"
```

---

## Task 2: `MotochefeReciboXlsxExtractor` (Excel determinístico)

**Files:**
- Create: `app/motos_assai/services/parsers/motochefe_recibo_xlsx_extractor.py`

- [ ] **Step 1: Extractor**

`app/motos_assai/services/parsers/motochefe_recibo_xlsx_extractor.py`:

```python
"""Extrator determinístico do recibo Motochefe em formato Excel (.xlsx).

Estratégia:
- Carrega workbook com data_only=True (resolve fórmulas)
- Detecta header pela presença de células contendo CHASSI, MOTOR, COR
- Extrai header (EMPRESA, CNPJ, EQUIPE, CONFERENTE) das células acima da tabela
- Itera linhas a partir do header até a primeira linha sem chassi
"""

from __future__ import annotations

import re
from typing import Dict, List, Any, Optional, Tuple

from openpyxl import load_workbook


class MotochefeReciboXlsxExtractor:
    """Parseia recibo Excel da Motochefe (estrutura tabular)."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.formato = 'MOTOCHEFE_RECIBO_XLSX'

    def extract(self, xlsx_path: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        try:
            wb = load_workbook(xlsx_path, data_only=True)
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]

                # Localiza header da tabela (linha onde aparece CHASSI/MOTOR/COR)
                header_row, col_map = self._localizar_header(ws)
                if header_row is None:
                    continue

                # Header textual: campos fora da tabela
                header_data = self._extract_header_excel(ws, header_row)

                # Linhas de chassi
                for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
                    chassi_raw = row[col_map['chassi']] if col_map.get('chassi') is not None else None
                    if not chassi_raw:
                        continue
                    chassi = str(chassi_raw).strip().upper()
                    if len(chassi) < 5:
                        continue
                    items.append({
                        **header_data,
                        'chassi': chassi,
                        'modelo_texto': self._cell_str(row, col_map.get('descricao')),
                        'motor': self._cell_str(row, col_map.get('motor')),
                        'cor': self._cell_str(row, col_map.get('cor')),
                    })
        except Exception as e:
            self.errors.append(f'Erro ao processar XLSX: {e}')
        return items

    def _cell_str(self, row, idx: Optional[int]) -> str:
        if idx is None:
            return ''
        v = row[idx]
        return str(v).strip() if v is not None else ''

    def _localizar_header(self, ws) -> Tuple[Optional[int], Dict[str, int]]:
        """Acha linha cabeçalho da tabela. Retorna (linha, {chassi, descricao, motor, cor})."""
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            cells_upper = [str(c or '').strip().upper() for c in row]

            col_map: Dict[str, int] = {}
            for i, c in enumerate(cells_upper):
                if c == 'CHASSI':
                    col_map['chassi'] = i
                elif 'DESCRI' in c or c == 'MODELO' or 'PRODUTO' in c:
                    col_map.setdefault('descricao', i)
                elif c == 'MOTOR':
                    col_map['motor'] = i
                elif c == 'COR':
                    col_map['cor'] = i

            if 'chassi' in col_map:
                return row_idx, col_map

        return None, {}

    def _extract_header_excel(self, ws, header_row: int) -> Dict[str, Any]:
        """Procura campos do header nas linhas anteriores ao cabeçalho da tabela."""
        header = {
            'data_recibo': None,
            'empresa_motochefe': None,
            'cnpj_motochefe': None,
            'equipe': None,
            'conferente': None,
            'total_motos_declarado': None,
        }
        for row in ws.iter_rows(min_row=1, max_row=header_row - 1, values_only=True):
            for cell in row:
                if not cell:
                    continue
                cell_str = str(cell).strip()
                upper = cell_str.upper()
                if upper.startswith('EMPRESA:'):
                    header['empresa_motochefe'] = cell_str.split(':', 1)[1].strip()
                elif upper.startswith('CNPJ:'):
                    cnpj_str = cell_str.split(':', 1)[1].strip()
                    header['cnpj_motochefe'] = re.sub(r'\D', '', cnpj_str)[:14] or None
                elif re.match(r'\d{2}/\d{2}/\d{4}', cell_str):
                    header['data_recibo'] = cell_str[:10]

        # Total e equipe podem estar em linhas APÓS a tabela; procurar tudo
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                # Total: número entre 10 e 9999
                if cell_str.isdigit():
                    n = int(cell_str)
                    if 10 <= n <= 9999 and (header['total_motos_declarado'] is None or n > header['total_motos_declarado']):
                        header['total_motos_declarado'] = n

        return header
```

- [ ] **Step 2: Commit**

```bash
git add app/motos_assai/services/parsers/motochefe_recibo_xlsx_extractor.py
git commit -m "feat(motos_assai): MotochefeReciboXlsxExtractor (openpyxl-based)"
```

---

## Task 3: `MotochefeReciboLlmFallback`

**Files:**
- Create: `app/motos_assai/services/parsers/motochefe_recibo_llm_fallback.py`

- [ ] **Step 1: Fallback**

`app/motos_assai/services/parsers/motochefe_recibo_llm_fallback.py`:

```python
"""Fallback LLM para recibo Motochefe (PDF ou XLSX→PDF).

Acionado quando determinístico extrai < 80% das linhas declaradas no header.

Estrutura:
- Haiku 4.5 → Sonnet 4.6 fallback
- PDF: enviado como document block direto
- XLSX: converte primeiro para texto plano (sem layout) e envia como text
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from decimal import Decimal
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

HAIKU_MODEL = 'claude-haiku-4-5-20251001'
SONNET_MODEL = 'claude-sonnet-4-6'

PROMPT_SYSTEM = """Você é um parser de recibos da Motochefe (contra-prova de entrega de motos elétricas para um CD).

Estrutura do recibo:
- Header com: data, empresa Motochefe, CNPJ, endereço, equipe, conferente, total de motos
- Tabela com linhas: PEDIDO | DESCRIÇÃO DO PRODUTO | CHASSI | MOTOR | COR

Modelos esperados (mas pode haver outros): DOT 1000W, X11 MINI 1000W, SOL 1000W, MIA 1000W.

Retorne JSON puro (sem markdown, sem comentários):

{
  "data_recibo": "DD/MM/YYYY",
  "empresa_motochefe": "...",
  "cnpj_motochefe": "37542484000100",
  "equipe": "HAROLDO SP",
  "conferente": "KAROLINE",
  "total_motos_declarado": 115,
  "chassis": [
    {
      "chassi": "LA2025SA110007354",
      "modelo_texto": "DOT 1000W",
      "motor": "QS60V30H25120801923",
      "cor": "CINZA"
    }
  ]
}

REGRAS:
- chassi sempre em UPPERCASE.
- Se um campo não existir, omita-o (não use null).
- Não inclua texto antes ou depois do JSON.
"""


class MotochefeReciboLlmFallbackError(Exception):
    pass


def parse_pdf_via_llm(pdf_bytes: bytes) -> Dict[str, Any]:
    """Parseia PDF de recibo via LLM. Retorna dict no mesmo formato dos extractors determinísticos."""
    try:
        import anthropic
    except ImportError:
        raise MotochefeReciboLlmFallbackError("anthropic SDK não instalado")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise MotochefeReciboLlmFallbackError("ANTHROPIC_API_KEY não configurada")

    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    for tentativa, modelo in enumerate([HAIKU_MODEL, SONNET_MODEL]):
        try:
            data = _chamar_llm_pdf(client, pdf_b64, modelo)
            items = _converter_para_lista_flat(data)
            if items:
                parser = 'LLM_HAIKU' if tentativa == 0 else 'LLM_SONNET'
                return {'parser_usado': parser, 'items': items}
        except Exception as e:
            logger.warning(f'{modelo} falhou: {e}')

    raise MotochefeReciboLlmFallbackError("Haiku e Sonnet falharam")


def parse_xlsx_via_llm(xlsx_bytes: bytes) -> Dict[str, Any]:
    """Parseia XLSX serializando-o como texto via openpyxl + envia como text."""
    import io
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(xlsx_bytes), data_only=True)

    chunks: List[str] = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        chunks.append(f'== Aba: {sheet_name} ==')
        for row in ws.iter_rows(values_only=True):
            cells = ['' if c is None else str(c) for c in row]
            chunks.append(' | '.join(cells))

    texto_xlsx = '\n'.join(chunks)
    return _parse_text_via_llm(texto_xlsx)


def _parse_text_via_llm(texto: str) -> Dict[str, Any]:
    try:
        import anthropic
    except ImportError:
        raise MotochefeReciboLlmFallbackError("anthropic SDK não instalado")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise MotochefeReciboLlmFallbackError("ANTHROPIC_API_KEY não configurada")

    client = anthropic.Anthropic(api_key=api_key)

    for tentativa, modelo in enumerate([HAIKU_MODEL, SONNET_MODEL]):
        try:
            response = client.messages.create(
                model=modelo,
                max_tokens=8192,
                system=PROMPT_SYSTEM,
                messages=[{
                    'role': 'user',
                    'content': f'Texto extraído do XLSX:\n\n{texto}',
                }],
            )
            raw = response.content[0].text.strip()
            data = json.loads(_extrair_json(raw))
            items = _converter_para_lista_flat(data)
            if items:
                parser = 'LLM_HAIKU' if tentativa == 0 else 'LLM_SONNET'
                return {'parser_usado': parser, 'items': items}
        except Exception as e:
            logger.warning(f'{modelo} (xlsx) falhou: {e}')

    raise MotochefeReciboLlmFallbackError("Haiku e Sonnet falharam (xlsx)")


def _chamar_llm_pdf(client, pdf_b64: str, model: str) -> Dict:
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=PROMPT_SYSTEM,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'document',
                 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': pdf_b64}},
                {'type': 'text', 'text': 'Extraia o recibo em JSON.'},
            ],
        }],
    )
    raw = response.content[0].text.strip()
    return json.loads(_extrair_json(raw))


def _extrair_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('```'):
        m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', raw, re.DOTALL)
        if m:
            return m.group(1)
    inicio = raw.find('{')
    if inicio < 0:
        raise MotochefeReciboLlmFallbackError(f'Sem JSON: {raw[:200]}')
    return raw[inicio:]


def _converter_para_lista_flat(data: Dict) -> List[Dict]:
    items = []
    header = {
        'data_recibo': data.get('data_recibo'),
        'empresa_motochefe': data.get('empresa_motochefe'),
        'cnpj_motochefe': re.sub(r'\D', '', str(data.get('cnpj_motochefe', '')))[:14] or None,
        'equipe': data.get('equipe'),
        'conferente': data.get('conferente'),
        'total_motos_declarado': data.get('total_motos_declarado'),
    }
    for c in data.get('chassis', []):
        chassi = str(c.get('chassi', '')).strip().upper()
        if not chassi:
            continue
        items.append({
            **header,
            'chassi': chassi,
            'modelo_texto': c.get('modelo_texto') or c.get('modelo') or '',
            'motor': c.get('motor', ''),
            'cor': c.get('cor', ''),
        })
    return items
```

- [ ] **Step 2: Commit**

```bash
git add app/motos_assai/services/parsers/motochefe_recibo_llm_fallback.py
git commit -m "feat(motos_assai): LLM fallback for Motochefe recibo (PDF + XLSX)"
```

---

## Task 4: Testes dos parsers de recibo

**Files:**
- Create: `tests/motos_assai/fixtures/recibo_motochefe_exemplo.pdf`
- Create: `tests/motos_assai/test_motochefe_recibo_pdf_extractor.py`

- [ ] **Step 1: Copiar fixture**

```bash
cp "/mnt/c/Users/rafael.nascimento/Downloads/HAROLDO SP 05.05 (1).pdf" \
   tests/motos_assai/fixtures/recibo_motochefe_exemplo.pdf
ls -lh tests/motos_assai/fixtures/recibo_motochefe_exemplo.pdf
```

Expected: ~280KB.

- [ ] **Step 2: Testes do PDF extractor**

`tests/motos_assai/test_motochefe_recibo_pdf_extractor.py`:

```python
import os
import pytest
from app.motos_assai.services.parsers.motochefe_recibo_pdf_extractor import (
    MotochefeReciboPdfExtractor,
)


FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'recibo_motochefe_exemplo.pdf')


def test_fixture_exists():
    assert os.path.exists(FIXTURE)


def test_extract_retorna_chassis():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    assert len(items) > 50, f'Esperava >=50 chassis (canon: 115), veio {len(items)}'


def test_header_data_recibo():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    assert items
    datas = {i['data_recibo'] for i in items if i.get('data_recibo')}
    assert '05/05/2026' in datas


def test_header_equipe_haroldo_sp():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    equipes = {i.get('equipe') for i in items if i.get('equipe')}
    assert any('HAROLDO' in str(e or '') for e in equipes)


def test_chassis_uppercase_e_distintos():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    chassis = [i['chassi'] for i in items]
    # Uppercase
    assert all(c == c.upper() for c in chassis)
    # Distintos (sem duplicatas)
    assert len(chassis) == len(set(chassis)), 'Chassis duplicados'


def test_modelo_texto_dot_e_mia():
    """Recibo HAROLDO SP tem DOT 1000W e MIA 1000W."""
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    modelos = {i.get('modelo_texto', '').upper() for i in items}
    assert any('DOT' in m for m in modelos)
    assert any('MIA' in m for m in modelos)
```

- [ ] **Step 3: Rodar**

```bash
pytest tests/motos_assai/test_motochefe_recibo_pdf_extractor.py -v
```

Expected: 6 PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/motos_assai/fixtures/recibo_motochefe_exemplo.pdf
git add tests/motos_assai/test_motochefe_recibo_pdf_extractor.py
git commit -m "test(motos_assai): MotochefeReciboPdfExtractor with HAROLDO SP fixture"
```

---

## Task 5: `recibo_service.importar`

**Files:**
- Create: `app/motos_assai/services/recibo_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Create: `tests/motos_assai/test_recibo_service.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/recibo_service.py`:

```python
"""Orquestração de importação do recibo Motochefe.

Aceita PDF e Excel. Estratégia:
1. Salva arquivo em S3
2. Detecta tipo (mime/extensão)
3. Roda extractor determinístico apropriado
4. Calcula confiança = (chassis_extraidos / total_motos_declarado_no_header)
5. Se confiança < 0.80 ou zero chassis: aciona LLM fallback
6. Persiste AssaiReciboMotochefe + N AssaiReciboItem
7. Resolve modelo_id via modelo_resolver para cada item
"""

from __future__ import annotations

import io
import logging
import tempfile
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app import db
from app.utils.file_storage import FileStorage
from app.motos_assai.models import (
    AssaiCompraMotochefe, AssaiReciboMotochefe, AssaiReciboItem,
    RECIBO_STATUS_AGUARDANDO,
)
from app.motos_assai.services.parsers.motochefe_recibo_pdf_extractor import (
    MotochefeReciboPdfExtractor,
)
from app.motos_assai.services.parsers.motochefe_recibo_xlsx_extractor import (
    MotochefeReciboXlsxExtractor,
)
from app.motos_assai.services.parsers.motochefe_recibo_llm_fallback import (
    parse_pdf_via_llm, parse_xlsx_via_llm, MotochefeReciboLlmFallbackError,
)
from app.motos_assai.services.modelo_resolver import resolver_modelo

logger = logging.getLogger(__name__)

CONFIANCA_LIMIAR = 0.80


class ReciboParserError(Exception):
    pass


def importar(
    compra_id: int,
    file_bytes: bytes,
    nome_arquivo: str,
    mime_type: Optional[str],
    importado_por_id: int,
) -> AssaiReciboMotochefe:
    """Importa recibo Motochefe (PDF ou XLSX)."""
    AssaiCompraMotochefe.query.get_or_404(compra_id)

    tipo_doc = _detectar_tipo(nome_arquivo, mime_type)

    # 1. S3
    buf = io.BytesIO(file_bytes)
    buf.name = nome_arquivo
    ext = 'pdf' if tipo_doc == 'PDF' else 'xlsx'
    s3_key = FileStorage().save_file(
        buf, folder=f'motos_assai/recibos/{compra_id}',
        filename=nome_arquivo,
        allowed_extensions=[ext],
    )

    # 2. Determinístico
    items = []
    parser_usado = 'DETERMINISTICO'
    confianca = 0.0

    if tipo_doc == 'PDF':
        extractor = MotochefeReciboPdfExtractor()
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(file_bytes)
            tmp = f.name
        try:
            items = extractor.extract(tmp)
        finally:
            import os; os.unlink(tmp)
    else:
        extractor = MotochefeReciboXlsxExtractor()
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(file_bytes)
            tmp = f.name
        try:
            items = extractor.extract(tmp)
        finally:
            import os; os.unlink(tmp)

    confianca = _calcular_confianca(items)

    # 3. Fallback LLM
    if not items or confianca < CONFIANCA_LIMIAR:
        logger.warning(f'Confiança {confianca:.2f} ou zero items. Acionando LLM.')
        try:
            llm_result = (
                parse_pdf_via_llm(file_bytes) if tipo_doc == 'PDF'
                else parse_xlsx_via_llm(file_bytes)
            )
            items = llm_result['items']
            parser_usado = llm_result['parser_usado']
            confianca = 1.0
        except MotochefeReciboLlmFallbackError as e:
            if not items:
                raise ReciboParserError(f'Determinístico zero + LLM falhou: {e}')
            logger.error(f'LLM falhou; usando determinístico com baixa confiança: {e}')

    if not items:
        raise ReciboParserError('Zero chassis extraídos')

    # 4. Persistir
    header = items[0]
    recibo = AssaiReciboMotochefe(
        compra_id=compra_id,
        numero_recibo=None,
        data_recibo=_parse_data(header.get('data_recibo')),
        equipe=header.get('equipe'),
        conferente_motochefe=header.get('conferente'),
        total_motos_declarado=header.get('total_motos_declarado'),
        doc_s3_key=s3_key,
        tipo_documento=tipo_doc,
        parser_usado=parser_usado,
        parsing_confianca=Decimal(str(round(confianca, 2))),
        status=RECIBO_STATUS_AGUARDANDO,
        criado_por_id=importado_por_id,
    )
    db.session.add(recibo)
    db.session.flush()

    chassis_vistos = set()
    for it in items:
        chassi = it.get('chassi', '').strip().upper()
        if not chassi or chassi in chassis_vistos:
            continue
        chassis_vistos.add(chassi)

        modelo = resolver_modelo(it.get('modelo_texto', ''), origem='RECIBO_MOTOCHEFE')

        db.session.add(AssaiReciboItem(
            recibo_id=recibo.id,
            chassi=chassi,
            modelo_texto_recibo=it.get('modelo_texto'),
            modelo_id=modelo.id if modelo else None,
            cor_texto=it.get('cor'),
            motor=it.get('motor'),
            conferido=False,
        ))

    db.session.commit()
    return recibo


def _detectar_tipo(nome_arquivo: str, mime_type: Optional[str]) -> str:
    nome_lower = (nome_arquivo or '').lower()
    if nome_lower.endswith('.pdf') or (mime_type and 'pdf' in mime_type):
        return 'PDF'
    if nome_lower.endswith(('.xlsx', '.xls')) or (mime_type and 'sheet' in (mime_type or '')):
        return 'EXCEL'
    raise ReciboParserError(f'Tipo de arquivo não suportado: {nome_arquivo}')


def _calcular_confianca(items: list) -> float:
    if not items:
        return 0.0
    total_declarado = items[0].get('total_motos_declarado')
    if not total_declarado:
        # Sem total declarado → confiança média se tem chassis
        return 0.85
    extraidos = len({i['chassi'] for i in items if i.get('chassi')})
    if total_declarado <= 0:
        return 0.0
    return min(1.0, extraidos / total_declarado)


def _parse_data(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip()[:10], '%d/%m/%Y').date()
    except (ValueError, AttributeError):
        return None


def get_recibo(recibo_id: int) -> AssaiReciboMotochefe:
    return AssaiReciboMotochefe.query.get_or_404(recibo_id)


def listar_recibos(compra_id: Optional[int] = None):
    q = AssaiReciboMotochefe.query
    if compra_id:
        q = q.filter_by(compra_id=compra_id)
    return q.order_by(AssaiReciboMotochefe.criado_em.desc()).all()
```

- [ ] **Step 2: Atualizar __init__**

```python
from .recibo_service import importar as importar_recibo, get_recibo, listar_recibos, ReciboParserError
```

E exportar.

- [ ] **Step 3: Test integration**

`tests/motos_assai/test_recibo_service.py`:

```python
import os
import pytest
from app import db
from app.motos_assai.services import importar_recibo, ReciboParserError
from app.motos_assai.services.compra_service import criar_consolidado
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiCompraMotochefe, AssaiReciboMotochefe, AssaiReciboItem,
)


FIXTURE_PDF = os.path.join(os.path.dirname(__file__), 'fixtures', 'recibo_motochefe_exemplo.pdf')


def _criar_compra_minima(admin_user):
    p = AssaiPedidoVenda(numero='RECIBO-TEST-001', criado_por_id=admin_user.id, status='ABERTO')
    db.session.add(p)
    db.session.flush()
    return criar_consolidado([p.id], None, admin_user.id)


def test_importar_pdf_recibo(app, admin_user):
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        with open(FIXTURE_PDF, 'rb') as f:
            pdf_bytes = f.read()

        recibo = importar_recibo(
            compra_id=compra.id,
            file_bytes=pdf_bytes,
            nome_arquivo='haroldo_sp.pdf',
            mime_type='application/pdf',
            importado_por_id=admin_user.id,
        )

        assert recibo.tipo_documento == 'PDF'
        assert recibo.compra_id == compra.id
        items = AssaiReciboItem.query.filter_by(recibo_id=recibo.id).all()
        assert len(items) > 50

        # Pelo menos algum chassi DOT deve ter modelo_id resolvido (assume DOT seeded)
        dot_resolvidos = [i for i in items if i.modelo_id is not None]
        assert len(dot_resolvidos) > 0

        db.session.rollback()


def test_tipo_arquivo_invalido(app, admin_user):
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        with pytest.raises(ReciboParserError, match='não suportado'):
            importar_recibo(
                compra_id=compra.id, file_bytes=b'fake',
                nome_arquivo='x.txt', mime_type='text/plain',
                importado_por_id=admin_user.id,
            )
        db.session.rollback()
```

- [ ] **Step 4: Rodar**

```bash
pytest tests/motos_assai/test_recibo_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/recibo_service.py
git add app/motos_assai/services/__init__.py
git add tests/motos_assai/test_recibo_service.py
git commit -m "feat(motos_assai): recibo_service.importar (PDF + XLSX + LLM fallback)"
```

---

## Task 6: Form + Rota POST upload recibo

**Files:**
- Create: `app/motos_assai/forms/recibo_forms.py`
- Modify: `app/motos_assai/forms/__init__.py`
- Create: `app/motos_assai/routes/recibos.py`
- Modify: `app/motos_assai/routes/__init__.py`

- [ ] **Step 1: Form**

`app/motos_assai/forms/recibo_forms.py`:

```python
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed


class UploadReciboForm(FlaskForm):
    arquivo = FileField('Recibo Motochefe (PDF ou XLSX)', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'xlsx', 'xls'], 'Apenas PDF ou Excel.'),
    ])
```

- [ ] **Step 2: Atualizar forms __init__**

```python
from .recibo_forms import UploadReciboForm
```

- [ ] **Step 3: Rota**

`app/motos_assai/routes/recibos.py`:

```python
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import UploadReciboForm
from app.motos_assai.services import (
    importar_recibo, get_recibo, listar_recibos, get_compra,
    ReciboParserError,
)
from app.motos_assai.models import AssaiReciboItem


@motos_assai_bp.route('/compras/<int:compra_id>/recibos/upload', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def recibos_upload(compra_id):
    compra = get_compra(compra_id)
    form = UploadReciboForm()
    if form.validate_on_submit():
        f = form.arquivo.data
        try:
            recibo = importar_recibo(
                compra_id=compra_id,
                file_bytes=f.read(),
                nome_arquivo=f.filename,
                mime_type=f.mimetype,
                importado_por_id=current_user.id,
            )
            flash(f'Recibo importado via {recibo.parser_usado} '
                  f'(confiança {float(recibo.parsing_confianca):.0%}).', 'success')
            return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo.id))
        except ReciboParserError as e:
            current_app.logger.exception('Erro recibo')
            flash(str(e), 'danger')
    return render_template('motos_assai/recibos/upload.html', form=form, compra=compra)
```

- [ ] **Step 4: Importar route no blueprint**

```python
from app.motos_assai.routes import recibos  # noqa: E402,F401
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/forms/recibo_forms.py app/motos_assai/forms/__init__.py
git add app/motos_assai/routes/recibos.py app/motos_assai/routes/__init__.py
git commit -m "feat(motos_assai): upload recibo route + form"
```

---

## Task 7: Template upload recibo

**Files:**
- Create: `app/templates/motos_assai/recibos/upload.html`

- [ ] **Step 1: Template**

`app/templates/motos_assai/recibos/upload.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="mb-3">
  <h2>Upload de Recibo Motochefe</h2>
  <p class="text-muted">PO Motochefe: <strong>{{ compra.numero }}</strong></p>
</header>

<form method="POST" enctype="multipart/form-data" class="card p-4" style="max-width: 600px;">
  {{ form.hidden_tag() }}

  <div class="mb-3">
    {{ form.arquivo.label(class="form-label") }}
    {{ form.arquivo(class="form-control", accept=".pdf,.xlsx,.xls") }}
    {% for e in form.arquivo.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
  </div>

  <div class="alert alert-info small">
    Aceita PDF (recibo digitalizado/gerado) ou Excel (.xlsx). Determinístico
    primeiro; LLM (Haiku→Sonnet) ativado quando confiança &lt; 80%.
  </div>

  <button type="submit" class="btn btn-primary">
    <i class="fas fa-upload"></i> Importar
  </button>
  <a href="{{ url_for('motos_assai.compras_detalhe', compra_id=compra.id) }}"
     class="btn btn-outline-secondary">Cancelar</a>
</form>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/motos_assai/recibos/upload.html
git commit -m "feat(motos_assai): upload recibo template"
```

---

## Task 8: Detalhe + lista de recibos

**Files:**
- Modify: `app/motos_assai/routes/recibos.py`
- Create: `app/templates/motos_assai/recibos/detalhe.html`
- Create: `app/templates/motos_assai/recibos/lista.html`

- [ ] **Step 1: Rotas**

Adicionar a `app/motos_assai/routes/recibos.py`:

```python
@motos_assai_bp.route('/recibos/<int:recibo_id>')
@login_required
@require_motos_assai
def recibos_detalhe(recibo_id):
    recibo = get_recibo(recibo_id)
    items = AssaiReciboItem.query.filter_by(recibo_id=recibo_id).order_by(
        AssaiReciboItem.id
    ).all()
    conferidos = sum(1 for i in items if i.conferido)
    return render_template(
        'motos_assai/recibos/detalhe.html',
        recibo=recibo, items=items, conferidos=conferidos,
    )


@motos_assai_bp.route('/recibos')
@login_required
@require_motos_assai
def recibos_lista():
    recibos = listar_recibos()
    return render_template('motos_assai/recibos/lista.html', recibos=recibos)
```

- [ ] **Step 2: Template detalhe**

`app/templates/motos_assai/recibos/detalhe.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>Recibo Motochefe — {{ recibo.numero_recibo or '#' ~ recibo.id }}
    <span class="badge bg-{% if recibo.status == 'CONCLUIDO' %}success{% elif recibo.status == 'COM_DIVERGENCIA' %}warning{% else %}primary{% endif %}">
      {{ recibo.status }}
    </span>
  </h2>
  {% if recibo.status == 'RECEBIDO_AGUARDANDO_CONFERENCIA' or recibo.status == 'EM_CONFERENCIA' %}
  <a href="{{ url_for('motos_assai.recebimento_wizard', recibo_id=recibo.id) }}"
     class="btn btn-primary">
    <i class="fas fa-qrcode"></i> Iniciar conferência
  </a>
  {% endif %}
</header>

<dl class="row small">
  <dt class="col-sm-2">Compra</dt>
  <dd class="col-sm-4">
    <a href="{{ url_for('motos_assai.compras_detalhe', compra_id=recibo.compra_id) }}">
      PO #{{ recibo.compra_id }}
    </a>
  </dd>
  <dt class="col-sm-2">Data recibo</dt>
  <dd class="col-sm-4">{{ recibo.data_recibo.strftime('%d/%m/%Y') if recibo.data_recibo else '-' }}</dd>

  <dt class="col-sm-2">Equipe</dt>
  <dd class="col-sm-4">{{ recibo.equipe or '-' }}</dd>
  <dt class="col-sm-2">Conferente</dt>
  <dd class="col-sm-4">{{ recibo.conferente_motochefe or '-' }}</dd>

  <dt class="col-sm-2">Total declarado</dt>
  <dd class="col-sm-4">{{ recibo.total_motos_declarado or '-' }}</dd>
  <dt class="col-sm-2">Conferidos</dt>
  <dd class="col-sm-4">{{ conferidos }} / {{ items|length }}</dd>

  <dt class="col-sm-2">Parser</dt>
  <dd class="col-sm-10">
    <code>{{ recibo.parser_usado }}</code>
    (confiança {{ '%.0f%%' | format(recibo.parsing_confianca * 100) if recibo.parsing_confianca else '-' }})
  </dd>
</dl>

<h4 class="mt-3">Chassis ({{ items|length }})</h4>
<table class="table table-sm">
  <thead>
    <tr><th>Chassi</th><th>Modelo (recibo)</th><th>Modelo (resolvido)</th>
        <th>Motor</th><th>Cor</th><th>Conferido</th><th>Divergência</th></tr>
  </thead>
  <tbody>
    {% for it in items %}
    <tr>
      <td><code>{{ it.chassi }}</code></td>
      <td>{{ it.modelo_texto_recibo }}</td>
      <td>{% if it.modelo_id %}<span class="badge bg-success">{{ it.modelo.codigo }}</span>{% else %}<span class="badge bg-warning">não resolvido</span>{% endif %}</td>
      <td><small>{{ it.motor or '-' }}</small></td>
      <td>{{ it.cor_texto or '-' }}</td>
      <td>{% if it.conferido %}<i class="fas fa-check text-success"></i>{% else %}<i class="fas fa-clock text-muted"></i>{% endif %}</td>
      <td>{% if it.tipo_divergencia %}<span class="badge bg-warning">{{ it.tipo_divergencia }}</span>{% endif %}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 3: Template lista**

`app/templates/motos_assai/recibos/lista.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<h2>Recibos Motochefe</h2>
<table class="table table-hover">
  <thead><tr><th>#</th><th>PO</th><th>Data recibo</th><th>Equipe</th><th>Total</th><th>Status</th></tr></thead>
  <tbody>
    {% for r in recibos %}
    <tr>
      <td><a href="{{ url_for('motos_assai.recibos_detalhe', recibo_id=r.id) }}">#{{ r.id }}</a></td>
      <td><a href="{{ url_for('motos_assai.compras_detalhe', compra_id=r.compra_id) }}">PO #{{ r.compra_id }}</a></td>
      <td>{{ r.data_recibo.strftime('%d/%m/%Y') if r.data_recibo else '-' }}</td>
      <td>{{ r.equipe or '-' }}</td>
      <td>{{ r.total_motos_declarado or '-' }}</td>
      <td><span class="badge bg-secondary">{{ r.status }}</span></td>
    </tr>
    {% else %}
    <tr><td colspan="6" class="text-center text-muted">Nenhum recibo.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 4: Adicionar link no nav**

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.recibos_lista') }}">
      <i class="fas fa-truck-loading"></i> Recibos
    </a>
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/routes/recibos.py
git add app/templates/motos_assai/recibos/
git add app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): recibo detail + list views"
```

---

## Task 9: Migration UNIQUE parcial em `assai_recibo_item`

**Files:**
- Create: `scripts/migrations/motos_assai_07_unique_recibo_item.sql`
- Create: `scripts/migrations/motos_assai_07_unique_recibo_item.py`

- [ ] **Step 1: SQL**

`scripts/migrations/motos_assai_07_unique_recibo_item.sql`:

```sql
-- UNIQUE (recibo_id, chassi) — protege contra race em conferência simultânea.
-- Já criado no Plano 1 schema (verificar se existe; idempotente).

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'assai_recibo_item'
          AND indexname = 'ux_assai_recibo_item_recibo_chassi'
    ) THEN
        CREATE UNIQUE INDEX ux_assai_recibo_item_recibo_chassi
            ON assai_recibo_item(recibo_id, chassi);
    END IF;
END $$;
```

- [ ] **Step 2: Python**

`scripts/migrations/motos_assai_07_unique_recibo_item.py`:

```python
"""Garante UNIQUE (recibo_id, chassi) em assai_recibo_item."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        sql_path = os.path.join(os.path.dirname(__file__),
                                'motos_assai_07_unique_recibo_item.sql')
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()
        print('OK: UNIQUE (recibo_id, chassi) garantido.')


if __name__ == '__main__':
    run()
```

- [ ] **Step 3: Executar**

```bash
python scripts/migrations/motos_assai_07_unique_recibo_item.py
```

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/motos_assai_07_unique_recibo_item.{py,sql}
git commit -m "feat(motos_assai): ensure UNIQUE (recibo_id, chassi) idempotently"
```

---

## Task 10: `chassi_validator` service

**Files:**
- Create: `app/motos_assai/services/chassi_validator.py`
- Modify: `app/motos_assai/services/__init__.py`
- Create: `tests/motos_assai/test_chassi_validator.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/chassi_validator.py`:

```python
"""Validador de chassi contra regex configurado em assai_modelo.regex_chassi.

Não bloqueia operação — retorna alerta para UI exibir.
"""

import re
from typing import Optional, Dict, Any
from app.motos_assai.models import AssaiModelo


class ResultadoValidacao(Dict):
    """{ok: bool, mensagem: str, regex_usado: str | None}"""


def validar_chassi(chassi: str, modelo_id: Optional[int]) -> Dict[str, Any]:
    """Valida chassi contra regex_chassi do modelo.

    Args:
        chassi: chassi observado
        modelo_id: id do AssaiModelo (None → não valida)

    Returns:
        {ok: True/False, mensagem: str, regex_usado: str | None}
    """
    if not chassi:
        return {'ok': False, 'mensagem': 'Chassi vazio', 'regex_usado': None}

    if not modelo_id:
        return {'ok': True, 'mensagem': 'Modelo não definido — pulando validação',
                'regex_usado': None}

    modelo = AssaiModelo.query.get(modelo_id)
    if not modelo:
        return {'ok': False, 'mensagem': f'Modelo {modelo_id} não encontrado',
                'regex_usado': None}

    if not modelo.regex_chassi:
        return {'ok': True, 'mensagem': f'Modelo {modelo.codigo} sem regex configurado',
                'regex_usado': None}

    pattern = modelo.regex_chassi
    if not pattern.startswith('^'):
        pattern = '^' + pattern
    if not pattern.endswith('$'):
        pattern = pattern + '$'

    try:
        if re.match(pattern, chassi):
            return {'ok': True, 'mensagem': 'Chassi bate o regex',
                    'regex_usado': modelo.regex_chassi}
        else:
            return {'ok': False,
                    'mensagem': f'Chassi {chassi} não bate o regex de {modelo.codigo}',
                    'regex_usado': modelo.regex_chassi}
    except re.error as e:
        return {'ok': False, 'mensagem': f'regex inválido: {e}',
                'regex_usado': modelo.regex_chassi}
```

- [ ] **Step 2: Atualizar __init__**

```python
from .chassi_validator import validar_chassi
```

- [ ] **Step 3: Testes**

`tests/motos_assai/test_chassi_validator.py`:

```python
from app import db
from app.motos_assai.models import AssaiModelo
from app.motos_assai.services import validar_chassi


def test_chassi_vazio():
    r = validar_chassi('', None)
    assert r['ok'] is False
    assert 'vazio' in r['mensagem']


def test_modelo_none(app):
    with app.app_context():
        r = validar_chassi('LA12345', None)
        assert r['ok'] is True


def test_modelo_sem_regex(app):
    """Modelo cadastrado mas sem regex_chassi → passa com aviso."""
    with app.app_context():
        m = AssaiModelo(codigo='TESTE_NO_REGEX', nome='T', regex_chassi=None)
        db.session.add(m); db.session.flush()
        r = validar_chassi('XYZ', m.id)
        assert r['ok'] is True
        assert 'sem regex' in r['mensagem']
        db.session.rollback()


def test_chassi_bate_regex(app):
    with app.app_context():
        m = AssaiModelo(codigo='TESTE_DOT_RX', nome='T', regex_chassi=r'LA\d+')
        db.session.add(m); db.session.flush()
        r = validar_chassi('LA12345', m.id)
        assert r['ok'] is True
        db.session.rollback()


def test_chassi_nao_bate_regex(app):
    with app.app_context():
        m = AssaiModelo(codigo='TESTE_DOT_RX2', nome='T', regex_chassi=r'LA\d+')
        db.session.add(m); db.session.flush()
        r = validar_chassi('XX99', m.id)
        assert r['ok'] is False
        assert 'não bate' in r['mensagem']
        db.session.rollback()


def test_anchors_aplicados_se_faltam(app):
    """Regex 'LA\\d+' sem anchors deve ser tratado como '^LA\\d+$'."""
    with app.app_context():
        m = AssaiModelo(codigo='TESTE_ANCHOR', nome='T', regex_chassi=r'LA\d+')
        db.session.add(m); db.session.flush()
        # 'XLA123' contém 'LA123' mas anchored não bate
        r = validar_chassi('XLA123', m.id)
        assert r['ok'] is False
        db.session.rollback()
```

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/services/chassi_validator.py
git add app/motos_assai/services/__init__.py
git add tests/motos_assai/test_chassi_validator.py
git commit -m "feat(motos_assai): chassi_validator (regex_chassi check, non-blocking)"
```

---

## Task 11: `moto_evento_service` helpers

**Files:**
- Create: `app/motos_assai/services/moto_evento_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Create: `tests/motos_assai/test_moto_evento_service.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/moto_evento_service.py`:

```python
"""Helpers para emitir e consultar eventos de moto.

Estado da moto = último evento por `ocorrido_em DESC`. Eventos são append-only.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List

from app import db
from app.motos_assai.models import (
    AssaiMotoEvento, EVENTOS_VALIDOS, EVENTOS_EM_ESTOQUE,
    EVENTO_ESTOQUE, EVENTO_MOTO_FALTANDO,
)


class EventoInvalidoError(Exception):
    pass


def emitir_evento(
    chassi: str,
    tipo: str,
    operador_id: Optional[int] = None,
    observacao: Optional[str] = None,
    dados_extras: Optional[Dict[str, Any]] = None,
) -> AssaiMotoEvento:
    """Cria um novo evento (NÃO commita — caller decide)."""
    if tipo not in EVENTOS_VALIDOS:
        raise EventoInvalidoError(f'Tipo inválido: {tipo}. Válidos: {EVENTOS_VALIDOS}')

    evento = AssaiMotoEvento(
        chassi=chassi.strip().upper(),
        tipo=tipo,
        operador_id=operador_id,
        observacao=observacao,
        dados_extras=dados_extras or {},
    )
    db.session.add(evento)
    db.session.flush()
    return evento


def ultimo_evento(chassi: str) -> Optional[AssaiMotoEvento]:
    """Retorna o evento mais recente ou None."""
    return (
        AssaiMotoEvento.query
        .filter_by(chassi=chassi.strip().upper())
        .order_by(AssaiMotoEvento.ocorrido_em.desc(), AssaiMotoEvento.id.desc())
        .first()
    )


def status_efetivo(chassi: str) -> Optional[str]:
    """String do tipo do último evento, ou None se moto sem eventos."""
    e = ultimo_evento(chassi)
    return e.tipo if e else None


def eventos_chassi(chassi: str, limit: int = 50) -> List[AssaiMotoEvento]:
    """Histórico do chassi (mais recente primeiro)."""
    return (
        AssaiMotoEvento.query
        .filter_by(chassi=chassi.strip().upper())
        .order_by(AssaiMotoEvento.ocorrido_em.desc(), AssaiMotoEvento.id.desc())
        .limit(limit)
        .all()
    )


def chassis_em_estoque(modelo_id: Optional[int] = None) -> List[str]:
    """Lista chassis cujo último evento está em EVENTOS_EM_ESTOQUE.

    Implementação: subquery do MAX(ocorrido_em, id) por chassi → join.
    """
    from app.motos_assai.models import AssaiMoto
    from sqlalchemy import func, and_

    sub = (
        db.session.query(
            AssaiMotoEvento.chassi,
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )

    q = (
        db.session.query(AssaiMotoEvento.chassi)
        .join(sub, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMotoEvento.tipo.in_(list(EVENTOS_EM_ESTOQUE)))
    )

    if modelo_id is not None:
        q = q.join(AssaiMoto, AssaiMoto.chassi == AssaiMotoEvento.chassi)\
             .filter(AssaiMoto.modelo_id == modelo_id)

    return [r[0] for r in q.all()]
```

- [ ] **Step 2: Atualizar __init__**

```python
from .moto_evento_service import (
    emitir_evento, ultimo_evento, status_efetivo, eventos_chassi,
    chassis_em_estoque, EventoInvalidoError,
)
```

- [ ] **Step 3: Testes**

`tests/motos_assai/test_moto_evento_service.py`:

```python
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services import (
    emitir_evento, ultimo_evento, status_efetivo, eventos_chassi,
    EventoInvalidoError,
)


def _criar_moto(app, chassi='ZZZ_TEST_001'):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    assert modelo, 'Pré-requisito: modelo DOT seeded'
    m = AssaiMoto(chassi=chassi, modelo_id=modelo.id)
    db.session.add(m); db.session.flush()
    return m


def test_emitir_tipo_invalido(app, admin_user):
    with app.app_context():
        with pytest.raises(EventoInvalidoError):
            emitir_evento('XXX', 'INEXISTENTE', admin_user.id)
        db.session.rollback()


def test_emitir_e_consultar_ultimo(app, admin_user):
    with app.app_context():
        _criar_moto(app, 'TST_ULTIMO_001')
        emitir_evento('TST_ULTIMO_001', EVENTO_ESTOQUE, admin_user.id)
        emitir_evento('TST_ULTIMO_001', EVENTO_MONTADA, admin_user.id)
        emitir_evento('TST_ULTIMO_001', EVENTO_DISPONIVEL, admin_user.id)
        last = ultimo_evento('TST_ULTIMO_001')
        assert last is not None
        assert last.tipo == EVENTO_DISPONIVEL
        assert status_efetivo('TST_ULTIMO_001') == EVENTO_DISPONIVEL
        db.session.rollback()


def test_status_chassi_sem_eventos(app):
    with app.app_context():
        assert status_efetivo('NAO_EXISTE_999') is None


def test_eventos_ordem_decrescente(app, admin_user):
    with app.app_context():
        _criar_moto(app, 'TST_HISTORICO_001')
        emitir_evento('TST_HISTORICO_001', EVENTO_ESTOQUE, admin_user.id)
        emitir_evento('TST_HISTORICO_001', EVENTO_MONTADA, admin_user.id)
        hist = eventos_chassi('TST_HISTORICO_001')
        assert len(hist) == 2
        assert hist[0].tipo == EVENTO_MONTADA  # mais recente primeiro
        db.session.rollback()


def test_chassi_normalizado_uppercase(app, admin_user):
    with app.app_context():
        _criar_moto(app, 'UPPER_001')
        emitir_evento('upper_001', EVENTO_ESTOQUE, admin_user.id)  # lowercase
        last = ultimo_evento('UPPER_001')
        assert last.chassi == 'UPPER_001'
        db.session.rollback()
```

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/services/moto_evento_service.py
git add app/motos_assai/services/__init__.py
git add tests/motos_assai/test_moto_evento_service.py
git commit -m "feat(motos_assai): moto_evento_service helpers (emit, status, history)"
```

---

## Task 12: `recebimento_service` (validação + registro + finalização)

**Files:**
- Create: `app/motos_assai/services/recebimento_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Create: `tests/motos_assai/test_recebimento_service.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/recebimento_service.py`:

```python
"""Service de recebimento físico — valida chassi contra recibo, registra conferência,
finaliza com `MOTO_FALTANDO` em batch para chassis declarados que não chegaram.

Lock pessimista via UNIQUE parcial em (recibo_id, chassi) — race retorna 409.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from sqlalchemy.exc import IntegrityError

from app import db
from app.motos_assai.models import (
    AssaiReciboMotochefe, AssaiReciboItem, AssaiMoto, AssaiModelo,
    RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
    RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA,
    DIVERGENCIA_MODELO_DIFERENTE, DIVERGENCIA_COR_DIFERENTE,
    DIVERGENCIA_CHASSI_EXTRA, DIVERGENCIA_MOTO_FALTANDO,
    EVENTO_ESTOQUE, EVENTO_MOTO_FALTANDO,
)
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.chassi_validator import validar_chassi


class RecebimentoConflictError(Exception):
    """Race condition em conferência simultânea — caller retorna 409."""


class RecebimentoValidationError(Exception):
    pass


def validar_chassi_contra_recibo(recibo_id: int, chassi: str) -> Dict[str, Any]:
    """Valida chassi contra o recibo (sem persistir).

    Retorna:
        {
            'ok': bool,
            'item_id': int | None,
            'modelo_id_esperado': int | None,
            'cor_esperada': str | None,
            'modelo_texto_recibo': str | None,
            'ja_conferido': bool,
            'na_nf': bool,           # false → CHASSI_EXTRA
            'regex_check': dict,     # do chassi_validator
            'mensagem': str,
        }
    """
    chassi_norm = chassi.strip().upper()
    item = AssaiReciboItem.query.filter_by(
        recibo_id=recibo_id, chassi=chassi_norm,
    ).first()

    if not item:
        return {
            'ok': False, 'item_id': None,
            'modelo_id_esperado': None, 'cor_esperada': None,
            'modelo_texto_recibo': None,
            'ja_conferido': False, 'na_nf': False,
            'regex_check': {'ok': True, 'mensagem': 'sem regex (chassi não no recibo)', 'regex_usado': None},
            'mensagem': f'Chassi {chassi_norm} NÃO está no recibo (CHASSI_EXTRA)',
        }

    regex_check = validar_chassi(chassi_norm, item.modelo_id)

    return {
        'ok': not item.conferido,
        'item_id': item.id,
        'modelo_id_esperado': item.modelo_id,
        'cor_esperada': item.cor_texto,
        'modelo_texto_recibo': item.modelo_texto_recibo,
        'ja_conferido': item.conferido,
        'na_nf': True,
        'regex_check': regex_check,
        'mensagem': (
            f'Já conferido em conferência anterior' if item.conferido
            else f'Chassi pertence ao recibo, modelo esperado: {item.modelo_id}'
        ),
    }


def registrar_conferencia(
    recibo_id: int,
    chassi: str,
    modelo_conferido_id: Optional[int],
    cor_conferida: Optional[str],
    qr_code_lido: bool,
    foto_s3_key: Optional[str],
    operador_id: int,
    avaria_fisica: bool = False,
) -> AssaiReciboItem:
    """Registra conferência de 1 chassi.

    - Cria AssaiMoto se não existe (modelo/cor conferidos).
    - Atualiza AssaiMoto se moto existe e cor/modelo conferidos divergem do cadastrado
      (exceção autorizada: recebimento físico é SOT).
    - Atualiza AssaiReciboItem.conferido=True.
    - Emite evento ESTOQUE.
    - Se chassi não está no recibo, marca tipo_divergencia=CHASSI_EXTRA.
    - Se modelo/cor divergem do recibo: tipo_divergencia=MODELO_DIFERENTE/COR_DIFERENTE.

    Raises:
        RecebimentoConflictError: race em UNIQUE (recibo_id, chassi).
        RecebimentoValidationError: dados inválidos.
    """
    chassi_norm = chassi.strip().upper()
    if not chassi_norm:
        raise RecebimentoValidationError('Chassi vazio')

    if not modelo_conferido_id:
        raise RecebimentoValidationError('Modelo conferido obrigatório')

    item = AssaiReciboItem.query.filter_by(
        recibo_id=recibo_id, chassi=chassi_norm,
    ).first()

    # Detecta divergências
    tipo_divergencia = None
    if not item:
        # Chassi NÃO está no recibo → CHASSI_EXTRA — cria item novo no recibo
        try:
            item = AssaiReciboItem(
                recibo_id=recibo_id,
                chassi=chassi_norm,
                modelo_id=modelo_conferido_id,
                modelo_texto_recibo=None,
                cor_texto=cor_conferida,
                tipo_divergencia=DIVERGENCIA_CHASSI_EXTRA,
                conferido=True,
                qr_code_lido=qr_code_lido,
                foto_s3_key=foto_s3_key,
            )
            db.session.add(item)
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            raise RecebimentoConflictError(
                f'Conflito: chassi {chassi_norm} sendo gravado simultaneamente'
            )
    else:
        if item.modelo_id and item.modelo_id != modelo_conferido_id:
            tipo_divergencia = DIVERGENCIA_MODELO_DIFERENTE
        elif item.cor_texto and cor_conferida and \
             item.cor_texto.upper() != (cor_conferida or '').upper():
            tipo_divergencia = DIVERGENCIA_COR_DIFERENTE
        if avaria_fisica:
            tipo_divergencia = 'AVARIA_FISICA'  # spec valid value

        item.conferido = True
        item.qr_code_lido = qr_code_lido
        item.foto_s3_key = foto_s3_key or item.foto_s3_key
        if tipo_divergencia:
            item.tipo_divergencia = tipo_divergencia

    # Cria/atualiza AssaiMoto
    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).with_for_update().first()
    if not moto:
        moto = AssaiMoto(
            chassi=chassi_norm,
            modelo_id=modelo_conferido_id,
            cor=cor_conferida,
            motor=item.motor if item else None,
        )
        db.session.add(moto)
    else:
        # Recebimento como SOT: UPDATE em cor/modelo se divergiu (exceção autorizada)
        if moto.modelo_id != modelo_conferido_id:
            moto.modelo_id = modelo_conferido_id
        if cor_conferida and moto.cor != cor_conferida:
            moto.cor = cor_conferida

    # Atualiza recibo para EM_CONFERENCIA se ainda AGUARDANDO
    recibo = AssaiReciboMotochefe.query.get(recibo_id)
    if recibo and recibo.status == RECIBO_STATUS_AGUARDANDO:
        recibo.status = RECIBO_STATUS_EM_CONFERENCIA

    # Emite evento ESTOQUE
    emitir_evento(
        chassi_norm, EVENTO_ESTOQUE,
        operador_id=operador_id,
        dados_extras={
            'recibo_id': recibo_id, 'item_id': item.id,
            'tipo_divergencia': tipo_divergencia,
        },
    )

    db.session.commit()
    return item


def finalizar_recebimento(
    recibo_id: int, operador_id: int,
    confirmar_faltantes: bool = False,
) -> AssaiReciboMotochefe:
    """Finaliza conferência. Para cada item NÃO conferido, marca MOTO_FALTANDO.

    Args:
        confirmar_faltantes: True → operador confirmou ciência. False e há faltantes
            → raise (caller mostra modal e re-chama com True).
    """
    recibo = AssaiReciboMotochefe.query.get_or_404(recibo_id)

    nao_conferidos: List[AssaiReciboItem] = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_id, conferido=False)
        .all()
    )

    if nao_conferidos and not confirmar_faltantes:
        raise RecebimentoValidationError(
            f'{len(nao_conferidos)} chassis não conferidos. Confirme MOTO_FALTANDO ou continue conferindo.'
        )

    # Marca cada não-conferido como MOTO_FALTANDO
    for item in nao_conferidos:
        item.tipo_divergencia = DIVERGENCIA_MOTO_FALTANDO
        emitir_evento(
            item.chassi, EVENTO_MOTO_FALTANDO,
            operador_id=operador_id,
            observacao='Declarado no recibo mas não chegou fisicamente',
            dados_extras={'recibo_id': recibo_id, 'item_id': item.id},
        )

    # Status final
    com_divergencia = (
        nao_conferidos
        or AssaiReciboItem.query.filter(
            AssaiReciboItem.recibo_id == recibo_id,
            AssaiReciboItem.tipo_divergencia.isnot(None),
        ).count() > 0
    )
    recibo.status = RECIBO_STATUS_COM_DIVERGENCIA if com_divergencia else RECIBO_STATUS_CONCLUIDO

    db.session.commit()
    return recibo
```

- [ ] **Step 2: Atualizar __init__**

```python
from .recebimento_service import (
    validar_chassi_contra_recibo, registrar_conferencia, finalizar_recebimento,
    RecebimentoConflictError, RecebimentoValidationError,
)
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/services/recebimento_service.py
git add app/motos_assai/services/__init__.py
git commit -m "feat(motos_assai): recebimento_service (validate, register, finalize)"
```

---

## Task 13: Wizard HTML (cópia adaptada do Hora)

**Files:**
- Create: `app/templates/motos_assai/recebimento/wizard.html`

**Instruções para o engenheiro:**
- LER `app/templates/hora/recebimento_wizard.html` (727 linhas) — referência
- COPIAR a estrutura do wizard A→B→C→D
- ADAPTAR os endpoints AJAX:
  - `/hora/recebimento/validar-chassi` → `/motos-assai/recebimento/validar-chassi`
  - `/hora/recebimento/registrar` → `/motos-assai/recebimento/registrar`
  - `/hora/recebimento/finalizar` → `/motos-assai/recebimento/finalizar`
- TROCAR `extends "hora/base.html"` por `extends "motos_assai/base_motos_assai.html"`
- TROCAR `current_user.tem_perm_hora(...)` por checagem simples
- USAR `recibo` no contexto em vez de `recebimento`
- MANTER: `html5-qrcode@2.3.8` CDN, mesmo facingMode, mesmo input chassi, mesmo modal de novo modelo

**Variável esperada do contexto** (passada pela rota Task 15):
- `recibo` (AssaiReciboMotochefe)
- `total_chassis` (int)
- `conferidos` (int)
- `pendentes` (int)
- `modelos` (list[AssaiModelo] ativos)

- [ ] **Step 1: Criar template (estrutura simplificada)**

`app/templates/motos_assai/recebimento/wizard.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<div class="d-flex align-items-center justify-content-between mb-3">
  <h2>Recebimento — Recibo #{{ recibo.id }}
    <span class="text-muted fw-normal">
      — {{ conferidos }} de {{ total_chassis }} conferido(s)
    </span>
  </h2>
  <div>
    <a href="{{ url_for('motos_assai.recibos_detalhe', recibo_id=recibo.id) }}"
       class="btn btn-sm btn-outline-secondary">
      <i class="fas fa-pause"></i> Pausar
    </a>
    <button type="button" class="btn btn-sm btn-success ms-2"
            id="btn-finalizar"
            {% if pendentes > 0 %}data-pendentes="{{ pendentes }}"{% endif %}>
      <i class="fas fa-check-double"></i> Finalizar
    </button>
  </div>
</div>

<div class="progress mb-3" style="height: 10px;">
  <div class="progress-bar bg-success"
       style="width: {{ (conferidos * 100 / total_chassis) if total_chassis else 0 }}%"></div>
</div>

<!-- Stepper -->
<div class="d-flex gap-2 mb-3 small" id="stepper">
  <span class="badge bg-primary" data-step="A">A. Chassi</span>
  <span class="badge bg-light border" data-step="B">B. Modelo</span>
  <span class="badge bg-light border" data-step="C">C. Cor + Foto</span>
  <span class="badge bg-light border" data-step="D">D. Confirmar</span>
</div>

<!-- ======= PASSO A: Chassi ======= -->
<div class="card p-3 mb-3" id="step-A">
  <h5>A. Ler chassi</h5>
  <div class="row">
    <div class="col-md-7">
      <div id="qr-reader" style="max-width:380px;"></div>
      <div class="d-flex gap-2 mt-2">
        <button type="button" id="btn-start-qr" class="btn btn-primary btn-sm">
          <i class="fas fa-camera"></i> Iniciar câmera
        </button>
        <button type="button" id="btn-stop-qr" class="btn btn-outline-secondary btn-sm d-none">
          <i class="fas fa-stop"></i> Parar
        </button>
      </div>
    </div>
    <div class="col-md-5">
      <label class="form-label">ou digite/escaneie com leitor USB</label>
      <input type="text" id="input-chassi" class="form-control" autofocus
             placeholder="Chassi (Enter para validar)" maxlength="50">
      <button type="button" id="btn-chassi-manual" class="btn btn-outline-primary mt-2">
        Validar chassi <i class="fas fa-arrow-right"></i>
      </button>

      <div id="alerta-chassi" class="mt-3 d-none"></div>
    </div>
  </div>
</div>

<!-- ======= PASSO B: Modelo ======= -->
<div class="card p-3 mb-3 d-none" id="step-B">
  <h5>B. Modelo</h5>
  <select id="select-modelo" class="form-select form-select-lg">
    <option value="">— Selecione —</option>
    {% for m in modelos %}
      <option value="{{ m.id }}">{{ m.codigo }} — {{ m.nome }}</option>
    {% endfor %}
  </select>
  <div class="d-flex gap-2 mt-3">
    <button type="button" id="btn-voltar-A" class="btn btn-secondary">
      <i class="fas fa-arrow-left"></i> Voltar
    </button>
    <button type="button" id="btn-avancar-B" class="btn btn-primary ms-auto">
      Próximo <i class="fas fa-arrow-right"></i>
    </button>
  </div>
</div>

<!-- ======= PASSO C: Cor + Foto ======= -->
<div class="card p-3 mb-3 d-none" id="step-C">
  <h5>C. Cor e foto</h5>
  <div class="mb-3">
    <label class="form-label">Cor</label>
    <input type="text" id="input-cor" class="form-control" placeholder="CINZA / PRETO / AZUL...">
  </div>
  <div class="mb-3">
    <label class="form-label">Foto da moto (opcional)</label>
    <input type="file" id="input-foto" class="form-control"
           accept="image/*" capture="environment">
  </div>
  <div class="form-check mb-3">
    <input type="checkbox" id="chk-avaria" class="form-check-input">
    <label for="chk-avaria" class="form-check-label">Avaria física detectada</label>
  </div>
  <div class="d-flex gap-2">
    <button type="button" id="btn-voltar-B" class="btn btn-secondary">
      <i class="fas fa-arrow-left"></i> Voltar
    </button>
    <button type="button" id="btn-avancar-C" class="btn btn-primary ms-auto">
      Confirmar conferência <i class="fas fa-check"></i>
    </button>
  </div>
</div>

<!-- ======= PASSO D: Confirmação visual ======= -->
<div class="card p-3 mb-3 d-none" id="step-D">
  <h5>D. Conferência registrada</h5>
  <div id="resumo-conferencia"></div>
  <button type="button" id="btn-proximo-chassi" class="btn btn-primary mt-3">
    <i class="fas fa-redo"></i> Próximo chassi
  </button>
</div>

<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"
        integrity="sha384-c9d8RFSL+sJ0dC0WGqK7tQXg4/c5++8KkF+xbSPq3ji10/wfKLtAVk0M3IY+XJ7q"
        crossorigin="anonymous"></script>
<script>
window.MOTOS_ASSAI_RECEBIMENTO = {
  reciboId: {{ recibo.id }},
  endpoints: {
    validar: '{{ url_for("motos_assai.recebimento_validar_chassi") }}',
    registrar: '{{ url_for("motos_assai.recebimento_registrar") }}',
    finalizar: '{{ url_for("motos_assai.recebimento_finalizar", recibo_id=recibo.id) }}',
    fotoUpload: '{{ url_for("motos_assai.recebimento_foto_upload") }}',
  },
};
</script>
<script src="{{ url_for('static', filename='motos_assai/js/recebimento_wizard.js') }}"></script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/motos_assai/recebimento/wizard.html
git commit -m "feat(motos_assai): recebimento wizard template (A→B→C→D adaptado de Hora)"
```

---

## Task 14: JS do wizard (`recebimento_wizard.js`)

**Files:**
- Create: `app/static/motos_assai/js/recebimento_wizard.js`

- [ ] **Step 1: JS**

`app/static/motos_assai/js/recebimento_wizard.js`:

```javascript
/**
 * Wizard de recebimento Motos Assaí — A→B→C→D
 *
 * Fluxo:
 * A: scan QR ou digita chassi → POST /validar-chassi → recebe modelo/cor esperados
 * B: operador confirma/troca modelo
 * C: operador confirma/troca cor + foto opcional + flag avaria
 * D: POST /registrar → grava AssaiReciboItem + AssaiMoto + evento ESTOQUE
 *    → reset para chassi seguinte
 */
(function() {
  const cfg = window.MOTOS_ASSAI_RECEBIMENTO;
  if (!cfg) { console.error('cfg ausente'); return; }

  const state = {
    chassi: null,
    qrLido: false,
    modeloId: null,
    cor: null,
    fotoS3Key: null,
    avaria: false,
    chassiContext: null,
  };

  // ============== Helpers ==============

  function setStep(step) {
    document.querySelectorAll('[id^="step-"]').forEach(el => el.classList.add('d-none'));
    document.getElementById('step-' + step).classList.remove('d-none');
    document.querySelectorAll('#stepper .badge').forEach(b => {
      b.classList.toggle('bg-primary', b.dataset.step === step);
      b.classList.toggle('bg-light', b.dataset.step !== step);
      b.classList.toggle('border', b.dataset.step !== step);
    });
  }

  function showAlerta(level, html) {
    const el = document.getElementById('alerta-chassi');
    el.className = `alert alert-${level} small mt-3`;
    el.innerHTML = html;
    el.classList.remove('d-none');
  }

  // ============== QR scanner ==============

  let html5Qr = null;
  function startQr() {
    if (!window.isSecureContext) {
      showAlerta('warning', 'Câmera requer HTTPS. Use leitor USB ou digite manualmente.');
      return;
    }
    html5Qr = new Html5Qrcode('qr-reader');
    html5Qr.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: 240 },
      (txt) => {
        state.qrLido = true;
        document.getElementById('input-chassi').value = txt.trim().toUpperCase();
        stopQr();
        validarChassi(txt);
      }
    ).then(() => {
      document.getElementById('btn-start-qr').classList.add('d-none');
      document.getElementById('btn-stop-qr').classList.remove('d-none');
    }).catch(e => showAlerta('danger', 'Erro ao iniciar câmera: ' + e));
  }

  function stopQr() {
    if (!html5Qr) return;
    html5Qr.stop().then(() => {
      document.getElementById('btn-start-qr').classList.remove('d-none');
      document.getElementById('btn-stop-qr').classList.add('d-none');
    }).catch(() => {});
  }

  // ============== AJAX ==============

  async function validarChassi(chassi) {
    const norm = chassi.trim().toUpperCase();
    if (!norm) { showAlerta('warning', 'Digite um chassi.'); return; }

    state.chassi = norm;

    const r = await fetch(cfg.endpoints.validar, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({recibo_id: cfg.reciboId, chassi: norm}),
    });
    const data = await r.json();

    state.chassiContext = data;

    if (data.ja_conferido) {
      showAlerta('warning', `Chassi ${norm} já foi conferido. Avance para o próximo.`);
      return;
    }

    if (!data.na_nf) {
      showAlerta('danger', `<strong>${norm}</strong> NÃO está no recibo (CHASSI_EXTRA). Conferência continua mas será marcada como divergência.`);
    } else {
      let msg = `Chassi pertence ao recibo. Modelo esperado: <code>${data.modelo_texto_recibo || '-'}</code>`;
      if (data.regex_check && !data.regex_check.ok) {
        msg += `<br><span class="text-warning">⚠ Regex: ${data.regex_check.mensagem}</span>`;
      }
      showAlerta('info', msg);
    }

    // Pré-seleciona modelo no Step B se conhecido
    if (data.modelo_id_esperado) {
      state.modeloId = data.modelo_id_esperado;
      document.getElementById('select-modelo').value = data.modelo_id_esperado;
    }
    if (data.cor_esperada) {
      state.cor = data.cor_esperada;
    }

    setStep('B');
  }

  async function registrarConferencia() {
    if (!state.chassi || !state.modeloId) {
      alert('Chassi e modelo são obrigatórios.');
      return;
    }

    const payload = {
      recibo_id: cfg.reciboId,
      chassi: state.chassi,
      modelo_id: state.modeloId,
      cor: state.cor,
      qr_code_lido: state.qrLido,
      foto_s3_key: state.fotoS3Key,
      avaria_fisica: state.avaria,
    };

    const r = await fetch(cfg.endpoints.registrar, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });

    if (r.status === 409) {
      alert('Conflito: outro operador conferindo este chassi simultaneamente. Tente novamente.');
      return;
    }

    const data = await r.json();
    if (!data.ok) {
      alert('Erro: ' + (data.erro || 'desconhecido'));
      return;
    }

    document.getElementById('resumo-conferencia').innerHTML =
      `<div class="alert alert-success">` +
      `Chassi <code>${state.chassi}</code> conferido com sucesso.<br>` +
      (data.tipo_divergencia ? `<strong>⚠ ${data.tipo_divergencia}</strong><br>` : '') +
      `Total conferido: ${data.conferidos} / ${data.total}` +
      `</div>`;
    setStep('D');
  }

  async function uploadFoto(file) {
    const fd = new FormData();
    fd.append('foto', file);
    fd.append('recibo_id', cfg.reciboId);
    fd.append('chassi', state.chassi);
    const r = await fetch(cfg.endpoints.fotoUpload, {method: 'POST', body: fd});
    const data = await r.json();
    if (data.ok) state.fotoS3Key = data.s3_key;
    return data.ok;
  }

  function reset() {
    state.chassi = null;
    state.qrLido = false;
    state.modeloId = null;
    state.cor = null;
    state.fotoS3Key = null;
    state.avaria = false;
    state.chassiContext = null;
    document.getElementById('input-chassi').value = '';
    document.getElementById('select-modelo').value = '';
    document.getElementById('input-cor').value = '';
    document.getElementById('input-foto').value = '';
    document.getElementById('chk-avaria').checked = false;
    document.getElementById('alerta-chassi').classList.add('d-none');
    setStep('A');
    document.getElementById('input-chassi').focus();
  }

  // ============== Handlers ==============

  document.getElementById('btn-start-qr').addEventListener('click', startQr);
  document.getElementById('btn-stop-qr').addEventListener('click', stopQr);

  document.getElementById('btn-chassi-manual').addEventListener('click', () => {
    validarChassi(document.getElementById('input-chassi').value);
  });
  document.getElementById('input-chassi').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      validarChassi(e.target.value);
    }
  });

  document.getElementById('btn-voltar-A').addEventListener('click', () => setStep('A'));
  document.getElementById('btn-avancar-B').addEventListener('click', () => {
    state.modeloId = parseInt(document.getElementById('select-modelo').value, 10) || null;
    if (!state.modeloId) {
      alert('Selecione um modelo.');
      return;
    }
    if (state.cor) {
      document.getElementById('input-cor').value = state.cor;
    }
    setStep('C');
  });

  document.getElementById('btn-voltar-B').addEventListener('click', () => setStep('B'));
  document.getElementById('btn-avancar-C').addEventListener('click', async () => {
    state.cor = document.getElementById('input-cor').value.trim().toUpperCase() || null;
    state.avaria = document.getElementById('chk-avaria').checked;
    const fileInput = document.getElementById('input-foto');
    if (fileInput.files && fileInput.files[0]) {
      const ok = await uploadFoto(fileInput.files[0]);
      if (!ok) {
        if (!confirm('Falha ao subir foto. Continuar mesmo assim?')) return;
      }
    }
    await registrarConferencia();
  });

  document.getElementById('btn-proximo-chassi').addEventListener('click', reset);

  document.getElementById('btn-finalizar').addEventListener('click', async () => {
    const pend = document.getElementById('btn-finalizar').dataset.pendentes;
    let confirmar_faltantes = false;
    if (pend && parseInt(pend, 10) > 0) {
      if (!confirm(`Há ${pend} chassis não conferidos. Finalizar marca-os como MOTO_FALTANDO. Continuar?`)) return;
      confirmar_faltantes = true;
    }
    const r = await fetch(cfg.endpoints.finalizar, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({confirmar_faltantes}),
    });
    const data = await r.json();
    if (data.ok) {
      window.location.href = data.redirect;
    } else {
      alert('Erro: ' + (data.erro || ''));
    }
  });

  // ============== Init ==============
  setStep('A');
  document.getElementById('input-chassi').focus();
})();
```

- [ ] **Step 2: Commit**

```bash
git add app/static/motos_assai/js/recebimento_wizard.js
git commit -m "feat(motos_assai): recebimento wizard JS (A→B→C→D, html5-qrcode, AJAX)"
```

---

## Task 15: Endpoints AJAX do recebimento

**Files:**
- Create: `app/motos_assai/routes/recebimento.py`
- Modify: `app/motos_assai/routes/__init__.py`

- [ ] **Step 1: Rotas**

`app/motos_assai/routes/recebimento.py`:

```python
import io
from flask import (
    render_template, request, redirect, url_for, flash, jsonify, current_app,
)
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    get_recibo, validar_chassi_contra_recibo, registrar_conferencia,
    finalizar_recebimento, listar_modelos,
    RecebimentoConflictError, RecebimentoValidationError,
)
from app.motos_assai.models import AssaiReciboItem
from app.utils.file_storage import FileStorage


@motos_assai_bp.route('/recibos/<int:recibo_id>/conferir')
@login_required
@require_motos_assai
def recebimento_wizard(recibo_id):
    recibo = get_recibo(recibo_id)
    total = AssaiReciboItem.query.filter_by(recibo_id=recibo_id).count()
    conferidos = AssaiReciboItem.query.filter_by(
        recibo_id=recibo_id, conferido=True,
    ).count()
    return render_template(
        'motos_assai/recebimento/wizard.html',
        recibo=recibo,
        total_chassis=total,
        conferidos=conferidos,
        pendentes=total - conferidos,
        modelos=listar_modelos(somente_ativos=True),
    )


@motos_assai_bp.route('/recebimento/validar-chassi', methods=['POST'])
@login_required
@require_motos_assai
def recebimento_validar_chassi():
    data = request.get_json(silent=True) or {}
    recibo_id = data.get('recibo_id')
    chassi = data.get('chassi', '')
    if not recibo_id or not chassi:
        return jsonify({'ok': False, 'erro': 'recibo_id e chassi obrigatórios'}), 400
    resultado = validar_chassi_contra_recibo(int(recibo_id), chassi)
    return jsonify(resultado)


@motos_assai_bp.route('/recebimento/registrar', methods=['POST'])
@login_required
@require_motos_assai
def recebimento_registrar():
    data = request.get_json(silent=True) or {}
    try:
        item = registrar_conferencia(
            recibo_id=int(data['recibo_id']),
            chassi=data['chassi'],
            modelo_conferido_id=int(data['modelo_id']),
            cor_conferida=data.get('cor'),
            qr_code_lido=bool(data.get('qr_code_lido')),
            foto_s3_key=data.get('foto_s3_key'),
            operador_id=current_user.id,
            avaria_fisica=bool(data.get('avaria_fisica')),
        )
    except RecebimentoConflictError as e:
        return jsonify({'ok': False, 'erro': str(e), 'retry': True}), 409
    except RecebimentoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception as e:
        current_app.logger.exception('Erro ao registrar conferência')
        return jsonify({'ok': False, 'erro': str(e)}), 500

    total = AssaiReciboItem.query.filter_by(recibo_id=item.recibo_id).count()
    conferidos = AssaiReciboItem.query.filter_by(
        recibo_id=item.recibo_id, conferido=True,
    ).count()
    return jsonify({
        'ok': True,
        'item_id': item.id,
        'tipo_divergencia': item.tipo_divergencia,
        'total': total,
        'conferidos': conferidos,
    })


@motos_assai_bp.route('/recebimento/finalizar/<int:recibo_id>', methods=['POST'])
@login_required
@require_motos_assai
def recebimento_finalizar(recibo_id):
    data = request.get_json(silent=True) or {}
    try:
        recibo = finalizar_recebimento(
            recibo_id=recibo_id,
            operador_id=current_user.id,
            confirmar_faltantes=bool(data.get('confirmar_faltantes')),
        )
    except RecebimentoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    return jsonify({
        'ok': True,
        'status': recibo.status,
        'redirect': url_for('motos_assai.recibos_detalhe', recibo_id=recibo.id),
    })


@motos_assai_bp.route('/recebimento/foto-upload', methods=['POST'])
@login_required
@require_motos_assai
def recebimento_foto_upload():
    f = request.files.get('foto')
    recibo_id = request.form.get('recibo_id')
    chassi = (request.form.get('chassi') or '').strip().upper()
    if not f or not recibo_id or not chassi:
        return jsonify({'ok': False, 'erro': 'foto, recibo_id, chassi obrigatórios'}), 400

    buf = io.BytesIO(f.read())
    buf.name = f.filename
    s3_key = FileStorage().save_file(
        buf,
        folder=f'motos_assai/recebimento/{recibo_id}',
        filename=f'{chassi}_{f.filename}',
        allowed_extensions=['jpg', 'jpeg', 'png', 'webp'],
    )
    return jsonify({'ok': True, 's3_key': s3_key})
```

- [ ] **Step 2: Importar route no blueprint**

```python
from app.motos_assai.routes import recebimento  # noqa: E402,F401
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/routes/recebimento.py
git add app/motos_assai/routes/__init__.py
git commit -m "feat(motos_assai): recebimento AJAX endpoints (validar, registrar, finalizar, foto)"
```

---

## Task 16: Testes do `recebimento_service`

**Files:**
- Create: `tests/motos_assai/test_recebimento_service.py`

- [ ] **Step 1: Tests**

`tests/motos_assai/test_recebimento_service.py`:

```python
import pytest
from app import db
from app.motos_assai.models import (
    AssaiCompraMotochefe, AssaiReciboMotochefe, AssaiReciboItem, AssaiModelo,
    AssaiPedidoVenda, AssaiMoto, AssaiMotoEvento,
    RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA,
    EVENTO_ESTOQUE, EVENTO_MOTO_FALTANDO,
    DIVERGENCIA_MOTO_FALTANDO, DIVERGENCIA_MODELO_DIFERENTE,
)
from app.motos_assai.services import (
    validar_chassi_contra_recibo, registrar_conferencia, finalizar_recebimento,
    RecebimentoValidationError,
)
from app.motos_assai.services.compra_service import criar_consolidado


def _setup_recibo(app, admin_user, chassis_no_recibo: list[str]):
    """Cria pedido + compra + recibo + N items."""
    p = AssaiPedidoVenda(numero=f'TEST-RECEB-{id(_setup_recibo)}',
                         status='ABERTO', criado_por_id=admin_user.id)
    db.session.add(p); db.session.flush()
    compra = criar_consolidado([p.id], None, admin_user.id)

    modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
    recibo = AssaiReciboMotochefe(
        compra_id=compra.id,
        status='RECEBIDO_AGUARDANDO_CONFERENCIA',
        criado_por_id=admin_user.id,
    )
    db.session.add(recibo); db.session.flush()

    for ch in chassis_no_recibo:
        db.session.add(AssaiReciboItem(
            recibo_id=recibo.id, chassi=ch,
            modelo_id=modelo_dot.id,
            modelo_texto_recibo='DOT 1000W',
            cor_texto='CINZA',
        ))
    db.session.flush()
    return recibo, modelo_dot


def test_validar_chassi_no_recibo(app, admin_user):
    with app.app_context():
        recibo, _ = _setup_recibo(app, admin_user, ['TEST_VAL_001'])
        r = validar_chassi_contra_recibo(recibo.id, 'TEST_VAL_001')
        assert r['ok'] is True
        assert r['na_nf'] is True
        assert r['ja_conferido'] is False
        db.session.rollback()


def test_validar_chassi_extra(app, admin_user):
    with app.app_context():
        recibo, _ = _setup_recibo(app, admin_user, ['TEST_VAL_002'])
        r = validar_chassi_contra_recibo(recibo.id, 'CHASSI_EXTRA_999')
        assert r['na_nf'] is False
        db.session.rollback()


def test_registrar_cria_moto_e_evento(app, admin_user):
    with app.app_context():
        recibo, modelo = _setup_recibo(app, admin_user, ['TEST_REG_001'])
        item = registrar_conferencia(
            recibo_id=recibo.id, chassi='TEST_REG_001',
            modelo_conferido_id=modelo.id, cor_conferida='CINZA',
            qr_code_lido=False, foto_s3_key=None,
            operador_id=admin_user.id,
        )
        assert item.conferido is True
        moto = AssaiMoto.query.filter_by(chassi='TEST_REG_001').first()
        assert moto is not None
        eventos = AssaiMotoEvento.query.filter_by(chassi='TEST_REG_001').all()
        assert len(eventos) == 1
        assert eventos[0].tipo == EVENTO_ESTOQUE
        db.session.rollback()


def test_registrar_modelo_divergente(app, admin_user):
    with app.app_context():
        recibo, modelo_dot = _setup_recibo(app, admin_user, ['TEST_DIV_001'])
        modelo_outro = AssaiModelo.query.filter_by(codigo='X11_MINI').first()
        item = registrar_conferencia(
            recibo_id=recibo.id, chassi='TEST_DIV_001',
            modelo_conferido_id=modelo_outro.id, cor_conferida='CINZA',
            qr_code_lido=False, foto_s3_key=None, operador_id=admin_user.id,
        )
        assert item.tipo_divergencia == DIVERGENCIA_MODELO_DIFERENTE
        db.session.rollback()


def test_finalizar_marca_faltantes(app, admin_user):
    with app.app_context():
        recibo, modelo = _setup_recibo(app, admin_user,
                                        ['TEST_FALT_A', 'TEST_FALT_B'])
        # Confere apenas 1
        registrar_conferencia(
            recibo_id=recibo.id, chassi='TEST_FALT_A',
            modelo_conferido_id=modelo.id, cor_conferida='CINZA',
            qr_code_lido=False, foto_s3_key=None, operador_id=admin_user.id,
        )

        # Finaliza sem confirmar → erro
        with pytest.raises(RecebimentoValidationError):
            finalizar_recebimento(recibo.id, admin_user.id,
                                  confirmar_faltantes=False)

        # Finaliza com confirmação
        recibo_final = finalizar_recebimento(
            recibo.id, admin_user.id, confirmar_faltantes=True,
        )
        assert recibo_final.status == RECIBO_STATUS_COM_DIVERGENCIA

        # Item B (não conferido) deve ter MOTO_FALTANDO
        item_b = AssaiReciboItem.query.filter_by(
            recibo_id=recibo.id, chassi='TEST_FALT_B',
        ).first()
        assert item_b.tipo_divergencia == DIVERGENCIA_MOTO_FALTANDO

        # Evento MOTO_FALTANDO emitido
        ev = AssaiMotoEvento.query.filter_by(
            chassi='TEST_FALT_B', tipo=EVENTO_MOTO_FALTANDO,
        ).first()
        assert ev is not None
        db.session.rollback()


def test_finalizar_sem_pendentes_concluido(app, admin_user):
    with app.app_context():
        recibo, modelo = _setup_recibo(app, admin_user, ['TEST_OK_001'])
        registrar_conferencia(
            recibo_id=recibo.id, chassi='TEST_OK_001',
            modelo_conferido_id=modelo.id, cor_conferida='CINZA',
            qr_code_lido=False, foto_s3_key=None, operador_id=admin_user.id,
        )
        recibo_final = finalizar_recebimento(recibo.id, admin_user.id)
        assert recibo_final.status == RECIBO_STATUS_CONCLUIDO
        db.session.rollback()
```

- [ ] **Step 2: Rodar todos os testes**

```bash
pytest tests/motos_assai/ -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/motos_assai/test_recebimento_service.py
git commit -m "test(motos_assai): recebimento_service (validate, register, finalize, MOTO_FALTANDO)"
```

---

## Task 17: Atualizar CLAUDE.md

**Files:**
- Modify: `app/motos_assai/CLAUDE.md`

- [ ] **Step 1: Anexar seção Plano 2B**

````markdown

---

## Plano 2B implementado (2026-XX-XX)

### Recibo Motochefe + Recebimento físico

**Parsers do recibo Motochefe**:
- `MotochefeReciboPdfExtractor` (`parsers/motochefe_recibo_pdf_extractor.py`): pdfplumber + `extract_tables()` com lines strategy. Detecta colunas CHASSI/MOTOR/COR no header. Extrai data, equipe (HAROLDO SP), conferente, total declarado.
- `MotochefeReciboXlsxExtractor` (`parsers/motochefe_recibo_xlsx_extractor.py`): openpyxl `data_only=True`. Localiza header da tabela pela presença de células CHASSI.
- `motochefe_recibo_llm_fallback.py`: Haiku 4.5 → Sonnet 4.6. Aceita PDF (document block) ou XLSX serializado como texto.

**Limiar de confiança**: `CONFIANCA_LIMIAR = 0.80` em `recibo_service`. Aciona LLM quando `chassis_extraidos / total_declarado < 0.80`.

**Wizard de recebimento físico**:
- Template `recebimento/wizard.html` com 4 passos A→B→C→D + indicador de progresso
- JS `recebimento_wizard.js` com `html5-qrcode@2.3.8` para câmera mobile + leitor USB (Enter dispara) + digitação manual
- Foto opcional em `<input type="file" capture="environment">` → upload S3 (`motos_assai/recebimento/<recibo_id>/<chassi>_<filename>`)

**Endpoints AJAX**:
- `POST /motos-assai/recebimento/validar-chassi` → retorna `{ok, na_nf, ja_conferido, modelo_id_esperado, cor_esperada, regex_check, mensagem}`
- `POST /motos-assai/recebimento/registrar` → cria/atualiza `assai_moto`, `assai_recibo_item.conferido=True`, emite evento `ESTOQUE`
- `POST /motos-assai/recebimento/finalizar/<recibo_id>` → marca pendentes como `MOTO_FALTANDO` em batch
- `POST /motos-assai/recebimento/foto-upload` → S3 + retorna s3_key

**Race / lock**:
- UNIQUE parcial em `(recibo_id, chassi)` (já existe via Plano 1 schema; Migration 07 garante idempotente)
- `with_for_update()` em `AssaiMoto.query.filter_by(chassi=...).with_for_update().first()`
- IntegrityError → `RecebimentoConflictError` → HTTP 409 com `{retry: true}`

**Recebimento como SOT** (exceção autorizada à invariante 3):
- Se modelo/cor conferidos divergem da NF, aplica UPDATE em `AssaiMoto.cor` e `AssaiMoto.modelo_id` (espelho de `_aplicar_correcao_moto_se_divergir` do Hora)

**Status do recibo**:
- `RECEBIDO_AGUARDANDO_CONFERENCIA` → `EM_CONFERENCIA` (primeiro chassi conferido) → `CONCLUIDO` (zero divergência) ou `COM_DIVERGENCIA`

**Próximo: Plano 3** (montagem, disponibilizar, separação, Excel Q.P.A., NF Q.P.A. import + match, polish).
````

- [ ] **Step 2: Commit**

```bash
git add app/motos_assai/CLAUDE.md
git commit -m "docs(motos_assai): document Plan 2B (recibo + recebimento físico)"
```

---

## Self-review

**Spec coverage**:
- §5.3 (Recibo Motochefe entra) — Tasks 1-9. ✓
- §5.4 (Recebimento físico wizard) — Tasks 10-15. ✓
- §8.3 (parser recibo PDF + XLSX) — Tasks 1, 2, 3. ✓

**Type consistency**:
- `validar_chassi_contra_recibo(recibo_id, chassi)` retorna dict consistente entre service (Task 12) e route (Task 15)
- `registrar_conferencia(...)` argumentos batem entre service (Task 12), route (Task 15) e JS (Task 14)
- `finalizar_recebimento(recibo_id, operador_id, confirmar_faltantes=False)` consistente
- Endpoints `recebimento_validar_chassi`, `recebimento_registrar`, `recebimento_finalizar`, `recebimento_foto_upload` referenciados no JS via `cfg.endpoints` definido no template (Task 13)

**Não coberto** (vai para Plano 3):
- Tela de montagem (etapa 5 do spec)
- Tela de disponibilizar (etapa 6)
- Tela de separação (etapa 7)
- Excel Q.P.A. + NF Q.P.A. import (etapa 8)

---

**Plano 2B salvo em** `docs/superpowers/plans/2026-05-07-motos-assai-recibo-recebimento.md` — 17 tasks. Próximo: Plano 3.
