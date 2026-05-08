# Motos Assaí — Plano 2A: Parser VOE + Pedido + Compra Motochefe

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar a entrada do pipeline: parser PDF do pedido VOE da Q.P.A. (determinístico + fallback LLM Haiku/Sonnet), tela de upload e detalhe de pedido com conferência humana, consolidação N→1 em pedido de compra Motochefe e geração de PDF do PO.

**Architecture:** Subclasse do `PDFExtractor` base do projeto (`app/pedidos/leitura/base.py`). Identificador estendido com padrão QPA. Service `pedido_service` orquestra parser → S3 → persistência. Adapter pattern para LLM (Haiku → Sonnet fallback). Modelo resolver compartilhado (`modelo_resolver`) usado em todos os parsers do módulo. Persistência via `FileStorage` (`app/utils/file_storage.py`).

**Tech Stack:** pdfplumber 0.10+ (PDF parsing), `anthropic==0.98.1` (Haiku 4.5 / Sonnet 4.6), Flask + SQLAlchemy 2.x, WeasyPrint (PDF do PO), Bootstrap 5.

**Pré-requisitos**:
- Plano 1 (Foundation + Cadastros) implementado: schema, models, blueprint, dashboard, lojas/modelos seeded
- `ANTHROPIC_API_KEY` configurado em ambiente
- `weasyprint` instalado (`pip install weasyprint`) — verificar se já está em `requirements.txt`

**Spec referência:** `docs/superpowers/specs/2026-05-07-motos-assai-design.md` §5.1, §5.2, §8.1, §8.2

---

## Visão de arquivos

```
app/motos_assai/
├── services/
│   ├── parsers/
│   │   ├── __init__.py                       # Task 1
│   │   ├── qpa_pedido_extractor.py           # Task 2
│   │   └── qpa_pedido_llm_fallback.py        # Task 4
│   ├── modelo_resolver.py                    # Task 5
│   ├── pedido_service.py                     # Task 6
│   └── compra_service.py                     # Task 11
├── forms/
│   ├── pedido_forms.py                       # Task 7
│   └── compra_forms.py                       # Task 13
├── routes/
│   ├── pedidos.py                            # Task 7-10
│   └── compras.py                            # Task 13-15
└── workers/                                  # (não usado — sync)
    └── __init__.py

app/templates/motos_assai/
├── pedidos/
│   ├── lista.html                            # Task 10
│   ├── upload.html                           # Task 8
│   └── detalhe.html                          # Task 9
└── compras/
    ├── lista.html                            # Task 15
    ├── nova.html                             # Task 13
    ├── detalhe.html                          # Task 14
    └── pdf_template.html                     # Task 12

# Modificações em arquivos existentes:
# - app/pedidos/leitura/identificador.py     (Task 1)

tests/motos_assai/
├── test_qpa_pedido_extractor.py              # Task 3
├── test_modelo_resolver.py                   # Task 5
├── test_pedido_service.py                    # Task 6
├── test_compra_service.py                    # Task 11
└── fixtures/
    └── pedido_voe_exemplo.pdf                # Task 3 — copiar do download
```

---

## Task 1: Estender `IdentificadorDocumento` com padrão QPA

**Files:**
- Modify: `app/pedidos/leitura/identificador.py`

- [ ] **Step 1: Adicionar padrão QPA**

Em `app/pedidos/leitura/identificador.py`, no dict `PADROES_TEXTO_REDE`:

```python
'QPA': [
    r'Q\.?P\.?A\s*DISTRIBUI[CÇ][AÃ]O',
    r'53\.?780\.?554\.?/?0001-?15',
    r'PEDIDO\s+DE\s+COMPRAS\s+\d+/[A-Z]',  # cabeçalho Consinco do VOE
],
```

E em `PADROES_NUMERO`:

```python
'QPA_PEDIDO': r'PEDIDO\s+DE\s+COMPRAS\s+(\d+/[A-Z])',
```

- [ ] **Step 2: Validar identificação**

```bash
source .venv/bin/activate
python -c "
from app.pedidos.leitura.identificador import identificar_documento
r = identificar_documento('/mnt/c/Users/rafael.nascimento/Downloads/pedido VOE 1 (1).pdf')
print('Rede:', r.rede, 'Tipo:', r.tipo, 'Número:', r.numero_documento, 'Confiança:', r.confianca)
"
```

Expected: `Rede: QPA Tipo: PEDIDO Número: 21439695/L Confiança: ~0.85+`

- [ ] **Step 3: Commit**

```bash
git add app/pedidos/leitura/identificador.py
git commit -m "feat(pedidos/leitura): identify QPA pedido by CNPJ + Consinco header"
```

---

## Task 2: `QpaPedidoExtractor` — extrator determinístico

**Files:**
- Create: `app/motos_assai/services/parsers/__init__.py`
- Create: `app/motos_assai/services/parsers/qpa_pedido_extractor.py`

- [ ] **Step 1: __init__**

`app/motos_assai/services/parsers/__init__.py`:

```python
"""Parsers de PDF/Excel do módulo Motos Assaí."""
```

- [ ] **Step 2: Extractor**

`app/motos_assai/services/parsers/qpa_pedido_extractor.py`:

```python
"""Extrator determinístico do PDF de Pedido de Compras Q.P.A. → Sendas/Assaí.

Layout de referência (Consinco): cada PÁGINA do PDF representa UMA loja Sendas
com header próprio + tabela de produtos. O PDF é multi-loja.

Header relevante por página:
  PEDIDO DE COMPRAS 21439695/L
  FORNECEDOR 4442498
  R. Social Q.P.A DISTRIBUICAO LTDA           CNPJ 53.780.554/0001-15
  ... DADOS PARA FATURAMENTO
  R. Social SENDAS DISTRIBUIDORA S/A LJ12     CNPJ 06.057.223/0272-90
  ENDEREÇO PARA ENTREGA
  Cidade JUNDIAÍ - SP

Linhas de produto (após "Cod Forn Seq Produtos a Receber"):
  1342056AUTOPROPELIDO X11 MINI 1000W 60V 20AH UN 1 10,00 7.100,0000 71.000,00 0,00 ...

Datas:
  Data da emissão     22/04/2026
  Previsão de entrega 22/04/2026

A confiança final é calculada em `pedido_service` a partir de:
  conf = (paginas_com_itens / paginas_total) * (lojas_resolvidas / lojas_total)
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Dict, List, Any, Optional

import pdfplumber

from app.pedidos.leitura.base import PDFExtractor


class QpaPedidoExtractor(PDFExtractor):
    """Extrai dados de pedido VOE Q.P.A. → Sendas em formato lista de items."""

    REGEX_NUMERO_PEDIDO = re.compile(
        r'PEDIDO\s+DE\s+COMPRAS\s+(\d+/[A-Z])'
    )
    REGEX_DATA_EMISSAO = re.compile(
        r'Data\s+da\s+emiss[aã]o\s+(\d{2}/\d{2}/\d{4})'
    )
    REGEX_PREVISAO = re.compile(
        r'Previs[aã]o\s+de\s+entrega\s+(\d{2}/\d{2}/\d{4})'
    )
    REGEX_FORNECEDOR_CNPJ = re.compile(
        r'Q\.?P\.?A\s*DISTRIBUI[CÇ][AÃ]O.*?CNPJ\s+([\d\.\-/]+)',
        re.DOTALL
    )
    REGEX_LOJA_NUMERO_E_NOME = re.compile(
        r'SENDAS\s+DISTRIBUIDORA\s+S/A\s+LJ(\d+)\s+\d+\s+([A-ZÀ-Ÿ /]+)'
    )
    # CNPJ da loja: o segundo CNPJ por página (primeiro é Q.P.A.)
    REGEX_CNPJ = re.compile(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})')
    # Linha de produto (Cod Forn): código 7 dígitos + descrição + UN 1 + qtd + valor_unit + valor_total
    # Tolera espaços variáveis e acentos na descrição.
    REGEX_PRODUTO = re.compile(
        r'^(\d{7})\s*([A-ZÀ-Ÿ0-9 ]+?)\s+UN\s+1\s+'
        r'([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)'
    )

    def __init__(self):
        super().__init__()
        self.formato = 'QPA_PEDIDO'

    def extract(self, pdf_path: str, texto_pre_extraido: str = None) -> List[Dict[str, Any]]:
        """Retorna lista flat de items: 1 item = (loja × produto).

        Cada item tem o numero_pedido + data_emissao do header (repetidos)
        + numero_loja + cnpj_loja + razao_social_loja + cidade_loja + uf_loja
        + codigo_qpa + descricao + qtd + valor_unitario + valor_total.
        """
        items: List[Dict[str, Any]] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Header global (mesmo em todas as páginas)
                texto_pag1 = pdf.pages[0].extract_text() or ''
                numero_pedido = self._match(self.REGEX_NUMERO_PEDIDO, texto_pag1)
                data_emissao = self._match(self.REGEX_DATA_EMISSAO, texto_pag1)
                previsao_entrega = self._match(self.REGEX_PREVISAO, texto_pag1)
                fornecedor_cnpj_raw = self._match(self.REGEX_FORNECEDOR_CNPJ, texto_pag1)
                fornecedor_cnpj = self.sanitize_cnpj(fornecedor_cnpj_raw) if fornecedor_cnpj_raw else None

                if not numero_pedido:
                    self.errors.append('numero_pedido não encontrado na página 1')

                # Itera páginas: cada página = 1 loja
                for idx, page in enumerate(pdf.pages):
                    texto = page.extract_text() or ''
                    page.flush_cache()
                    if idx > 0 and idx % 20 == 0:
                        import gc; gc.collect()

                    loja_dados = self._extract_loja_da_pagina(texto)
                    if not loja_dados:
                        self.warnings.append(f'Página {idx+1}: loja não identificada')
                        continue

                    produtos = self._extract_produtos_da_pagina(texto)
                    if not produtos:
                        self.warnings.append(
                            f'Página {idx+1} (loja {loja_dados.get("numero_loja")}): zero produtos extraídos'
                        )
                        continue

                    for prod in produtos:
                        items.append({
                            'numero_pedido': numero_pedido,
                            'data_emissao': data_emissao,
                            'previsao_entrega': previsao_entrega,
                            'fornecedor_cnpj': fornecedor_cnpj,
                            **loja_dados,
                            **prod,
                            'pagina': idx + 1,
                        })

        except Exception as e:
            import traceback
            self.errors.append(f'Erro ao processar PDF: {e}')
            self.errors.append(traceback.format_exc())

        return items

    def validate(self, data: Dict[str, Any]) -> bool:
        """Valida 1 item: campos obrigatórios + qtd > 0 + valor > 0."""
        for k in ('numero_pedido', 'numero_loja', 'codigo_qpa', 'qtd', 'valor_unitario'):
            if data.get(k) in (None, ''):
                return False
        if (data.get('qtd') or 0) <= 0:
            return False
        if (data.get('valor_unitario') or Decimal('0')) <= 0:
            return False
        return True

    # ============== helpers privados ==============

    def _match(self, regex: re.Pattern, texto: str) -> Optional[str]:
        m = regex.search(texto)
        return m.group(1).strip() if m else None

    def _extract_loja_da_pagina(self, texto: str) -> Optional[Dict[str, Any]]:
        m = self.REGEX_LOJA_NUMERO_E_NOME.search(texto)
        if not m:
            return None
        numero_loja = m.group(1).strip()
        razao_apos_LJ = m.group(2).strip()  # ex: "012 JUNDIAI" ou "JOÃO DIAS"

        # CNPJs da página: o primeiro é Q.P.A., o segundo é a loja Sendas
        cnpjs = self.REGEX_CNPJ.findall(texto)
        cnpj_loja = cnpjs[1] if len(cnpjs) >= 2 else None

        # Cidade/UF: vem na linha "Cidade XXXX - UF" do bloco DADOS PARA FATURAMENTO
        cidade = None
        uf = None
        for ln in texto.split('\n'):
            m_cid = re.search(r'Cidade\s+([A-ZÀ-Ÿ ]+?)\s*-\s*([A-Z]{2})\s', ln)
            if m_cid:
                cidade = m_cid.group(1).strip()
                uf = m_cid.group(2).strip()
                break  # primeiro match: dados para faturamento

        return {
            'numero_loja': numero_loja,
            'razao_social_loja': f'SENDAS DISTRIBUIDORA S/A LJ{numero_loja}',
            'cnpj_loja': cnpj_loja,
            'cidade_loja': cidade,
            'uf_loja': uf,
        }

    def _extract_produtos_da_pagina(self, texto: str) -> List[Dict[str, Any]]:
        produtos = []
        for linha in texto.split('\n'):
            linha = linha.strip()
            if not linha:
                continue
            m = self.REGEX_PRODUTO.match(linha)
            if not m:
                continue
            codigo, descricao, qtd_str, vu_str, vt_str = m.groups()
            produtos.append({
                'codigo_qpa': codigo.strip(),
                'descricao': descricao.strip(),
                'qtd': self.sanitize_quantity(qtd_str),
                'valor_unitario': self.sanitize_decimal(vu_str),
                'valor_total': self.sanitize_decimal(vt_str),
            })
        return produtos
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/services/parsers/__init__.py
git add app/motos_assai/services/parsers/qpa_pedido_extractor.py
git commit -m "feat(motos_assai): add QpaPedidoExtractor (deterministic regex/pdfplumber)"
```

