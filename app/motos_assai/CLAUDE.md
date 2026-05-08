# Módulo Motos Assaí

**Data**: 2026-05-07
**Status**: Foundation + Cadastros (Plano 1) implementado.
**Propósito**: gerenciar a operação B2B Q.P.A. → Sendas/Assaí com motos elétricas, isolada de outros módulos.

---

## Fronteira do módulo (o que NÃO fazer)

| Módulo vizinho | Motivo da fronteira |
|---|---|
| `app/hora/` | PJ diferente; HORA é B2C varejo, Motos Assaí é B2B atacadista |
| `app/carvia/` | CarVia só transporta. Reuso permitido APENAS via adapter |
| `app/motochefe/` | PJ diferente |
| `app/pedidos/leitura/` | Reuso permitido via subclasse de `PDFExtractor` |

---

## Convenções obrigatórias

### 1. Prefixo de tabela `assai_`

Todas as tabelas começam com `assai_`. 16 tabelas no schema atual.

### 2. Blueprint isolado

Rotas em `app/motos_assai/routes/`, services em `app/motos_assai/services/`,
models em `app/motos_assai/models/`. Blueprint `motos_assai_bp` registrado em
`app/__init__.py` com `url_prefix='/motos-assai'`.

### 3. Toggle master `sistema_motos_assai`

Coluna em `usuarios`. Método `Usuario.pode_acessar_motos_assai()`:
admin sempre passa; status != 'ativo' bloqueia mesmo com flag.

Decorator `@require_motos_assai` em TODAS as rotas (sem exceção).

### 4. Menu

Link em `app/templates/base.html` condicionado a
`current_user.pode_acessar_motos_assai()`.

---

## Invariante central

**`assai_moto.chassi` é a chave universal do módulo.**

1. Toda tabela transacional tem `chassi` indexada.
2. `assai_moto` é insert-once com atributos imutáveis (UPDATE apenas em `cor`/`modelo_id`
   quando recebimento físico diverge do recibo Motochefe — SOT, padrão Hora).
3. Estado atual de uma moto = consulta à tabela de eventos
   (`assai_moto_evento` ordenado por `ocorrido_em DESC`), nunca UPDATE em coluna `status`.
4. `assai_moto_evento` é append-only — nunca DELETE; reversão cria nova linha
   (`REVERTIDA_PARA_MONTADA`).

---

## Eventos por chassi (`assai_moto_evento.tipo`)

| Tipo | Significado | Conta como em estoque? |
|------|-------------|------------------------|
| `ESTOQUE` | Recebida no CD | Sim |
| `MONTADA` | Montada e OK | Sim |
| `PENDENTE` | Peça com defeito a resolver | Sim, mas bloqueia DISPONIVEL |
| `PENDENCIA_RESOLVIDA` | Voltou a MONTADA após pendência | Sim (efetivo MONTADA) |
| `DISPONIVEL` | Tag + manual + pronta para separação | Sim |
| `REVERTIDA_PARA_MONTADA` | Operador reverteu disponibilização | Sim (efetivo MONTADA) |
| `SEPARADA` | Vinculada a separação ativa | Não |
| `FATURADA` | NF Q.P.A. importada e bateu | Não |
| `CANCELADA` | Separação cancelada (volta como DISPONIVEL via novo evento) | Depende |
| `MOTO_FALTANDO` | Declarada no recibo mas não chegou | Não |

---

## Modelo de dados (16 tabelas)

Ver spec em `docs/superpowers/specs/2026-05-07-motos-assai-design.md` §4.

Cadastros: `assai_cd`, `assai_loja`, `assai_modelo`, `assai_modelo_alias`.
Identidade: `assai_moto`, `assai_moto_evento`.
Pipeline: `assai_pedido_venda*`, `assai_compra_motochefe*`, `assai_recibo_motochefe*`.
Saída: `assai_separacao*`, `assai_nf_qpa*`.

---

## Lista de constantes/aliases por arquivo

- `app/motos_assai/models/moto.py`: `EVENTO_*`, `EVENTOS_VALIDOS`, `EVENTOS_EM_ESTOQUE`
- `app/motos_assai/models/pedido.py`: `PEDIDO_STATUS_*`, `PEDIDO_STATUS_VALIDOS`
- `app/motos_assai/models/compra.py`: `COMPRA_STATUS_*`, `COMPRA_STATUS_VALIDOS`
- `app/motos_assai/models/recibo.py`: `RECIBO_STATUS_*`, `DIVERGENCIA_*`
- `app/motos_assai/models/separacao.py`: `SEPARACAO_STATUS_*`
- `app/motos_assai/models/nf_qpa.py`: `NF_STATUS_*`
- `app/motos_assai/models/modelo.py`: `ALIAS_TIPO_*`

---

## Próximos passos (Planos 2 e 3)

- **Plano 2**: parsers de pedido VOE Q.P.A. + recibo Motochefe + wizard de recebimento físico
- **Plano 3**: montagem, disponibilizar, separação, Excel Q.P.A., importação de NF Q.P.A.

---

## Referências

- Spec: `docs/superpowers/specs/2026-05-07-motos-assai-design.md`
- Plano 1: `docs/superpowers/plans/2026-05-07-motos-assai-foundation.md`
- Padrão arquitetural de referência: `app/hora/CLAUDE.md`
- Parser base de PDF: `app/pedidos/leitura/base.py:PDFExtractor`
- Parser DANFE Q.P.A. (CarVia, sem modificar): `app/carvia/services/parsers/danfe_pdf_parser.py`
- Wizard QR de referência: `app/templates/hora/recebimento_wizard.html`
