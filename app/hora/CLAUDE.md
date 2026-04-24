# Módulo HORA — Lojas Motochefe

**Data**: 2026-04-22 (atualizado)
**Status**: em produção — modelos, migrations e fluxos pedido→NF→recebimento implementados; permissões granulares ativas.
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

**Autorização (adicionada 2026-04-22)**:
- `hora_user_permissao` — permissões granulares por (`user_id`, `modulo`) com flags `pode_ver/criar/editar/apagar/aprovar`. Sem FK para `usuarios` (mantém `app/hora` independente de `app/auth`). Migration: `scripts/migrations/hora_13_user_permissao.{py,sql}`.

---

## Autorização granular (decorator + service)

> Substitui o antigo `require_lojas` (mantido apenas para retrocompat). Use sempre `require_hora_perm` em rotas novas.

**10 módulos canônicos** (em `app/hora/models/permissao.py:MODULOS_HORA`):
`usuarios, dashboard, lojas, modelos, pedidos, nfs, recebimentos, estoque, devolucoes, pecas`.

**5 ações** (`ACOES_HORA`): `ver, criar, editar, apagar, aprovar`.
A ação `aprovar` é semântica e só tem decorator real no módulo `usuarios` (aprovação de cadastros pendentes). Para os demais, a flag é armazenada mas ignorada — o template marca a célula com `—`.

**Como usar em rotas novas**:
```python
from app.hora.decorators import require_hora_perm

@hora_bp.route('/pedidos')
@require_hora_perm('pedidos', 'ver')   # admin sempre passa; usuario inativo bloqueado; resto via tabela
def pedidos_lista(): ...
```

**Como usar em templates**:
```jinja
{% if current_user.tem_perm_hora('lojas', 'criar') %}
  <a href="{{ url_for('hora.lojas_novo') }}">Nova loja</a>
{% endif %}
```
`Usuario.tem_perm_hora` (em `app/auth/models.py`) tem cache `_hora_perm_cache` por instância — uma única query por request resolve N chamadas no menu.

**Service** (`app/hora/services/permissao_service.py`):
- `tem_perm(user, modulo, acao)` — fonte de verdade (admin sempre True; status≠ativo False; sem entry False).
- `get_matriz(user_id)` — dict `{modulo: {acao: bool}}` com 10 módulos × 5 ações.
- `get_matrizes_batch(user_ids)` — versão N-usuarios em 1 query (usado na tela de gestão).
- `salvar_matriz_completa(user_id, matriz, atualizado_por_id)` — upsert em batch + commit.

**Tela de gestão**: `/hora/permissoes` (rota `hora.permissoes_lista`). Decorator `usuarios/ver` para abrir; `usuarios/editar` para toggle/loja/granular; `usuarios/aprovar` para o card de pendentes (aprovar/rejeitar com escolha de loja). Self-edit e edição de admin por não-admin são bloqueados.

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