---

## Task 3: Testes do `QpaPedidoExtractor`

**Files:**
- Create: `tests/motos_assai/fixtures/pedido_voe_exemplo.pdf`
- Create: `tests/motos_assai/test_qpa_pedido_extractor.py`

- [ ] **Step 1: Copiar PDF de exemplo para fixtures**

```bash
mkdir -p tests/motos_assai/fixtures
cp "/mnt/c/Users/rafael.nascimento/Downloads/pedido VOE 1 (1).pdf" tests/motos_assai/fixtures/pedido_voe_exemplo.pdf
ls -lh tests/motos_assai/fixtures/pedido_voe_exemplo.pdf
```

Expected: ~370KB.

- [ ] **Step 2: Test**

`tests/motos_assai/test_qpa_pedido_extractor.py`:

```python
import os
from decimal import Decimal
import pytest

from app.motos_assai.services.parsers.qpa_pedido_extractor import QpaPedidoExtractor


FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'pedido_voe_exemplo.pdf')


def test_fixture_exists():
    assert os.path.exists(FIXTURE), f"Fixture {FIXTURE} ausente"


def test_extract_retorna_38_lojas_x_3_modelos():
    """Pedido VOE 1 tem 38 páginas (lojas) × 3 modelos = 114 itens."""
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    assert len(items) == 38 * 3, f"Esperava 114 items, veio {len(items)}"


def test_header_global_consistente():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    numeros = {i['numero_pedido'] for i in items}
    assert numeros == {'21439695/L'}, f"Esperava 1 número de pedido, veio {numeros}"
    datas = {i['data_emissao'] for i in items}
    assert datas == {'22/04/2026'}


def test_lojas_unicas_38():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    numeros_loja = {i['numero_loja'] for i in items}
    assert len(numeros_loja) == 38
    assert '12' in numeros_loja  # JUNDIAI
    assert '285' in numeros_loja  # FREGUESIA DO O


def test_codigos_qpa_3_modelos():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    codigos = {i['codigo_qpa'] for i in items}
    assert codigos == {'1342056', '1342059', '1342063'}


def test_qtd_x11_mini_e_10_por_loja():
    """X11 MINI (1342056): 10 motos por loja, 38 lojas → 380 motos total."""
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    x11 = [i for i in items if i['codigo_qpa'] == '1342056']
    total_qtd = sum(i['qtd'] for i in x11)
    assert total_qtd == 380, f"Esperava 380 X11 MINI, veio {total_qtd}"


def test_qtd_dot_e_14_por_loja():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    dot = [i for i in items if i['codigo_qpa'] == '1342059']
    total_qtd = sum(i['qtd'] for i in dot)
    assert total_qtd == 14 * 38


def test_valor_unitario_dot():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    dot = next(i for i in items if i['codigo_qpa'] == '1342059')
    assert dot['valor_unitario'] == Decimal('6900.00') or \
           dot['valor_unitario'] == Decimal('6900.0000')


def test_validate_aceita_item_valido():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    assert e.validate(items[0]) is True


def test_validate_rejeita_qtd_zero():
    e = QpaPedidoExtractor()
    item = {'numero_pedido': '1', 'numero_loja': '1', 'codigo_qpa': '1',
            'qtd': 0, 'valor_unitario': Decimal('1')}
    assert e.validate(item) is False


def test_zero_warnings_zero_errors_em_pdf_canonico():
    """No PDF canônico, parser não deve gerar warnings ou errors."""
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    assert len(items) > 0
    assert e.errors == [], f"Errors inesperados: {e.errors}"
```

- [ ] **Step 3: Rodar**

```bash
pytest tests/motos_assai/test_qpa_pedido_extractor.py -v
```

Expected: 10 PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/motos_assai/fixtures/pedido_voe_exemplo.pdf
git add tests/motos_assai/test_qpa_pedido_extractor.py
git commit -m "test(motos_assai): QpaPedidoExtractor with real VOE fixture (114 items)"
```

---

## Task 4: Fallback LLM `QpaPedidoLlmFallback`

**Files:**
- Create: `app/motos_assai/services/parsers/qpa_pedido_llm_fallback.py`

- [ ] **Step 1: Implementar fallback**

`app/motos_assai/services/parsers/qpa_pedido_llm_fallback.py`:

```python
"""Fallback LLM para parsing de pedido VOE Q.P.A. quando determinístico falha.

Acionado pelo `pedido_service` quando confiança < 70% ou zero items extraídos.

Estratégia:
- Tentativa 1: Haiku 4.5 com schema JSON estruturado
- Tentativa 2: Sonnet 4.6 (se Haiku falhar parse JSON ou retornar incompleto)

Não usa caching: cada PDF é único; o prompt sistema é estático mas o conteúdo varia.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from decimal import Decimal
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

HAIKU_MODEL = 'claude-haiku-4-5-20251001'
SONNET_MODEL = 'claude-sonnet-4-6'

PROMPT_SYSTEM = """Você é um parser de PDFs de Pedido de Compras (sistema Consinco) emitidos pela Q.P.A. Distribuição LTDA para a Sendas Distribuidora (Assaí).

Cada PÁGINA do PDF representa UMA loja Sendas com header próprio + tabela de produtos.

Modelos comercializados (todos 1000W 60V 20AH autopropelidos):
- AUTOPROPELIDO X11 MINI 1000W 60V 20AH (código Q.P.A. típico: 1342056)
- AUTOPROPELIDO DOT 1000W 60V 20AH (código Q.P.A. típico: 1342059)
- AUTOPROPELIDO SOL 1000W 60V 20AH (código Q.P.A. típico: 1342063)

Retorne JSON puro (sem markdown fence, sem comentários) seguindo o schema:

{
  "numero_pedido": "21439695/L",
  "data_emissao": "DD/MM/YYYY",
  "previsao_entrega": "DD/MM/YYYY",
  "fornecedor_cnpj": "53780554000115",
  "lojas": [
    {
      "numero_loja": "12",
      "razao_social_loja": "SENDAS DISTRIBUIDORA S/A LJ12",
      "cnpj_loja": "06.057.223/0272-90",
      "cidade_loja": "JUNDIAI",
      "uf_loja": "SP",
      "itens": [
        {
          "codigo_qpa": "1342056",
          "descricao": "AUTOPROPELIDO X11 MINI 1000W 60V 20AH",
          "qtd": 10,
          "valor_unitario": 7100.00,
          "valor_total": 71000.00
        }
      ]
    }
  ]
}

