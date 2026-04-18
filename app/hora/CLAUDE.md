# Módulo HORA — Lojas Motochefe

**Data**: 2026-04-18
**Status**: skeleton — modelos e migrations não implementados ainda.
**Propósito**: controle de estoque unitário de motos elétricas nas lojas físicas da HORA (PJ distinta da Motochefe-distribuidora e CarVia).

---

## Fronteira do módulo (o que NÃO fazer)

O módulo HORA **não compartilha dados** com os módulos abaixo. Joins, FKs cross-módulo e imports de modelos de outros módulos para código HORA são proibidos.

| Módulo vizinho | Motivo da fronteira | O que NÃO misturar |
|---|---|---|
| `app/motochefe/` (distribuidora) | PJ diferente (Motochefe ≠ HORA). Motochefe é B2B atacadista; HORA é B2C varejo. | Não importar `Moto`, `PedidoVendaMoto`, `ClienteMoto`. Não reusar status enum. |
| `app/carvia/` (transportadora) | PJ diferente. CarVia só transporta; não tem estoque. | Não importar `FaturaCarVia`, modelos de CTe. |
| `app/cadastros_*`, `app/faturamento`, etc. | Clientes e produtos da Nacom Goya são indústria alimentícia; nada a ver com motos varejo. | Zero relação. |

**Reuso permitido (via adapter, não import direto)**:
- `app/carvia/services/parsers/danfe_pdf_parser.py` — extrai chassi/modelo/cor de DANFE via LLM. **Usar via `app/hora/services/parsers/danfe_adapter.py`** que encapsula a chamada e traduz para entidades HORA.
- `app/carvia/services/pricing/moto_recognition_service.py` — regex de padronização de nomes de modelo. Mesmo padrão de adapter.

---

## Convenções obrigatórias

### 1. Prefixo de tabela `hora_`

Todas as tabelas do módulo vivem no schema `public` e começam com `hora_`. Exemplos: `hora_loja`, `hora_moto`, `hora_pedido`, `hora_pedido_item`, `hora_nf_entrada`, `hora_nf_entrada_item`, `hora_recebimento`, `hora_recebimento_conferencia`, `hora_venda`, `hora_venda_item`, `hora_moto_evento`, `hora_modelo`, `hora_tabela_preco`.

**Não usar** schema PostgreSQL separado nem bind SQLAlchemy dedicado. Decisão tomada em 2026-04-18 pelo usuário: isolamento via prefixo + code review + este CLAUDE.md é suficiente.

### 2. Blueprint Flask isolado

Rotas em `app/hora/routes/`, services em `app/hora/services/`, models em `app/hora/models/`. Blueprint registrado em `app/__init__.py` com `url_prefix='/hora'`. Templates em `app/templates/hora/`.

### 3. Menu

Toda tela do módulo DEVE ter link em `app/templates/base.html` (submenu dedicado "Lojas HORA") ou em tela-mãe do próprio módulo. Regra global: nunca criar tela sem acesso via UI.

---

## Invariante central (resumo)

**`hora_moto.chassi` é a chave universal do módulo.** Detalhes completos: `docs/hora/INVARIANTES.md`.

Em 1 linha por invariante:
1. Chassi é a chave de rastreamento universal.
2. Toda tabela transacional tem `chassi` FK indexada.
3. `hora_moto` é insert-once com atributos imutáveis (chassi, modelo_id, cor, motor, ano).
4. Estado atual = consulta à tabela de eventos, não UPDATE na linha da moto.

**Consequências práticas**:
- Nunca escreva `UPDATE hora_moto SET status = ...`. Em vez disso, `INSERT INTO hora_moto_evento (chassi, tipo, ...)`.
- Ao criar uma nova tabela transacional, pergunte: "tem `chassi`?" Se não, revise o desenho.
- Ao adicionar coluna em `hora_moto`, pergunte: "esse dado pode mudar durante a vida da moto?" Se sim, o lugar certo é satélite.

---

## Modelo de dados planejado (13 tabelas)

Documentação detalhada no plano `/home/rafaelnascimento/.claude/plans/toasty-snuggling-sunrise.md`. Resumo:

**Cadastros**:
- `hora_loja` — lojas físicas (identidade, CNPJ, nome).
- `hora_modelo` — catálogo de modelos (modelo + variantes).
- `hora_tabela_preco` — preço de tabela por modelo com vigência.

**Identidade**:
- `hora_moto` — uma linha por moto física, insert-once.