1. **P1**: documentos contratuais — `docs/hora/INVARIANTES.md` e este `app/hora/CLAUDE.md`. **Concluído**.
2. **P2**: migrations + modelos SQLAlchemy das 13 tabelas. **Concluído** (+ tabela 14 `hora_user_permissao` em 2026-04-22).
3. **P3**: fluxo pedido → NF → recebimento → conferência (ingestão e confronto). **Concluído**.
4. **P4**: fluxo venda com tabela de preço + desconto auditável. **Parcial — fluxo (a) concluído 2026-04-24**.
   - **Fluxo (a) — import NF saída (DANFE PDF)**: operador sobe PDF emitido pelo ERP externo em `/hora/vendas/upload`; service `venda_service.importar_nf_saida_pdf` parseia via `danfe_adapter` (reuso CarVia + extensão CPF/nome destinatário), cria `HoraVenda` + `HoraVendaItem` + emite evento `VENDIDA` nos chassis, persiste PDF em `hora/vendas/` S3, preenche `cnpj_emitente`, `parser_usado`, `parseada_em`.
   - **Fluxo permissivo**: problemas geram `HoraVendaDivergencia` (5 tipos: `CHASSI_NAO_CADASTRADO`, `CHASSI_INDISPONIVEL`, `LOJA_DIVERGENTE`, `CNPJ_DESCONHECIDO`, `TABELA_PRECO_AUSENTE`) sem bloquear o import.
   - **Campos pós-import editáveis** na tela de detalhe: `vendedor` (NULL inicialmente, preenchido manualmente), `forma_pagamento` (default `'NAO_INFORMADO'`, operador troca para PIX/CARTAO_CREDITO/DINHEIRO/MISTO), telefone, email, observações.
   - **Cancelamento**: `cancelar_venda` muda status=CANCELADA e emite evento `DEVOLVIDA` nos chassis (simetria com devolução).
   - **Wiring no estoque**: `listar_estoque` enriquece com `venda_id`, `nf_saida_numero`, `venda_status`; template mostra link clicável para a venda na coluna NF (ambas entrada e saída) e em `estoque_chassi_detalhe.html` seção Venda.
   - **Migration**: `scripts/migrations/hora_17_nf_saida.{py,sql}` — ALTER `hora_venda` (4 colunas novas + loja_id nullable + forma_pagamento default) + CREATE `hora_venda_divergencia`.
   - **Permissão**: módulo `vendas` adicionado a `MODULOS_HORA` (`app/hora/models/permissao.py:35`).
   - **Fluxo (c) — TagPlus**: ainda pendente (será em sessão futura quando houver integração de faturamento pelo sistema).
5. **P5** (2026-04-22): autorização granular por usuário × módulo × ação. **Concluído** — todas as 64 rotas usam `require_hora_perm`.
6. **P6** (2026-04-22): **Transferência entre filiais + Registro de avaria em estoque**. **Concluído**.
   - 5 tabelas novas: `hora_transferencia`, `hora_transferencia_item`, `hora_transferencia_auditoria`, `hora_avaria`, `hora_avaria_foto` (migration `hora_15`).
   - 2 tipos de evento novos em `hora_moto_evento.tipo`: `EM_TRANSITO`, `CANCELADA`.
   - Fluxo transferência: Loja A emite → `EM_TRANSITO` (loja_id=destino). Loja B confirma → `TRANSFERIDA`. A pode cancelar enquanto em trânsito → `CANCELADA` (loja_id=origem). Itens já confirmados no destino permanecem.
   - Avaria: **não bloqueia venda**. Registra + emite evento `AVARIADA`. Foto obrigatória + descrição ≥ 3 chars + múltiplas avarias por chassi permitidas. Listagem de estoque mostra badge "⚠ N" quando há avarias abertas.
   - `EVENTOS_EM_ESTOQUE` agora inclui `CANCELADA`. `EM_TRANSITO` fica em limbo (helper `listar_em_transito` em `estoque_service`).
   - Services: `transferencia_service`, `transferencia_audit`, `avaria_service` + helper `loja_origem_permitida_para_transferencia` em `auth_helper`.
   - 36 testes em `tests/hora/` cobrindo regras de negócio.
   - Spec: `docs/superpowers/specs/2026-04-22-hora-transferencia-e-avaria-design.md`.
   - Plano: `docs/superpowers/plans/2026-04-22-hora-transferencia-e-avaria.md`.
7. **Fase 2 futura**: financeiro (títulos a pagar/receber, conciliação, comissões). Todas as tabelas novas com `chassi` FK conforme invariante 2.

---

## Referências

- **Contrato de design**: `docs/hora/INVARIANTES.md`
- **Análise de primeiros princípios**: `/home/rafaelnascimento/.claude/plans/toasty-snuggling-sunrise.md`
- **Contexto original do processo atual (Excel/WhatsApp)**: `.claude/plans/CONTROLE_MOTOS.md`
- **Precedente de chassi como PK** (ver, não copiar): `app/motochefe/models/produto.py:45`
- **Parsers reusáveis**: `app/carvia/services/parsers/danfe_pdf_parser.py`, `app/carvia/services/pricing/moto_recognition_service.py`
- **Regra de migrations duais**: `/home/rafaelnascimento/.claude/CLAUDE.md` seção "MIGRATIONS"
- **JSON sanitization** (se usarmos JSONB para foto/metadados): `/home/rafaelnascimento/.claude/CLAUDE.md` seção "JSON SANITIZATION"