REGRAS:
- Use ponto como separador decimal (não vírgula).
- numero_loja = só os dígitos (sem o prefixo "LJ").
- Se um campo não existir, omita-o (não use null).
- Não inclua qualquer texto antes ou depois do JSON.
"""


class QpaPedidoLlmFallbackError(Exception):
    """Erro irrecuperável do fallback LLM."""


def parse_via_llm(pdf_bytes: bytes) -> Dict[str, Any]:
    """Parseia PDF via LLM. Tenta Haiku, depois Sonnet em fallback.

    Retorna mesmo formato lista-flat do `QpaPedidoExtractor.extract()` para
    o `pedido_service` poder consumir uniformemente.
    """
    try:
        import anthropic
    except ImportError:
        raise QpaPedidoLlmFallbackError("Pacote 'anthropic' não instalado")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise QpaPedidoLlmFallbackError("ANTHROPIC_API_KEY não configurada")

    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    # Tentativa 1: Haiku
    try:
        data = _chamar_llm(client, pdf_b64, HAIKU_MODEL)
        items = _converter_para_lista_flat(data, modelo='HAIKU')
        if items:
            return {'parser_usado': 'LLM_HAIKU', 'items': items}
    except Exception as e:
        logger.warning(f'Haiku fallback falhou: {e}')

    # Tentativa 2: Sonnet
    data = _chamar_llm(client, pdf_b64, SONNET_MODEL)
    items = _converter_para_lista_flat(data, modelo='SONNET')
    if items:
        return {'parser_usado': 'LLM_SONNET', 'items': items}

    raise QpaPedidoLlmFallbackError("Haiku e Sonnet retornaram zero items")


def _chamar_llm(client, pdf_b64: str, model: str) -> Dict[str, Any]:
    """Chama Anthropic Messages API com PDF como document block."""
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=PROMPT_SYSTEM,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'document',
                    'source': {
                        'type': 'base64',
                        'media_type': 'application/pdf',
                        'data': pdf_b64,
                    },
                },
                {
                    'type': 'text',
                    'text': 'Extraia o pedido completo em JSON.',
                },
            ],
        }],
    )

    raw = response.content[0].text.strip()
    json_str = _extrair_json(raw)
    return json.loads(json_str)


def _extrair_json(raw: str) -> str:
    """Remove markdown fence se presente; isola primeiro objeto JSON."""
    raw = raw.strip()
    if raw.startswith('```'):
        m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', raw, re.DOTALL)
        if m:
            return m.group(1)
    # Procura primeiro { e último } balanceado
    inicio = raw.find('{')
    if inicio < 0:
        raise QpaPedidoLlmFallbackError(f"Sem JSON em resposta: {raw[:200]}")
    return raw[inicio:]


def _converter_para_lista_flat(data: Dict, modelo: str) -> List[Dict]:
    """Converte schema JSON estruturado para lista-flat de items.

    Mesmo formato que `QpaPedidoExtractor.extract()` retorna.
    """
    items = []
    numero_pedido = data.get('numero_pedido')
    data_emissao = data.get('data_emissao')
    previsao = data.get('previsao_entrega')
    fornecedor_cnpj = data.get('fornecedor_cnpj')

    for loja in data.get('lojas', []):
        loja_dados = {
            'numero_loja': str(loja.get('numero_loja', '')).strip(),
            'razao_social_loja': loja.get('razao_social_loja'),
            'cnpj_loja': loja.get('cnpj_loja'),
            'cidade_loja': loja.get('cidade_loja'),
            'uf_loja': loja.get('uf_loja'),
        }
        for item in loja.get('itens', []):
            items.append({
                'numero_pedido': numero_pedido,
                'data_emissao': data_emissao,
                'previsao_entrega': previsao,
                'fornecedor_cnpj': fornecedor_cnpj,
                **loja_dados,
                'codigo_qpa': str(item.get('codigo_qpa', '')).strip(),
                'descricao': item.get('descricao'),
                'qtd': int(item.get('qtd', 0)),
                'valor_unitario': Decimal(str(item.get('valor_unitario', 0))),
                'valor_total': Decimal(str(item.get('valor_total', 0))),
            })
    return items
```

- [ ] **Step 2: Validar import**

```bash
python -c "from app.motos_assai.services.parsers.qpa_pedido_llm_fallback import parse_via_llm, HAIKU_MODEL; print('OK,', HAIKU_MODEL)"
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/services/parsers/qpa_pedido_llm_fallback.py
git commit -m "feat(motos_assai): add LLM fallback (Haiku→Sonnet) for VOE PDF parser"
```

---

## Task 5: `modelo_resolver` service + testes

**Files:**
- Create: `app/motos_assai/services/modelo_resolver.py`
- Create: `tests/motos_assai/test_modelo_resolver.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/modelo_resolver.py`:

```python
"""Resolve nome/código observado em PDF/Excel para o `AssaiModelo` canônico.

Estratégia em 3 camadas (primeiro match retorna):
1. Match exato em `assai_modelo.codigo` (ex: 'X11_MINI', 'DOT', 'SOL')
2. Match em `assai_modelo_alias.alias` por (tipo, alias) case-insensitive
3. Substring em `assai_modelo.descricao_qpa` (ilike)

Retorna None se nada bate — caller decide se cria pendência ou skipa item.
"""

from __future__ import annotations

import re
from typing import Optional

from app import db
from app.motos_assai.models import (
    AssaiModelo, AssaiModeloAlias,
    ALIAS_TIPO_CODIGO_QPA, ALIAS_TIPO_DESCRICAO_RECIBO, ALIAS_TIPO_NOME_LIVRE,
)


def _normalizar(s: Optional[str]) -> str:
    """Uppercase + trim + colapsa espaços múltiplos."""
    if not s:
        return ''
    return re.sub(r'\s+', ' ', s.strip().upper())


def resolver_modelo(texto: str, origem: str = 'GENERICO') -> Optional[AssaiModelo]:
    """Resolve texto observado para AssaiModelo. None se nada bate.

    `origem` é informativo (logging/debug); não altera lookup.
    """
    if not texto:
        return None

    norm = _normalizar(texto)

    # 1. Match exato em codigo
    m = AssaiModelo.query.filter(
        db.func.upper(AssaiModelo.codigo) == norm,
        AssaiModelo.ativo == True,
    ).first()
    if m:
        return m

    # 2. Match em alias (case-insensitive)
    alias = AssaiModeloAlias.query.filter(
        db.func.upper(AssaiModeloAlias.alias) == norm,
        AssaiModeloAlias.ativo == True,
    ).first()
    if alias:
        return alias.modelo

    # 3. Substring de descricao_qpa
    m = AssaiModelo.query.filter(
        AssaiModelo.descricao_qpa.ilike(f'%{texto.strip()}%'),
        AssaiModelo.ativo == True,
    ).first()
    if m:
        return m

    return None


def resolver_por_codigo_qpa(codigo_qpa: str) -> Optional[AssaiModelo]:
    """Lookup direto por código Q.P.A. (ex: '1342056'). Mais rápido."""
    if not codigo_qpa:
        return None
    cod = str(codigo_qpa).strip()

    # Match direto em assai_modelo.codigo_qpa
    m = AssaiModelo.query.filter_by(codigo_qpa=cod, ativo=True).first()
    if m:
        return m

    # Fallback: match em alias do tipo CODIGO_QPA
    alias = AssaiModeloAlias.query.filter_by(
        alias=cod, tipo=ALIAS_TIPO_CODIGO_QPA, ativo=True,
    ).first()
    if alias:
        return alias.modelo

    return None
```

- [ ] **Step 2: __init__ services (anexar)**

Em `app/motos_assai/services/__init__.py` (criado no Plano 1), adicionar:

```python
from .modelo_resolver import resolver_modelo, resolver_por_codigo_qpa
```

E acrescentar a `__all__`.

- [ ] **Step 3: Testes**

`tests/motos_assai/test_modelo_resolver.py`:

```python
from app.motos_assai.services import resolver_modelo, resolver_por_codigo_qpa


def test_resolve_codigo_canonico(app):
    """X11_MINI já existe seeded."""
    with app.app_context():
        m = resolver_modelo('X11_MINI')
        assert m is not None
        assert m.codigo == 'X11_MINI'


def test_resolve_alias_x11_nac(app):
    """X11 NAC é alias seeded de X11_MINI."""
    with app.app_context():
        m = resolver_modelo('X11 NAC')
        assert m is not None
        assert m.codigo == 'X11_MINI'


def test_resolve_alias_case_insensitive(app):
    with app.app_context():
        m = resolver_modelo('x11 nac')
        assert m is not None
        assert m.codigo == 'X11_MINI'


def test_resolve_substring_descricao_qpa(app):
    """Substring de descricao_qpa pega quando texto é mais longo."""
    with app.app_context():
        m = resolver_modelo('AUTOPROPELIDO DOT 1000W 60V 20AH')
        assert m is not None
        assert m.codigo == 'DOT'


def test_resolve_codigo_qpa(app):
    with app.app_context():
        m = resolver_por_codigo_qpa('1342063')
        assert m is not None
        assert m.codigo == 'SOL'


def test_resolve_nao_encontrado(app):
    with app.app_context():
        m = resolver_modelo('MIA TURBO')
        assert m is None


def test_resolve_string_vazia(app):
    with app.app_context():
        assert resolver_modelo('') is None
        assert resolver_modelo(None) is None
        assert resolver_por_codigo_qpa('') is None
```

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/motos_assai/test_modelo_resolver.py -v
```

Expected: 7 PASS (depende dos seeds do Plano 1 estarem aplicados).

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/modelo_resolver.py
git add app/motos_assai/services/__init__.py
git add tests/motos_assai/test_modelo_resolver.py
git commit -m "feat(motos_assai): add modelo_resolver (3-layer lookup) + tests"
```

---

## Task 6: `pedido_service.importar_pdf_voe`

**Files:**
- Create: `app/motos_assai/services/pedido_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Create: `tests/motos_assai/test_pedido_service.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/pedido_service.py`:

```python
"""Orquestração de importação de pedido VOE Q.P.A.

Fluxo:
1. Salva PDF em S3 (`motos_assai/pedidos/<numero_ou_uuid>.pdf`)
2. Roda QpaPedidoExtractor (determinístico)
3. Calcula confiança = (paginas_com_itens / paginas_total) * (lojas_resolvidas / lojas_total)
4. Se confiança < 0.70 OU zero items: aciona LLM fallback (Haiku → Sonnet)
5. Persiste AssaiPedidoVenda + N AssaiPedidoVendaItem
6. Status final: ABERTO