**Fluxo de entrada** (Motochefe → HORA):
- `hora_pedido` + `hora_pedido_item` — pedido da HORA à Motochefe.
- `hora_nf_entrada` + `hora_nf_entrada_item` — NF recebida da Motochefe.
- `hora_recebimento` + `hora_recebimento_conferencia` — ato de receber na loja + QR code + foto + divergências.

**Fluxo de saída** (HORA → consumidor):
- `hora_venda` + `hora_venda_item` — venda ao consumidor final, multi-item possível, com `preco_tabela_ref` + `desconto_aplicado` + `preco_final` auditáveis.

**Histórico**:
- `hora_moto_evento` — log de todas as transições de estado por chassi.

---

## Parsers reusados (via adapter)

**Não duplicar**, **não mover**, **não reimplementar**. Os parsers de DANFE da CarVia já lidam com:
- Laiouns (DANFEs compactas sem CFOP, código com dash) — `danfe_pdf_parser.py:623,1076`.
- Q.P.A (repeat detection de código) — `danfe_pdf_parser.py:1191,1221`.
- B2B (comportamento default).
- Extração de chassi/motor/cor/modelo via LLM (Haiku primário, Sonnet fallback) — `danfe_pdf_parser.py:1418`.
- Regex de modelos eletric motos — `moto_recognition_service.py:48`.

**Padrão de uso no HORA**:
```python
# app/hora/services/parsers/danfe_adapter.py
from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser
from app.hora.models import HoraMoto, HoraNfEntrada

def processar_danfe_motochefe(pdf_bytes, loja_id, ...):
    parser = DanfePDFParser()
    resultado = parser.parse(pdf_bytes)
    # traduzir resultado para entidades hora_*
    ...
```

Se um comportamento específico da HORA for necessário (ex.: validação adicional de chassi), coloque na camada adapter, **nunca edite o parser CarVia**.

---

## O que NÃO fazer (lista explícita)

1. **Não copiar** o padrão `PedidoVendaMoto + PedidoVendaMotoItem` do Motochefe-distribuidora como template. Aquele desenho é B2B com fungibilidade por modelo; HORA é B2C com chassi declarado. Ver `docs/hora/INVARIANTES.md` seção "Anti-padrões rejeitados".
2. **Não adicionar status/loja/preço em `hora_moto`**. Viola invariante 3.
3. **Não fazer UPDATE em `hora_moto`** após insert. Viola invariante 4.
4. **Não criar FK cross-módulo** para tabelas de `app/motochefe/`, `app/carvia/`, ou qualquer outra tabela não-`hora_`.
5. **Não duplicar** os parsers de DANFE/regex de modelo. Reusar via adapter.
6. **Não criar schema PostgreSQL separado** nem bind dedicado. Decisão tomada em 2026-04-18.
7. **Não modelar Venda como atômica** (1 moto por venda hardcoded). Sempre header + item, mesmo quando quase todas as vendas são 1-moto.

---

## Ordem de implementação planejada

Segue o plano aprovado em 2026-04-18:

1. **P1** (esta fase): documentos contratuais — `docs/hora/INVARIANTES.md` e este `app/hora/CLAUDE.md`. **Concluído**.
2. **P2**: migrations + modelos SQLAlchemy das 13 tabelas. Dois artefatos por migration (`scripts/migrations/*.py` + `*.sql` — regra universal do sistema).
3. **P3**: fluxo pedido → NF → recebimento → conferência (ingestão e confronto).
4. **P4**: fluxo venda com tabela de preço + desconto auditável.
5. **Fase 2 futura**: financeiro (títulos a pagar/receber, conciliação, comissões). Todas as tabelas novas com `chassi` FK conforme invariante 2.

---

## Referências

- **Contrato de design**: `docs/hora/INVARIANTES.md`
- **Análise de primeiros princípios**: `/home/rafaelnascimento/.claude/plans/toasty-snuggling-sunrise.md`
- **Contexto original do processo atual (Excel/WhatsApp)**: `.claude/plans/CONTROLE_MOTOS.md`
- **Precedente de chassi como PK** (ver, não copiar): `app/motochefe/models/produto.py:45`
- **Parsers reusáveis**: `app/carvia/services/parsers/danfe_pdf_parser.py`, `app/carvia/services/pricing/moto_recognition_service.py`
- **Regra de migrations duais**: `/home/rafaelnascimento/.claude/CLAUDE.md` seção "MIGRATIONS"
- **JSON sanitization** (se usarmos JSONB para foto/metadados): `/home/rafaelnascimento/.claude/CLAUDE.md` seção "JSON SANITIZATION"