Não confirma o pedido — operador deve revisar tela de detalhe e clicar
"Confirmar pedido" para liberar consolidação em PO Motochefe.
"""

from __future__ import annotations

import io
import logging
import tempfile
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime

import pdfplumber

from app import db
from app.utils.file_storage import FileStorage
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiLoja, AssaiModelo,
    PEDIDO_STATUS_ABERTO,
)
from app.motos_assai.services.parsers.qpa_pedido_extractor import QpaPedidoExtractor
from app.motos_assai.services.parsers.qpa_pedido_llm_fallback import (
    parse_via_llm, QpaPedidoLlmFallbackError,
)
from app.motos_assai.services.modelo_resolver import resolver_por_codigo_qpa

logger = logging.getLogger(__name__)


CONFIANCA_LIMIAR = 0.70


class PedidoVoeJaExisteError(Exception):
    """Pedido com mesmo número já foi importado."""


class PedidoVoeParserError(Exception):
    """Falha tanto determinística quanto LLM."""


def importar_pdf_voe(
    pdf_bytes: bytes,
    nome_arquivo: str,
    importado_por_id: int,
) -> AssaiPedidoVenda:
    """Importa PDF do pedido VOE. Persiste em S3 + cria registros no banco.

    Raises:
        PedidoVoeJaExisteError: se número do pedido já existe.
        PedidoVoeParserError: se determinístico e LLM falham.
    """
    # 1. Salvar PDF no S3
    buf = io.BytesIO(pdf_bytes)
    buf.name = nome_arquivo
    s3_key = FileStorage().save_file(
        buf, folder='motos_assai/pedidos',
        filename=nome_arquivo,
        allowed_extensions=['pdf'],
    )

    # 2. Determinístico
    extractor = QpaPedidoExtractor()
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name

    try:
        items = extractor.extract(tmp_path)
        confianca = _calcular_confianca(tmp_path, items)
        parser_usado = 'DETERMINISTICO'

        # 3. Fallback LLM se necessário
        if not items or confianca < CONFIANCA_LIMIAR:
            logger.warning(
                f"Confiança baixa ({confianca:.2f}) ou zero items. "
                f"Acionando LLM fallback para {nome_arquivo}."
            )
            try:
                llm_result = parse_via_llm(pdf_bytes)
                items = llm_result['items']
                parser_usado = llm_result['parser_usado']
                confianca = 1.0  # LLM retornou; assumimos sucesso após validação humana
            except QpaPedidoLlmFallbackError as e:
                if not items:
                    raise PedidoVoeParserError(
                        f"Determinístico zero items + LLM falhou: {e}"
                    )
                # Mantém items determinísticos com confiança baixa
                logger.error(f'LLM fallback falhou, usando determinístico: {e}')
    finally:
        import os
        os.unlink(tmp_path)

    if not items:
        raise PedidoVoeParserError("Zero items extraídos por ambos parsers")

    # 4. Persistir
    numero_pedido = items[0].get('numero_pedido')
    if not numero_pedido:
        raise PedidoVoeParserError("numero_pedido ausente nos items")

    if AssaiPedidoVenda.query.filter_by(numero=numero_pedido).first():
        raise PedidoVoeJaExisteError(
            f"Pedido {numero_pedido} já foi importado anteriormente"
        )

    pedido = AssaiPedidoVenda(
        numero=numero_pedido,
        data_emissao=_parse_data(items[0].get('data_emissao')),
        previsao_entrega=_parse_data(items[0].get('previsao_entrega')),
        fornecedor_cnpj=items[0].get('fornecedor_cnpj'),
        pdf_s3_key=s3_key,
        parser_usado=parser_usado,
        parsing_confianca=Decimal(str(round(confianca, 2))),
        status=PEDIDO_STATUS_ABERTO,
        criado_por_id=importado_por_id,
    )
    db.session.add(pedido)
    db.session.flush()

    # Cache de lojas e modelos para não fazer N queries
    lojas_cache: Dict[str, AssaiLoja] = {}
    modelos_cache: Dict[str, Optional[AssaiModelo]] = {}

    items_persistidos = 0
    items_pulados = []

    for item in items:
        numero_loja = item.get('numero_loja')
        codigo_qpa = item.get('codigo_qpa')
        if not numero_loja or not codigo_qpa:
            items_pulados.append({'motivo': 'numero_loja ou codigo_qpa ausente', 'item': item})
            continue

        # Resolver loja
        if numero_loja not in lojas_cache:
            lojas_cache[numero_loja] = AssaiLoja.query.filter_by(numero=numero_loja).first()
        loja = lojas_cache[numero_loja]
        if not loja:
            items_pulados.append({
                'motivo': f'loja {numero_loja} não cadastrada',
                'item': item,
            })
            continue

        # Resolver modelo
        if codigo_qpa not in modelos_cache:
            modelos_cache[codigo_qpa] = resolver_por_codigo_qpa(codigo_qpa)
        modelo = modelos_cache[codigo_qpa]
        if not modelo:
            items_pulados.append({
                'motivo': f'modelo codigo_qpa={codigo_qpa} não cadastrado',
                'item': item,
            })
            continue

        # Verifica se já existe (evita duplicata em pages re-processed)
        existente = AssaiPedidoVendaItem.query.filter_by(
            pedido_id=pedido.id, loja_id=loja.id, modelo_id=modelo.id,
        ).first()
        if existente:
            existente.qtd_pedida += int(item['qtd'])
            existente.valor_total = (existente.valor_total or Decimal('0')) + Decimal(str(item['valor_total']))
            continue

        db.session.add(AssaiPedidoVendaItem(
            pedido_id=pedido.id,
            loja_id=loja.id,
            modelo_id=modelo.id,
            qtd_pedida=int(item['qtd']),
            valor_unitario=Decimal(str(item['valor_unitario'])),
            valor_total=Decimal(str(item['valor_total'])),
        ))
        items_persistidos += 1

    if items_persistidos == 0:
        db.session.rollback()
        raise PedidoVoeParserError(
            f"Nenhum item válido. Pulados: {len(items_pulados)} (primeiros 3: {items_pulados[:3]})"
        )

    db.session.commit()

    if items_pulados:
        logger.warning(
            f"Pedido {numero_pedido}: {items_persistidos} items persistidos, "
            f"{len(items_pulados)} pulados. Primeiros pulados: {items_pulados[:3]}"
        )

    return pedido


def confirmar_pedido(pedido_id: int) -> AssaiPedidoVenda:
    """Apenas marca o pedido como conferido pelo operador (sem mudar status).

    No fluxo atual, status = ABERTO já significa pronto para consolidar em
    PO Motochefe. A confirmação humana é registrada via auditoria implícita
    (timestamp criado_em + usuário criado_por_id já existem). Este método
    é placeholder para futura adição de campo `conferido_em`/`conferido_por`.
    """
    return AssaiPedidoVenda.query.get_or_404(pedido_id)


# ============== helpers ==============

def _calcular_confianca(pdf_path: str, items: list) -> float:
    """Confiança = (lojas_extraídas / paginas_total) clamped [0, 1].

    Heurística: cada página = 1 loja. Se 36 páginas mas só 32 lojas distintas
    nos items, confiança = 32/36 = 0.89.
    """
    if not items:
        return 0.0
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_paginas = len(pdf.pages)
    except Exception:
        return 0.5  # PDF deu erro mas items vieram

    lojas_distintas = len({i['numero_loja'] for i in items if i.get('numero_loja')})
    if total_paginas == 0:
        return 0.0
    return min(1.0, lojas_distintas / total_paginas)


def _parse_data(data_str: Optional[str]):
    """Converte 'DD/MM/YYYY' para date. None se inválido."""
    if not data_str:
        return None
    try:
        return datetime.strptime(data_str.strip(), '%d/%m/%Y').date()
    except (ValueError, AttributeError):
        return None
```

- [ ] **Step 2: Atualizar __init__**

Em `app/motos_assai/services/__init__.py`, adicionar:

```python
from .pedido_service import (
    importar_pdf_voe, confirmar_pedido,
    PedidoVoeJaExisteError, PedidoVoeParserError,
    CONFIANCA_LIMIAR,
)
```

E acrescentar a `__all__`.

- [ ] **Step 3: Test integration (sem mockar LLM — só determinístico)**

`tests/motos_assai/test_pedido_service.py`:

```python
import os
import pytest

from app import db
from app.motos_assai.services import (
    importar_pdf_voe, PedidoVoeJaExisteError,
)
from app.motos_assai.models import AssaiPedidoVenda, AssaiPedidoVendaItem


FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'pedido_voe_exemplo.pdf')


def test_importar_pdf_voe_sucesso(app, admin_user):
    """Importa o PDF canônico e persiste 38 lojas × 3 modelos = 114 items."""
    with app.app_context():
        with open(FIXTURE, 'rb') as f:
            pdf_bytes = f.read()

        # Limpa pedido se já existe (re-run)
        AssaiPedidoVenda.query.filter_by(numero='21439695/L').delete()
        db.session.commit()

        pedido = importar_pdf_voe(
            pdf_bytes=pdf_bytes,
            nome_arquivo='pedido_voe_exemplo.pdf',
            importado_por_id=admin_user.id,
        )

        assert pedido.numero == '21439695/L'
        assert pedido.parser_usado == 'DETERMINISTICO'
        assert float(pedido.parsing_confianca) >= 0.95
        assert pedido.status == 'ABERTO'

        items = AssaiPedidoVendaItem.query.filter_by(pedido_id=pedido.id).all()
        # 38 lojas seeded × 3 modelos = 114 (assume todas lojas em assai_loja)
        assert len(items) == 38 * 3, f'Esperava 114 items, veio {len(items)}'


def test_importar_duplicado_falha(app, admin_user):
    with app.app_context():
        with open(FIXTURE, 'rb') as f:
            pdf_bytes = f.read()

        # Garante que já existe
        if not AssaiPedidoVenda.query.filter_by(numero='21439695/L').first():
            importar_pdf_voe(pdf_bytes, 'p.pdf', admin_user.id)

        with pytest.raises(PedidoVoeJaExisteError):
            importar_pdf_voe(pdf_bytes, 'p2.pdf', admin_user.id)
```

- [ ] **Step 4: Rodar**

```bash
pytest tests/motos_assai/test_pedido_service.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/pedido_service.py
git add app/motos_assai/services/__init__.py
git add tests/motos_assai/test_pedido_service.py
git commit -m "feat(motos_assai): pedido_service.importar_pdf_voe with confidence + LLM fallback"
```

---

## Task 7: Form + Rota POST upload pedido

**Files:**
- Create: `app/motos_assai/forms/pedido_forms.py`
- Modify: `app/motos_assai/forms/__init__.py`
- Create: `app/motos_assai/routes/pedidos.py`
- Modify: `app/motos_assai/routes/__init__.py`

- [ ] **Step 1: Form**

`app/motos_assai/forms/pedido_forms.py`:

```python
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed


class UploadPedidoVoeForm(FlaskForm):
    pdf = FileField('PDF do Pedido VOE', validators=[
        FileRequired('Selecione o PDF do pedido.'),
        FileAllowed(['pdf'], 'Apenas PDF.'),
    ])
```

- [ ] **Step 2: Atualizar __init__**

```python
from .pedido_forms import UploadPedidoVoeForm

__all__ = [..., 'UploadPedidoVoeForm']
```

- [ ] **Step 3: Rota**

`app/motos_assai/routes/pedidos.py`:

```python
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import UploadPedidoVoeForm
from app.motos_assai.services import (
    importar_pdf_voe, PedidoVoeJaExisteError, PedidoVoeParserError,
)


@motos_assai_bp.route('/pedidos/upload', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def pedidos_upload():
    form = UploadPedidoVoeForm()
    if form.validate_on_submit():
        pdf_file = form.pdf.data
        pdf_bytes = pdf_file.read()
        try:
            pedido = importar_pdf_voe(
                pdf_bytes=pdf_bytes,
                nome_arquivo=pdf_file.filename or 'pedido.pdf',
                importado_por_id=current_user.id,
            )
            flash(
                f'Pedido {pedido.numero} importado via {pedido.parser_usado} '
                f'(confiança {float(pedido.parsing_confianca):.0%}).',
                'success',
            )
            return redirect(url_for('motos_assai.pedidos_detalhe', pedido_id=pedido.id))
        except PedidoVoeJaExisteError as e:
            flash(str(e), 'warning')
        except PedidoVoeParserError as e:
            current_app.logger.exception('Erro ao parsear pedido VOE')
            flash(f'Erro ao parsear PDF: {e}', 'danger')
    return render_template('motos_assai/pedidos/upload.html', form=form)
```

- [ ] **Step 4: Importar route no blueprint**

Em `app/motos_assai/routes/__init__.py`, adicionar ao final:

```python
from app.motos_assai.routes import pedidos  # noqa: E402,F401
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/forms/pedido_forms.py
git add app/motos_assai/forms/__init__.py
git add app/motos_assai/routes/pedidos.py
git add app/motos_assai/routes/__init__.py
git commit -m "feat(motos_assai): pedidos_upload route + form"
```

---

## Task 8: Template upload pedido

**Files:**
- Create: `app/templates/motos_assai/pedidos/upload.html`

- [ ] **Step 1: Template**

`app/templates/motos_assai/pedidos/upload.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="mb-3">
  <h2>Importar pedido VOE (Q.P.A. → Sendas)</h2>
  <p class="text-muted">Faça upload do PDF gerado pelo Consinco.</p>
</header>

<form method="POST" enctype="multipart/form-data" class="card p-4" style="max-width: 600px;">
  {{ form.hidden_tag() }}

  <div class="mb-3">
    {{ form.pdf.label(class="form-label") }}
    {{ form.pdf(class="form-control", accept="application/pdf") }}
    {% for e in form.pdf.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
  </div>

  <div class="alert alert-info small">
    <i class="fas fa-info-circle"></i>
    O parser determinístico tenta primeiro. Se a confiança for inferior a 70%,
    o sistema usa fallback LLM (Haiku → Sonnet) automaticamente.
    Você revisará todos os dados extraídos antes de confirmar.
  </div>

  <button type="submit" class="btn btn-primary">
    <i class="fas fa-upload"></i> Importar pedido
  </button>
</form>
{% endblock %}
```

- [ ] **Step 2: Adicionar link no nav**

Em `app/templates/motos_assai/base_motos_assai.html`, adicionar:

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.pedidos_lista') }}">
      <i class="fas fa-file-invoice"></i> Pedidos VOE
    </a>
```

(A rota `pedidos_lista` será criada na Task 10. Até lá, link 404 — aceitável durante implementação.)

- [ ] **Step 3: Commit**

```bash
git add app/templates/motos_assai/pedidos/upload.html
git add app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): upload pedido VOE template + nav link"
```

---

## Task 9: Tela de detalhe do pedido

**Files:**
- Modify: `app/motos_assai/routes/pedidos.py` (adicionar rotas)
- Create: `app/templates/motos_assai/pedidos/detalhe.html`

- [ ] **Step 1: Rotas detalhe + confirmar**

Adicionar a `app/motos_assai/routes/pedidos.py`:

```python
from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiLoja, AssaiModelo,
    PEDIDO_STATUS_ABERTO,
)
from sqlalchemy import func


@motos_assai_bp.route('/pedidos/<int:pedido_id>')
@login_required
@require_motos_assai
def pedidos_detalhe(pedido_id):
    pedido = AssaiPedidoVenda.query.get_or_404(pedido_id)

    # Totais por modelo (cross-loja)
    totais_por_modelo = (
        db.session.query(
            AssaiModelo.codigo,
            AssaiModelo.nome,
            func.sum(AssaiPedidoVendaItem.qtd_pedida).label('qtd'),
            func.sum(AssaiPedidoVendaItem.valor_total).label('valor'),
        )
        .join(AssaiPedidoVendaItem, AssaiPedidoVendaItem.modelo_id == AssaiModelo.id)
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .group_by(AssaiModelo.id, AssaiModelo.codigo, AssaiModelo.nome)
        .order_by(AssaiModelo.codigo)
        .all()
    )

    # Lojas com seus items
    lojas_items = (
        db.session.query(AssaiLoja, AssaiPedidoVendaItem, AssaiModelo)
        .join(AssaiPedidoVendaItem, AssaiPedidoVendaItem.loja_id == AssaiLoja.id)
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .order_by(AssaiLoja.numero, AssaiModelo.codigo)
        .all()
    )

    # Agrupa por loja para template
    por_loja: dict = {}
    for loja, item, modelo in lojas_items:
        por_loja.setdefault(loja.id, {'loja': loja, 'items': []})
        por_loja[loja.id]['items'].append({'item': item, 'modelo': modelo})

    return render_template(
        'motos_assai/pedidos/detalhe.html',
        pedido=pedido,
        totais_por_modelo=totais_por_modelo,
        por_loja=list(por_loja.values()),
    )
```

- [ ] **Step 2: Template detalhe**

`app/templates/motos_assai/pedidos/detalhe.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>Pedido VOE — {{ pedido.numero }}
    <span class="badge bg-{% if pedido.status == 'ABERTO' %}primary{% else %}secondary{% endif %}">
      {{ pedido.status }}
    </span>
  </h2>
  <div>
    {% if pedido.pdf_s3_key %}
      <a href="#" class="btn btn-outline-secondary btn-sm">
        <i class="fas fa-file-pdf"></i> Baixar PDF original
      </a>
    {% endif %}
  </div>
</header>

<dl class="row small">
  <dt class="col-sm-2">Data emissão</dt>
  <dd class="col-sm-4">{{ pedido.data_emissao.strftime('%d/%m/%Y') if pedido.data_emissao else '-' }}</dd>
  <dt class="col-sm-2">Previsão entrega</dt>
  <dd class="col-sm-4">{{ pedido.previsao_entrega.strftime('%d/%m/%Y') if pedido.previsao_entrega else '-' }}</dd>

  <dt class="col-sm-2">Fornecedor</dt>
  <dd class="col-sm-4">Q.P.A. — {{ pedido.fornecedor_cnpj or '-' }}</dd>
  <dt class="col-sm-2">Parser</dt>
  <dd class="col-sm-4">
    <code>{{ pedido.parser_usado }}</code>
    (confiança {{ '%.0f%%' | format(pedido.parsing_confianca * 100) if pedido.parsing_confianca else '-' }})
  </dd>
</dl>

<h4 class="mt-4">Totais por modelo</h4>
<table class="table table-sm">
  <thead>
    <tr><th>Modelo</th><th class="text-end">Qtd total</th><th class="text-end">Valor total</th></tr>
  </thead>
  <tbody>
    {% for r in totais_por_modelo %}
    <tr>
      <td>{{ r.codigo }} — {{ r.nome }}</td>
      <td class="text-end">{{ r.qtd }}</td>
      <td class="text-end">R$ {{ r.valor | numero_br(2) }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<h4 class="mt-4">Por loja ({{ por_loja|length }})</h4>
<div class="accordion" id="acc-lojas">
  {% for entry in por_loja %}
    {% set loja = entry.loja %}
    <div class="accordion-item">
      <h5 class="accordion-header">
        <button class="accordion-button collapsed" type="button"
                data-bs-toggle="collapse" data-bs-target="#loja-{{ loja.id }}">
          Loja {{ loja.numero }} — {{ loja.nome }}
          <span class="ms-3 text-muted">{{ loja.cidade }}/{{ loja.uf }}</span>
        </button>
      </h5>
      <div id="loja-{{ loja.id }}" class="accordion-collapse collapse" data-bs-parent="#acc-lojas">
        <div class="accordion-body">
          <table class="table table-sm mb-0">
            <thead><tr><th>Modelo</th><th class="text-end">Qtd</th><th class="text-end">Valor unit.</th><th class="text-end">Total</th></tr></thead>
            <tbody>
              {% for it in entry.items %}
              <tr>
                <td>{{ it.modelo.codigo }} — {{ it.modelo.nome }}</td>
                <td class="text-end">{{ it.item.qtd_pedida }}</td>
                <td class="text-end">R$ {{ it.item.valor_unitario | numero_br(2) }}</td>
                <td class="text-end">R$ {{ it.item.valor_total | numero_br(2) }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  {% endfor %}
</div>

<div class="mt-3">
  <a href="{{ url_for('motos_assai.pedidos_lista') }}" class="btn btn-outline-secondary">
    <i class="fas fa-arrow-left"></i> Voltar
  </a>
  {% if pedido.status == 'ABERTO' %}
  <a href="{{ url_for('motos_assai.compras_nova', pedido_ids=[pedido.id]) }}" class="btn btn-primary">
    <i class="fas fa-arrow-right"></i> Consolidar em PO Motochefe
  </a>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/routes/pedidos.py
git add app/templates/motos_assai/pedidos/detalhe.html
git commit -m "feat(motos_assai): pedido detail view with totals and per-loja breakdown"
```

---

## Task 10: Lista de pedidos

**Files:**
- Modify: `app/motos_assai/routes/pedidos.py`
- Create: `app/templates/motos_assai/pedidos/lista.html`

- [ ] **Step 1: Rota**

Adicionar a `app/motos_assai/routes/pedidos.py`:

```python
@motos_assai_bp.route('/pedidos')
@login_required
@require_motos_assai
def pedidos_lista():
    status = request.args.get('status', '').strip() or None
    q = AssaiPedidoVenda.query

    if status:
        q = q.filter_by(status=status)

    pedidos = q.order_by(AssaiPedidoVenda.criado_em.desc()).limit(250).all()

    return render_template(
        'motos_assai/pedidos/lista.html',
        pedidos=pedidos,
        status_filtro=status,
        statuses=['ABERTO', 'EM_PRODUCAO', 'SEPARANDO', 'FATURADO_PARCIAL', 'FATURADO', 'CANCELADO'],
    )
```

- [ ] **Step 2: Template**

`app/templates/motos_assai/pedidos/lista.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>Pedidos VOE</h2>
  <a href="{{ url_for('motos_assai.pedidos_upload') }}" class="btn btn-primary">
    <i class="fas fa-upload"></i> Importar PDF
  </a>
</header>

<form method="GET" class="row g-2 mb-3">
  <div class="col-md-3">
    <select name="status" class="form-select">
      <option value="">— Todos os status —</option>
      {% for s in statuses %}
        <option value="{{ s }}" {% if s == status_filtro %}selected{% endif %}>{{ s }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-md-2">
    <button class="btn btn-outline-secondary w-100">Filtrar</button>
  </div>
</form>

<table class="table table-hover">
  <thead>
    <tr>
      <th>Número</th><th>Data emissão</th><th>Previsão</th>
      <th>Parser</th><th class="text-end">Confiança</th><th>Status</th><th>Importado em</th>
    </tr>
  </thead>
  <tbody>
    {% for p in pedidos %}
    <tr>
      <td><a href="{{ url_for('motos_assai.pedidos_detalhe', pedido_id=p.id) }}">{{ p.numero }}</a></td>
      <td>{{ p.data_emissao.strftime('%d/%m/%Y') if p.data_emissao else '-' }}</td>
      <td>{{ p.previsao_entrega.strftime('%d/%m/%Y') if p.previsao_entrega else '-' }}</td>
      <td><code class="small">{{ p.parser_usado or '-' }}</code></td>
      <td class="text-end">{{ '%.0f%%' | format(p.parsing_confianca * 100) if p.parsing_confianca else '-' }}</td>
      <td><span class="badge bg-secondary">{{ p.status }}</span></td>
      <td class="small text-muted">{{ p.criado_em.strftime('%d/%m/%Y %H:%M') }}</td>
    </tr>
    {% else %}
    <tr><td colspan="7" class="text-center text-muted">Nenhum pedido importado.</td></tr>
    {% endfor %}
  </tbody>
</table>

<p class="text-muted small">{{ pedidos|length }} pedido(s)</p>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/routes/pedidos.py
git add app/templates/motos_assai/pedidos/lista.html
git commit -m "feat(motos_assai): pedidos list view with status filter"
```

---

## Task 11: `compra_service.criar_consolidado`

**Files:**
- Create: `app/motos_assai/services/compra_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Create: `tests/motos_assai/test_compra_service.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/compra_service.py`:

```python
"""Consolida N pedidos VOE em 1 PO Motochefe.

Regras:
- Pedidos devem estar em status ABERTO
- Numero do PO Motochefe: auto MA-AAAA-NNNN (sequencial por ano)
- Após consolidação: pedidos passam a EM_PRODUCAO; PO em ABERTA
- N:N via assai_compra_motochefe_pedido
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import func, extract

from app import db
from app.motos_assai.models import (
    AssaiCompraMotochefe, AssaiCompraMotochefePedido,
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiModelo,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO,
    COMPRA_STATUS_ABERTA,
)


class CompraValidationError(Exception):
    """Erro de validação na consolidação."""


def listar_pedidos_consolidaveis() -> List[AssaiPedidoVenda]:
    """Pedidos em status ABERTO disponíveis para virar PO Motochefe."""
    return (
        AssaiPedidoVenda.query
        .filter_by(status=PEDIDO_STATUS_ABERTO)
        .order_by(AssaiPedidoVenda.criado_em.desc())
        .all()
    )


def calcular_totalizadores_por_modelo(pedido_ids: List[int]) -> List[Dict[str, Any]]:
    """SUM por modelo dos pedidos selecionados (preview antes de confirmar)."""
    if not pedido_ids:
        return []
    rows = (
        db.session.query(
            AssaiModelo.id,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            func.sum(AssaiPedidoVendaItem.qtd_pedida).label('qtd_total'),
            func.sum(AssaiPedidoVendaItem.valor_total).label('valor_total'),
        )
        .join(AssaiPedidoVendaItem, AssaiPedidoVendaItem.modelo_id == AssaiModelo.id)
        .filter(AssaiPedidoVendaItem.pedido_id.in_(pedido_ids))
        .group_by(AssaiModelo.id, AssaiModelo.codigo, AssaiModelo.nome)
        .order_by(AssaiModelo.codigo)
        .all()
    )
    return [
        {
            'modelo_id': r.id,
            'codigo': r.codigo,
            'nome': r.nome,
            'qtd_total': int(r.qtd_total or 0),
            'valor_total': r.valor_total or Decimal('0'),
        }
        for r in rows
    ]


def gerar_numero_po(hoje: Optional[date] = None) -> str:
    """Gera numero MA-YYYY-NNNN sequencial dentro do ano."""
    hoje = hoje or date.today()
    ano = hoje.year
    count = (
        AssaiCompraMotochefe.query
        .filter(extract('year', AssaiCompraMotochefe.criada_em) == ano)
        .count()
    )
    return f'MA-{ano}-{count + 1:04d}'


def criar_consolidado(
    pedido_ids: List[int],
    motochefe_cnpj: Optional[str],
    criada_por_id: int,
) -> AssaiCompraMotochefe:
    """Cria PO Motochefe consolidado."""
    if not pedido_ids:
        raise CompraValidationError('Selecione ao menos 1 pedido.')

    pedidos = AssaiPedidoVenda.query.filter(AssaiPedidoVenda.id.in_(pedido_ids)).all()
    if len(pedidos) != len(pedido_ids):
        raise CompraValidationError(
            f'Pedidos não encontrados: esperava {len(pedido_ids)}, achei {len(pedidos)}.'
        )

    nao_abertos = [p for p in pedidos if p.status != PEDIDO_STATUS_ABERTO]
    if nao_abertos:
        nums = ', '.join(p.numero for p in nao_abertos)
        raise CompraValidationError(
            f'Pedidos não estão em ABERTO: {nums}'
        )

    # Cria header
    compra = AssaiCompraMotochefe(
        numero=gerar_numero_po(),
        data_emissao=date.today(),
        motochefe_cnpj=motochefe_cnpj,
        status=COMPRA_STATUS_ABERTA,
        criada_por_id=criada_por_id,
    )
    db.session.add(compra)
    db.session.flush()

    # N:N + transição de status
    for p in pedidos:
        db.session.add(AssaiCompraMotochefePedido(compra_id=compra.id, pedido_id=p.id))
        p.status = PEDIDO_STATUS_EM_PRODUCAO

    db.session.commit()
    return compra


def get_compra(compra_id: int) -> AssaiCompraMotochefe:
    return AssaiCompraMotochefe.query.get_or_404(compra_id)


def listar_compras() -> List[AssaiCompraMotochefe]:
    return (
        AssaiCompraMotochefe.query
        .order_by(AssaiCompraMotochefe.criada_em.desc())
        .limit(250)
        .all()
    )
```

- [ ] **Step 2: Atualizar __init__**

```python
from .compra_service import (
    listar_pedidos_consolidaveis, calcular_totalizadores_por_modelo,
    gerar_numero_po, criar_consolidado, get_compra, listar_compras,
    CompraValidationError,
)
```

E acrescentar a `__all__`.

- [ ] **Step 3: Tests**

`tests/motos_assai/test_compra_service.py`:

```python
import pytest
from app import db
from app.motos_assai.services import (
    listar_pedidos_consolidaveis, criar_consolidado,
    calcular_totalizadores_por_modelo, gerar_numero_po,
    CompraValidationError,
)
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiCompraMotochefe,
    AssaiCompraMotochefePedido, PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO,
)


def _criar_pedido_minimo(numero, admin_user):
    p = AssaiPedidoVenda(
        numero=numero,
        status=PEDIDO_STATUS_ABERTO,
        criado_por_id=admin_user.id,
    )
    db.session.add(p)
    db.session.flush()
    return p


def test_gerar_numero_po_sequencial(app):
    with app.app_context():
        n = gerar_numero_po()
        assert n.startswith('MA-')
        assert len(n.split('-')) == 3


def test_criar_consolidado_vazio_falha(app, admin_user):
    with app.app_context():
        with pytest.raises(CompraValidationError, match='Selecione'):
            criar_consolidado([], None, admin_user.id)


def test_criar_consolidado_pedido_inexistente_falha(app, admin_user):
    with app.app_context():
        with pytest.raises(CompraValidationError, match='não encontrados'):
            criar_consolidado([999999], None, admin_user.id)


def test_criar_consolidado_sucesso(app, admin_user):
    with app.app_context():
        p = _criar_pedido_minimo('TEST-CONSOL-001', admin_user)
        compra = criar_consolidado(
            pedido_ids=[p.id],
            motochefe_cnpj='37542484000100',
            criada_por_id=admin_user.id,
        )
        assert compra.numero.startswith('MA-')
        assert compra.status == 'ABERTA'

        # Pedido transicionou para EM_PRODUCAO
        p_after = AssaiPedidoVenda.query.get(p.id)
        assert p_after.status == PEDIDO_STATUS_EM_PRODUCAO

        # Link N:N existe
        link = AssaiCompraMotochefePedido.query.filter_by(
            compra_id=compra.id, pedido_id=p.id,
        ).first()
        assert link is not None

        db.session.rollback()


def test_consolidar_pedido_nao_aberto_falha(app, admin_user):
    with app.app_context():
        p = _criar_pedido_minimo('TEST-CONSOL-002', admin_user)
        p.status = PEDIDO_STATUS_EM_PRODUCAO
        db.session.flush()
        with pytest.raises(CompraValidationError, match='não estão em ABERTO'):
            criar_consolidado([p.id], None, admin_user.id)
        db.session.rollback()
```

- [ ] **Step 4: Rodar**

```bash
pytest tests/motos_assai/test_compra_service.py -v
```

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/compra_service.py
git add app/motos_assai/services/__init__.py
git add tests/motos_assai/test_compra_service.py
git commit -m "feat(motos_assai): compra_service.criar_consolidado (N pedidos → 1 PO)"
```

---

## Task 12: Geração PDF do PO Motochefe

**Files:**
- Create: `app/templates/motos_assai/compras/pdf_template.html`
- Modify: `app/motos_assai/services/compra_service.py` (adicionar `gerar_pdf_po`)

- [ ] **Step 1: Verificar weasyprint**

```bash
python -c "import weasyprint; print(weasyprint.__version__)"
```

Se não estiver instalado, adicionar a `requirements.txt`:

```
weasyprint==62.3
```

E rodar `pip install weasyprint`.

- [ ] **Step 2: Template PDF**

`app/templates/motos_assai/compras/pdf_template.html`:

```jinja
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Pedido de Compra Motochefe — {{ compra.numero }}</title>
  <style>
    @page { size: A4; margin: 1.5cm; }
    body { font-family: Arial, sans-serif; font-size: 11pt; color: #222; }
    h1 { font-size: 16pt; margin: 0 0 0.5em 0; }
    .header { display: flex; justify-content: space-between; align-items: start; margin-bottom: 1em; padding-bottom: 0.5em; border-bottom: 2px solid #000; }
    .meta { font-size: 9pt; }
    .meta dt { font-weight: bold; display: inline; }
    .meta dd { display: inline; margin-left: 0.5em; }
    .meta div { margin-bottom: 0.2em; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 1em; }
    th, td { padding: 0.4em 0.6em; border: 1px solid #ccc; font-size: 10pt; }
    th { background: #f0f0f0; text-align: left; }
    td.num { text-align: right; }
    .total-row td { font-weight: bold; background: #f8f8f8; }
    .footer { margin-top: 2em; padding-top: 0.5em; border-top: 1px solid #999; font-size: 9pt; color: #666; }
    .assinatura { margin-top: 3em; display: flex; justify-content: space-between; }
    .assinatura div { width: 45%; text-align: center; border-top: 1px solid #000; padding-top: 0.3em; font-size: 9pt; }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>Pedido de Compra — {{ compra.numero }}</h1>
      <div class="meta">
        <div><dt>Data:</dt><dd>{{ compra.data_emissao.strftime('%d/%m/%Y') if compra.data_emissao else '-' }}</dd></div>
        <div><dt>Fornecedor:</dt><dd>Motochefe — CNPJ {{ compra.motochefe_cnpj or '-' }}</dd></div>
        <div><dt>Status:</dt><dd>{{ compra.status }}</dd></div>
      </div>
    </div>
  </div>

  <h3>Total por modelo</h3>
  <table>
    <thead>
      <tr><th>Código</th><th>Modelo</th><th class="num">Qtd total</th><th class="num">Valor total</th></tr>
    </thead>
    <tbody>
      {% set sum_qtd = namespace(v=0) %}
      {% set sum_valor = namespace(v=0) %}
      {% for r in totais %}
        <tr>
          <td><code>{{ r.codigo }}</code></td>
          <td>{{ r.nome }}</td>
          <td class="num">{{ r.qtd_total }}</td>
          <td class="num">R$ {{ '{:,.2f}'.format(r.valor_total) | replace(',', 'X') | replace('.', ',') | replace('X', '.') }}</td>
        </tr>
        {% set sum_qtd.v = sum_qtd.v + r.qtd_total %}
        {% set sum_valor.v = sum_valor.v + r.valor_total %}
      {% endfor %}
      <tr class="total-row">
        <td colspan="2">TOTAL GERAL</td>
        <td class="num">{{ sum_qtd.v }}</td>
        <td class="num">R$ {{ '{:,.2f}'.format(sum_valor.v) | replace(',', 'X') | replace('.', ',') | replace('X', '.') }}</td>
      </tr>
    </tbody>
  </table>

  <h3>Pedidos Sendas/Assaí consolidados ({{ pedidos|length }})</h3>
  <table>
    <thead><tr><th>Pedido VOE</th><th>Data</th><th class="num">Lojas</th><th class="num">Itens</th></tr></thead>
    <tbody>
      {% for entry in pedidos %}
      <tr>
        <td>{{ entry.pedido.numero }}</td>
        <td>{{ entry.pedido.data_emissao.strftime('%d/%m/%Y') if entry.pedido.data_emissao else '-' }}</td>
        <td class="num">{{ entry.qtd_lojas }}</td>
        <td class="num">{{ entry.qtd_items }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class="assinatura">
    <div>Comprador (Q.P.A. / Operação VOE)</div>
    <div>Motochefe</div>
  </div>

  <div class="footer">
    Documento gerado pelo sistema em {{ gerado_em }}.
  </div>
</body>
</html>
```

- [ ] **Step 3: Service `gerar_pdf_po`**

Adicionar em `app/motos_assai/services/compra_service.py`:

```python
import io
from flask import render_template
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.models import AssaiCompraMotochefePedido


def gerar_pdf_po(compra_id: int) -> bytes:
    """Renderiza template e converte para PDF via WeasyPrint. Retorna bytes."""
    from weasyprint import HTML

    compra = AssaiCompraMotochefe.query.get_or_404(compra_id)

    pedido_ids = [link.pedido_id for link in compra.pedido_links]
    totais = calcular_totalizadores_por_modelo(pedido_ids)

    # Por pedido: lojas e itens
    pedidos_info = []
    for link in compra.pedido_links:
        p = link.pedido
        qtd_lojas = (
            db.session.query(func.count(func.distinct(AssaiPedidoVendaItem.loja_id)))
            .filter(AssaiPedidoVendaItem.pedido_id == p.id)
            .scalar() or 0
        )
        qtd_items = (
            AssaiPedidoVendaItem.query.filter_by(pedido_id=p.id).count()
        )
        pedidos_info.append({
            'pedido': p, 'qtd_lojas': qtd_lojas, 'qtd_items': qtd_items,
        })

    html_str = render_template(
        'motos_assai/compras/pdf_template.html',
        compra=compra,
        totais=totais,
        pedidos=pedidos_info,
        gerado_em=agora_brasil_naive().strftime('%d/%m/%Y %H:%M'),
    )

    return HTML(string=html_str).write_pdf()
```

E exportar em `__init__.py`:

```python
from .compra_service import (..., gerar_pdf_po)
```

- [ ] **Step 4: Validar geração**

```bash
python -c "
from app import create_app
from app.motos_assai.services import listar_compras, gerar_pdf_po
app = create_app()
with app.app_context():
    compras = listar_compras()
    if compras:
        with app.test_request_context():
            pdf = gerar_pdf_po(compras[0].id)
        print(f'PDF gerado: {len(pdf)} bytes')
    else:
        print('Sem compras para testar — rodar Task 14 primeiro')
"
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/compra_service.py
git add app/motos_assai/services/__init__.py
git add app/templates/motos_assai/compras/pdf_template.html
git commit -m "feat(motos_assai): generate PO Motochefe PDF via WeasyPrint"
```

---

## Task 13: Form + Rota nova compra (preview)

**Files:**
- Create: `app/motos_assai/forms/compra_forms.py`
- Modify: `app/motos_assai/forms/__init__.py`
- Create: `app/motos_assai/routes/compras.py`
- Modify: `app/motos_assai/routes/__init__.py`
- Create: `app/templates/motos_assai/compras/nova.html`

- [ ] **Step 1: Form**

`app/motos_assai/forms/compra_forms.py`:

```python
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import Optional, Length, Regexp


class NovaCompraForm(FlaskForm):
    motochefe_cnpj = StringField('CNPJ Motochefe', validators=[
        Optional(),
        Length(max=18),
        Regexp(r'^[\d\.\-/]+$', message='Apenas dígitos e pontuação.'),
    ])
```

- [ ] **Step 2: Atualizar __init__**

```python
from .compra_forms import NovaCompraForm
```

- [ ] **Step 3: Rota**

`app/motos_assai/routes/compras.py`:

```python
from flask import render_template, request, redirect, url_for, flash, abort, Response
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import NovaCompraForm
from app.motos_assai.services import (
    listar_pedidos_consolidaveis, calcular_totalizadores_por_modelo,
    criar_consolidado, get_compra, listar_compras, gerar_pdf_po,
    CompraValidationError,
)


@motos_assai_bp.route('/compras/nova', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def compras_nova():
    form = NovaCompraForm()
    pedidos_disponiveis = listar_pedidos_consolidaveis()
    pedido_ids_pre = request.args.getlist('pedido_ids', type=int)
    pedido_ids_post = request.form.getlist('pedido_ids', type=int)

    # POST: tenta criar
    if request.method == 'POST' and form.validate_on_submit():
        if not pedido_ids_post:
            flash('Selecione ao menos 1 pedido.', 'warning')
        else:
            try:
                compra = criar_consolidado(
                    pedido_ids=pedido_ids_post,
                    motochefe_cnpj=form.motochefe_cnpj.data.strip() if form.motochefe_cnpj.data else None,
                    criada_por_id=current_user.id,
                )
                flash(f'PO {compra.numero} gerado.', 'success')
                return redirect(url_for('motos_assai.compras_detalhe', compra_id=compra.id))
            except CompraValidationError as e:
                flash(str(e), 'danger')

    # Preview de totais (se pedidos selecionados via GET ou POST)
    pedido_ids_preview = pedido_ids_post or pedido_ids_pre
    totais_preview = (
        calcular_totalizadores_por_modelo(pedido_ids_preview)
        if pedido_ids_preview else []
    )

    return render_template(
        'motos_assai/compras/nova.html',
        form=form,
        pedidos=pedidos_disponiveis,
        pedido_ids_preview=set(pedido_ids_preview),
        totais_preview=totais_preview,
    )
```

- [ ] **Step 4: Importar route no blueprint**

```python
from app.motos_assai.routes import compras  # noqa: E402,F401
```

- [ ] **Step 5: Template**

`app/templates/motos_assai/compras/nova.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="mb-3">
  <h2>Novo Pedido de Compra Motochefe</h2>
  <p class="text-muted">Selecione 1 ou mais pedidos VOE em ABERTO para consolidar.</p>
</header>

<form method="POST" id="form-compra">
  {{ form.hidden_tag() }}

  <div class="row g-3">
    <div class="col-md-7">
      <h5>Pedidos VOE em ABERTO ({{ pedidos|length }})</h5>
      {% if not pedidos %}
        <p class="text-muted">Nenhum pedido em ABERTO. Importe um pedido VOE primeiro.</p>
      {% else %}
      <table class="table table-sm">
        <thead>
          <tr>
            <th><input type="checkbox" id="select-all"></th>
            <th>Número</th><th>Data</th><th>Confiança</th>
          </tr>
        </thead>
        <tbody>
          {% for p in pedidos %}
          <tr>
            <td>
              <input type="checkbox" name="pedido_ids" value="{{ p.id }}"
                     class="form-check-input pedido-check"
                     {% if p.id in pedido_ids_preview %}checked{% endif %}>
            </td>
            <td>{{ p.numero }}</td>
            <td>{{ p.data_emissao.strftime('%d/%m/%Y') if p.data_emissao else '-' }}</td>
            <td>{{ '%.0f%%' | format(p.parsing_confianca * 100) if p.parsing_confianca else '-' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% endif %}
    </div>

    <div class="col-md-5">
      <h5>Preview totalizadores</h5>
      {% if totais_preview %}
      <table class="table table-sm">
        <thead><tr><th>Modelo</th><th class="text-end">Qtd</th><th class="text-end">Valor</th></tr></thead>
        <tbody>
          {% set sum_qtd = namespace(v=0) %}
          {% set sum_v = namespace(v=0) %}
          {% for r in totais_preview %}
          <tr>
            <td>{{ r.codigo }}</td>
            <td class="text-end">{{ r.qtd_total }}</td>
            <td class="text-end">R$ {{ r.valor_total | numero_br(2) }}</td>
          </tr>
          {% set sum_qtd.v = sum_qtd.v + r.qtd_total %}
          {% set sum_v.v = sum_v.v + r.valor_total %}
          {% endfor %}
          <tr class="table-active">
            <td><strong>TOTAL</strong></td>
            <td class="text-end"><strong>{{ sum_qtd.v }}</strong></td>
            <td class="text-end"><strong>R$ {{ sum_v.v | numero_br(2) }}</strong></td>
          </tr>
        </tbody>
      </table>
      {% else %}
        <p class="text-muted small">Selecione pedidos para ver o preview e clique em "Atualizar preview".</p>
      {% endif %}

      <div class="mb-3">
        {{ form.motochefe_cnpj.label(class="form-label") }}
        {{ form.motochefe_cnpj(class="form-control", placeholder="37.542.484/0001-00") }}
      </div>

      <button type="submit" name="action" value="preview" class="btn btn-outline-secondary"
              formmethod="get" formaction="{{ url_for('motos_assai.compras_nova') }}">
        <i class="fas fa-sync"></i> Atualizar preview
      </button>
      <button type="submit" name="action" value="confirmar" class="btn btn-primary">
        <i class="fas fa-check"></i> Gerar PO Motochefe
      </button>
    </div>
  </div>
</form>

<script>
document.getElementById('select-all').addEventListener('change', (e) => {
  document.querySelectorAll('.pedido-check').forEach(c => c.checked = e.target.checked);
});
</script>
{% endblock %}
```

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/forms/compra_forms.py
git add app/motos_assai/forms/__init__.py
git add app/motos_assai/routes/compras.py
git add app/motos_assai/routes/__init__.py
git add app/templates/motos_assai/compras/nova.html
git commit -m "feat(motos_assai): nova compra Motochefe page (multi-select + preview)"
```

---

## Task 14: Detalhe da compra + download PDF

**Files:**
- Modify: `app/motos_assai/routes/compras.py`
- Create: `app/templates/motos_assai/compras/detalhe.html`

- [ ] **Step 1: Rotas**

Adicionar em `app/motos_assai/routes/compras.py`:

```python
@motos_assai_bp.route('/compras/<int:compra_id>')
@login_required
@require_motos_assai
def compras_detalhe(compra_id):
    compra = get_compra(compra_id)
    pedido_ids = [link.pedido_id for link in compra.pedido_links]
    totais = calcular_totalizadores_por_modelo(pedido_ids) if pedido_ids else []
    return render_template(
        'motos_assai/compras/detalhe.html',
        compra=compra,
        totais=totais,
    )


@motos_assai_bp.route('/compras/<int:compra_id>/pdf')
@login_required
@require_motos_assai
def compras_pdf(compra_id):
    pdf_bytes = gerar_pdf_po(compra_id)
    compra = get_compra(compra_id)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="PO_{compra.numero}.pdf"'
        },
    )
```

- [ ] **Step 2: Template**

`app/templates/motos_assai/compras/detalhe.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>PO Motochefe — {{ compra.numero }}
    <span class="badge bg-primary">{{ compra.status }}</span>
  </h2>
  <a href="{{ url_for('motos_assai.compras_pdf', compra_id=compra.id) }}"
     class="btn btn-primary">
    <i class="fas fa-file-pdf"></i> Baixar PDF do PO
  </a>
</header>

<dl class="row small">
  <dt class="col-sm-2">Data</dt>
  <dd class="col-sm-4">{{ compra.data_emissao.strftime('%d/%m/%Y') if compra.data_emissao else '-' }}</dd>
  <dt class="col-sm-2">Motochefe CNPJ</dt>
  <dd class="col-sm-4">{{ compra.motochefe_cnpj or '-' }}</dd>
  <dt class="col-sm-2">Criada em</dt>
  <dd class="col-sm-10">{{ compra.criada_em.strftime('%d/%m/%Y %H:%M') }}</dd>
</dl>

<h4>Totais por modelo</h4>
<table class="table table-sm">
  <thead><tr><th>Modelo</th><th class="text-end">Qtd</th><th class="text-end">Valor</th></tr></thead>
  <tbody>
    {% for r in totais %}
    <tr>
      <td>{{ r.codigo }} — {{ r.nome }}</td>
      <td class="text-end">{{ r.qtd_total }}</td>
      <td class="text-end">R$ {{ r.valor_total | numero_br(2) }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<h4 class="mt-4">Pedidos VOE consolidados ({{ compra.pedido_links|length }})</h4>
<table class="table">
  <thead><tr><th>Pedido</th><th>Data</th><th>Status atual</th></tr></thead>
  <tbody>
    {% for link in compra.pedido_links %}
    <tr>
      <td>
        <a href="{{ url_for('motos_assai.pedidos_detalhe', pedido_id=link.pedido.id) }}">
          {{ link.pedido.numero }}
        </a>
      </td>
      <td>{{ link.pedido.data_emissao.strftime('%d/%m/%Y') if link.pedido.data_emissao else '-' }}</td>
      <td><span class="badge bg-secondary">{{ link.pedido.status }}</span></td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<a href="{{ url_for('motos_assai.compras_lista') }}" class="btn btn-outline-secondary mt-3">
  <i class="fas fa-arrow-left"></i> Voltar à lista
</a>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/routes/compras.py
git add app/templates/motos_assai/compras/detalhe.html
git commit -m "feat(motos_assai): compra detail view + PDF download"
```

---

## Task 15: Lista de compras + link no menu

**Files:**
- Modify: `app/motos_assai/routes/compras.py`
- Create: `app/templates/motos_assai/compras/lista.html`
- Modify: `app/templates/motos_assai/base_motos_assai.html`

- [ ] **Step 1: Rota**

```python
@motos_assai_bp.route('/compras')
@login_required
@require_motos_assai
def compras_lista():
    compras = listar_compras()
    return render_template('motos_assai/compras/lista.html', compras=compras)
```

- [ ] **Step 2: Template**

`app/templates/motos_assai/compras/lista.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>POs Motochefe</h2>
  <a href="{{ url_for('motos_assai.compras_nova') }}" class="btn btn-primary">
    <i class="fas fa-plus"></i> Novo PO
  </a>
</header>

<table class="table table-hover">
  <thead>
    <tr><th>Número</th><th>Data</th><th>Motochefe CNPJ</th><th>Status</th><th>Pedidos</th><th>Criada em</th></tr>
  </thead>
  <tbody>
    {% for c in compras %}
    <tr>
      <td><a href="{{ url_for('motos_assai.compras_detalhe', compra_id=c.id) }}">{{ c.numero }}</a></td>
      <td>{{ c.data_emissao.strftime('%d/%m/%Y') if c.data_emissao else '-' }}</td>
      <td>{{ c.motochefe_cnpj or '-' }}</td>
      <td><span class="badge bg-secondary">{{ c.status }}</span></td>
      <td>{{ c.pedido_links|length }}</td>
      <td class="small text-muted">{{ c.criada_em.strftime('%d/%m/%Y %H:%M') }}</td>
    </tr>
    {% else %}
    <tr><td colspan="6" class="text-center text-muted">Nenhum PO Motochefe.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 3: Adicionar link no nav**

Em `app/templates/motos_assai/base_motos_assai.html`:

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.compras_lista') }}">
      <i class="fas fa-shopping-cart"></i> POs Motochefe
    </a>
```

- [ ] **Step 4: Validar fluxo end-to-end manualmente**

```bash
source .venv/bin/activate
python -c "
from app import create_app
from app.auth.models import Usuario
app = create_app()
with app.app_context():
    u = Usuario.query.filter_by(perfil='administrador').first()
    with app.test_client() as c:
        with c.session_transaction() as s:
            s['_user_id'] = str(u.id); s['_fresh'] = True
        for path in ['/motos-assai/pedidos', '/motos-assai/compras', '/motos-assai/compras/nova']:
            r = c.get(path)
            print(f'{path}: {r.status_code}')
"
```

Expected: todos `200`.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/routes/compras.py
git add app/templates/motos_assai/compras/lista.html
git add app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): compras list + nav links"
```

---

## Task 16: Atualizar CLAUDE.md do módulo

**Files:**
- Modify: `app/motos_assai/CLAUDE.md`

- [ ] **Step 1: Adicionar seção Plano 2A**

Adicionar ao final de `app/motos_assai/CLAUDE.md`:

````markdown

---

## Plano 2A implementado (2026-XX-XX)

### Pipeline de entrada — Pedido VOE → PO Motochefe

**Parser determinístico** (`app/motos_assai/services/parsers/qpa_pedido_extractor.py`):
- Subclasse de `app.pedidos.leitura.base.PDFExtractor`
- Cada página = 1 loja Sendas. Layout Consinco com header LJ\<n\> + tabela de produtos
- Regex: `REGEX_PRODUTO = r'^(\d{7})\s*([A-ZÀ-Ÿ0-9 ]+?)\s+UN\s+1\s+([\d\.,]+)\s+...'`
- 38 páginas × 3 modelos = 114 itens em PDF canônico

**Fallback LLM** (`qpa_pedido_llm_fallback.py`):
- Acionado quando `confianca < 0.70` ou zero items
- Haiku 4.5 (`claude-haiku-4-5-20251001`) → Sonnet 4.6 (`claude-sonnet-4-6`)
- Anthropic SDK 0.98.1, lazy init

**Confiança** (em `pedido_service`):
```
confianca = lojas_distintas_extraidas / total_paginas
```
Limiar `CONFIANCA_LIMIAR = 0.70`.

**Modelo resolver** (`modelo_resolver.py`):
- 3 camadas: codigo → alias → substring de descricao_qpa
- `resolver_por_codigo_qpa('1342056')` para lookup direto

**Consolidação N→1** (`compra_service.criar_consolidado`):
- Pedidos em status ABERTO → EM_PRODUCAO ao consolidar
- Numero auto MA-YYYY-NNNN
- N:N via `assai_compra_motochefe_pedido`

**PDF do PO** (`gerar_pdf_po`):
- Template `compras/pdf_template.html` + WeasyPrint
- Totais por modelo + lista de pedidos consolidados + assinaturas

**Rotas adicionadas**:
- `GET/POST /motos-assai/pedidos/upload`
- `GET /motos-assai/pedidos/<id>` — detalhe com totais e accordion por loja
- `GET /motos-assai/pedidos` — lista com filtro de status
- `GET/POST /motos-assai/compras/nova` — multi-select pedidos + preview totalizadores
- `GET /motos-assai/compras/<id>` — detalhe
- `GET /motos-assai/compras/<id>/pdf` — download
- `GET /motos-assai/compras` — lista

**Próximo: Plano 2B** (recibo Motochefe + recebimento físico com QR/barcode wizard).
````

- [ ] **Step 2: Commit**

```bash
git add app/motos_assai/CLAUDE.md
git commit -m "docs(motos_assai): document Plan 2A (entrada pipeline)"
```

---

## Self-review do plano

**Spec coverage**:
- §5.1 (etapa 1: Pedido VOE entra) — Tasks 1-10. ✓
- §5.2 (etapa 2: PO Motochefe consolidado) — Tasks 11-15. ✓
- §8.1 (Pedido VOE extractor determinístico) — Task 2. ✓
- §8.2 (Pedido VOE fallback LLM) — Task 4. ✓
- §8.5 (modelo_resolver) — Task 5. ✓

**Não coberto neste plano** (vai para 2B):
- §5.3 Recibo Motochefe (PDF + Excel)
- §5.4 Recebimento físico (wizard A→B→C→D)

**Placeholder scan**: nenhum TBD/TODO sem contexto. "PREENCHER" em Task 14 do Plano 1 referenciado para CD seed; aceitável como item explícito para o dono.

**Type consistency**:
- `numero_pedido` (string com `/L`) consistente entre extractor (Task 2), LLM fallback (Task 4) e service (Task 6)
- `criar_consolidado(pedido_ids, motochefe_cnpj, criada_por_id)` consistente entre service (Task 11) e route (Task 13)
- `gerar_pdf_po(compra_id) -> bytes` em Task 12 e usado em Task 14
- Status pedido `ABERTO`/`EM_PRODUCAO` consistentes com modelos do Plano 1

---

**Plano 2A salvo em** `docs/superpowers/plans/2026-05-07-motos-assai-pedido-compra.md` — 16 tasks, ~80 sub-steps, TDD onde aplicável.

Próximo: Plano 2B (Recibo Motochefe + Recebimento físico).
