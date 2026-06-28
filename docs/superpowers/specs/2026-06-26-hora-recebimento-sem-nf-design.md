<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-26
-->
# HORA — Recebimento por filial sem NF (NF provisória)

> **Papel:** spec de design do recebimento de motos na loja HORA selecionando **apenas a loja**, sem preencher a NF. Modela uma **NF provisória** (container) cujo gabarito é o snapshot dos pedidos pendentes da filial; a NF real é gravada por cima depois, promovendo a hierarquia de status.

## Indice

- [Contexto](#contexto)
- [Escopo](#escopo)
- [Decisões aprovadas (Q&A)](#decisões-aprovadas-qa)
- [Máquina de estados](#máquina-de-estados)
- [Modelo de dados](#modelo-de-dados)
- [Serviços](#serviços)
- [Efeito nos demais locais](#efeito-nos-demais-locais)
- [UI e rotas](#ui-e-rotas)
- [Migration](#migration)
- [Não-objetivos](#não-objetivos)
- [Testes](#testes)
- [Riscos e pontos de atenção](#riscos-e-pontos-de-atenção)

## Contexto

Hoje o recebimento da HORA é modelado como **"uma NF chegou numa loja"**: `HoraRecebimento.nf_id` é FK **NOT NULL** e a NF de entrada é o **gabarito** contra o qual a conferência cega deriva divergências (chassi fora da NF = `CHASSI_EXTRA`; modelo/cor diferentes = `MODELO_DIFERENTE`/`COR_DIFERENTE`; chassi da NF sem conferência = `MOTO_FALTANDO`). O operador precisa importar o DANFE **antes** de receber.

O dono quer **receber selecionando só a loja**, porque na prática a moto chega fisicamente antes da NF estar disponível no sistema. Em vez de tornar `nf_id` nullable (que espalharia guardas-`None` por ~12 call-sites de service, 5 templates, 2 skills do Agente Lojas HORA e o dashboard), a abordagem aprovada cria uma **NF provisória**: `nf_id` permanece **NOT NULL**, o recebimento sempre tem uma NF — ela só é do tipo `PROVISORIA`. Quando a NF real chega, é **gravada por cima** da provisória (mesma linha, promovida a `REAL`), reusando o motor de reconciliação que já existe.

**Fontes do estado atual:**
- `app/hora/models/recebimento.py:18-23` — `nf_id` FK NOT NULL; `:59-61` UNIQUE(`nf_id`,`loja_id`).
- `app/hora/services/recebimento_service.py:212` `iniciar_recebimento` (exige NF); `:299` `registrar_conferencia_cega`; `:506` `finalizar_recebimento` (MOTO_FALTANDO em `:557-558` via `rec.nf.itens_considerados`); `:1766` `_redefinir_divergencias` (`item_nf None → CHASSI_EXTRA` em `:1780`); `:1701` `_garantir_moto` (sem NF cria `CHASSI_EXTRA_DESCONHECIDO` em `:1724`); `:634/715` `reprocessar_recebimentos_para_nf` (motor de reconciliação).
- `app/hora/services/estoque_service.py:23-30` — `EVENTOS_EM_ESTOQUE` inclui `RECEBIDA` **e** `CONFERIDA` (moto recebida sem item de NF já conta em estoque).
- `app/hora/services/matching_service.py:23` `STATUS_CANDIDATOS = ('ABERTO','PARCIALMENTE_FATURADO')`; `:110-118` `candidatos_pedidos_para_nf` filtra pedidos da loja por esses status — é a query do "snapshot da filial"; `:50-55` `_chassis_pedido_preenchidos`/`_chassis_pedido_pendentes`.
- `app/hora/services/pedido_service.py:84-130` — item de pedido de compra pode nascer **sem chassi** ("pedido pré-NF"); o chassi é atribuído quando a NF chega.
- `app/hora/models/compra.py:208,211` — `HoraNfEntradaItem.numero_chassi` e `preco_real` são **NOT NULL** (impede materializar o esperado-sem-chassi como item de NF).
- `app/hora/services/moto_service.py:14-121` `get_or_create_moto` (insert-once por chassi PK); `:124-165` `registrar_evento`.

## Escopo

**Dentro do escopo:**
- Criar recebimento informando **apenas a loja** (sem NF).
- Materializar um **snapshot congelado** dos pedidos pendentes da filial como gabarito (`hora_recebimento_esperado`).
- Conferência cega normal (operador declara chassi+modelo+cor → cria a moto → evento `CONFERIDA`/`RECEBIDA` → entra em estoque).
- **Anexar a NF real dentro do recebimento** (re-import do DANFE), promovendo a NF `PROVISORIA → REAL`, reprocessando divergências e avançando o status fiscal do pedido.
- Isolamento fiscal das NFs provisórias (não poluir valor de estoque / listas de NF).

**Fora do escopo (descartado pelo usuário):**
- Tornar `hora_recebimento.nf_id` nullable.
- Reconciliação automática de uma NF importada pelo fluxo `/nfs/upload` separado (a NF real entra **dentro** do recebimento — D4).
- O recebimento físico atribuir chassi ao `HoraPedidoItem` (quem atribui é a NF real — D6).
- Marcar o pedido de compra como `FATURADO` pelo recebimento físico (só a NF real avança a hierarquia fiscal — D9).

## Decisões aprovadas (Q&A)

| ID | Decisão | Fonte |
|----|---------|-------|
| D1 | Gabarito = **snapshot dos pedidos pendentes da filial** (`status ∈ {ABERTO, PARCIALMENTE_FATURADO}`, `loja_destino_id == loja`), congelado no momento do recebimento. | usuário |
| D2 | Modelar via **NF provisória**: `hora_recebimento.nf_id` permanece NOT NULL; a NF ganha `tipo ∈ {PROVISORIA, REAL}`. | usuário |
| D3 | Snapshot **congelado/materializado** em tabela nova `hora_recebimento_esperado` (aceita esperado **sem chassi**, que `HoraNfEntradaItem` não permite). | usuário + `compra.py:208` |
| D4 | NF real é **anexada dentro do recebimento** (re-import do DANFE), promovendo a **mesma** linha `PROVISORIA → REAL`. | usuário |
| D5 | **Conferência é SOT** de cor/modelo (regra 2026-05-06): a NF real, ao divergir, **só gera divergência**, não sobrescreve a moto. | usuário |
| D6 | O recebimento físico **não atribui** chassi ao `HoraPedidoItem`; a NF real faz isso. | usuário |
| D7 | Chassi fora de todos os pedidos pendentes → **aceita e sinaliza** `CHASSI_EXTRA` (não bloqueia; fluxo permissivo). | usuário |
| D8 | No recebimento provisório, `finalizar_recebimento` **não** gera `MOTO_FALTANDO` (snapshot é lista aberta da filial — não-conferidos seguem pendentes). | derivado de D1 |
| D9 | Status do pedido de compra (`ABERTO→PARCIAL→FATURADO`) é **fiscal**: só avança quando a NF real é anexada, não no recebimento físico. | derivado de D4 |

## Máquina de estados

**NF (`hora_nf_entrada.tipo`)** — hierarquia, só sobe:
```
PROVISORIA ──(anexar NF real)──> REAL
```

**Recebimento (`hora_recebimento.status`)** — inalterado:
```
AGUARDANDO_QTD → EM_CONFERENCIA → CONCLUIDO | COM_DIVERGENCIA
```
- No provisório, `CONCLUIDO` se só houve conferências limpas/`CHASSI_EXTRA`-free; `COM_DIVERGENCIA` se houve `CHASSI_EXTRA` ou `AVARIA_FISICA`.
- Anexar a NF real roda `reprocessar_recebimentos_para_nf` → pode mover `CONCLUIDO → COM_DIVERGENCIA` se a real revelar divergência (é a verdade; "respeita a hierarquia" — a chegada da NF nunca rebaixa para antes de `EM_CONFERENCIA`).

**Pedido de compra (`hora_pedido.status`)** — fiscal, só avança com a NF real:
```
ABERTO → PARCIALMENTE_FATURADO → FATURADO   (via matching, disparado pela NF REAL)
```

## Modelo de dados

**1. `hora_nf_entrada` — coluna nova:**
```
tipo  VARCHAR(20)  NOT NULL  DEFAULT 'REAL'   -- {'PROVISORIA','REAL'}; NFs existentes = REAL
```
Property de conveniência no modelo: `provisoria` → `self.tipo == 'PROVISORIA'`.

**2. `hora_recebimento_esperado` — tabela nova (snapshot congelado):**
```
id                          SERIAL PK
recebimento_id              INTEGER NOT NULL  REFERENCES hora_recebimento(id)
pedido_id                   INTEGER NULL      REFERENCES hora_pedido(id)
pedido_item_id              INTEGER NULL      REFERENCES hora_pedido_item(id)
modelo_id                   INTEGER NULL      REFERENCES hora_modelo(id)
cor                         VARCHAR(50) NULL
chassi_esperado             VARCHAR(30) NULL  -- preenchido só quando o pedido já tinha chassi
preco_esperado              NUMERIC(15,2) NULL
consumido_por_conferencia_id INTEGER NULL     REFERENCES hora_recebimento_conferencia(id)
criado_em                   TIMESTAMP NOT NULL
índices: (recebimento_id), (recebimento_id, modelo_id), (recebimento_id, chassi_esperado)
```

**3. NF provisória — valores dos campos NOT NULL de `hora_nf_entrada`:**
- `chave_44` = `'PROV' + uuid4().hex` (36 chars, único, cabe em 44).
- `numero_nf` = `'PROV-' + <recebimento_seq>` (placeholder).
- `cnpj_emitente` = `''` (sentinela; emitente desconhecido até a NF real).
- `cnpj_destinatario` = `loja.cnpj`.
- `data_emissao` = data de hoje; `valor_total` = `0`; `tipo` = `'PROVISORIA'`.
- `loja_destino_id` = loja recebedora.
- **Sem** `HoraNfEntradaItem` (o gabarito vive em `hora_recebimento_esperado`).

**`hora_recebimento` permanece intacto** — `nf_id` continua NOT NULL. A UNIQUE(`nf_id`,`loja_id`) não atrapalha (cada provisória tem `nf_id` distinto).

## Serviços

Todos em `app/hora/services/recebimento_service.py` salvo indicação.

- **`criar_recebimento_sem_nf(loja_id, operador) -> HoraRecebimento`** (novo):
  1. Cria `HoraNfEntrada(tipo='PROVISORIA', ...)` (campos acima) + flush.
  2. Materializa o snapshot: `matching_service` → pedidos `STATUS_CANDIDATOS` da loja; para cada `HoraPedidoItem` ainda **não faturado** (sem chassi em NF vinculada), cria `HoraRecebimentoEsperado(chassi_esperado=item.numero_chassi, modelo_id, cor, preco_esperado=item.preco_compra_esperado, pedido_id, pedido_item_id)`.
  3. `iniciar_recebimento(nf_id=provisoria.id, loja_id, operador)` (reusa).
  - Retorna o recebimento (status `AGUARDANDO_QTD`).

- **`_gabarito_provisorio(rec, chassi, modelo_id_conf)`** (novo, privado): casa um chassi conferido contra o snapshot — (a) item com `chassi_esperado == chassi`; (b) senão item sem chassi com `modelo_id == modelo_id_conf` ainda não consumido; senão `None`. Marca `consumido_por_conferencia_id`. **Lógico** — não toca `HoraPedidoItem` (D6).

- **`_redefinir_divergencias`** (modificar `:1766`): branch — se `rec.nf.provisoria`, deriva contra o snapshot via `_gabarito_provisorio`: sem match → `CHASSI_EXTRA` (D7); com match → sem divergência de modelo/cor (operador é SOT, gabarito é referência); `AVARIA_FISICA` se marcada. **Não** consulta `HoraNfEntradaItem`.

- **`_garantir_moto`** (modificar `:1701`): no modo provisório com `modelo_id_conferido`/`cor_conferida` presentes, criar a moto com o **modelo/cor declarados** (não o sentinela `CHASSI_EXTRA_DESCONHECIDO`).

- **`finalizar_recebimento`** (modificar `:506`): se `rec.nf.provisoria`, **pular** o bloco `MOTO_FALTANDO` (`:557-605`) — não há remessa fechada (D8). `status` derivado só de `CHASSI_EXTRA`/`AVARIA`.

- **`anexar_nf_real_ao_recebimento(recebimento_id, pdf_bytes, operador) -> HoraNfEntrada`** (novo):
  1. `parse_danfe_to_hora_payload(pdf_bytes)`; valida que a `chave_44` real **não** existe em outra NF (dedup).
  2. Promove a NF provisória: `tipo='REAL'`, grava `chave_44`/`numero_nf`/`cnpj_emitente`/`valor_total` reais; cria os `HoraNfEntradaItem` reais (via `get_or_create_moto(fallback_sentinela=True)` — idempotente; reusa motos já criadas na conferência).
  3. `reprocessar_recebimentos_para_nf(nf.id)` → reavalia divergências conferido × NF real (motor existente).
  4. Se houver pedido vinculável: `matching` → `atualizar_status_pedido_por_faturamento` (avança a hierarquia fiscal — D9).
  - Retorna a NF promovida.

## Efeito nos demais locais

- **Estoque** (`estoque_service`): nenhuma mudança — `CONFERIDA`/`RECEBIDA` já contam em estoque (`:23-30`). Moto provisória entra normal.
- **`chassi_protecao_service.chassi_protegido`** (`:14`): **estender** para considerar protegida a moto com conferência de recebimento ativa (hoje só protege chassi em `HoraPedidoItem`/`HoraNfEntradaItem`) — senão o backfill TagPlus pode sobrescrever a moto provisória (risco R2).
- **`resolucao_service`** (DEVOLVER lê `rec.nf_id`): funciona — a NF existe (provisória). Sem divergência além de avaria, o caminho "devolver via divergência" fica ocioso; devolução avulsa usa a rota standalone (`devolucoes.py:117` já aceita `nf_entrada_id=None`).
- **`assert_item_moto_consistente`** (`nf_entrada_service.py:255`): valida que **não** roda/falha sobre moto provisória (ela não tem `HoraNfEntradaItem` real nem `HoraPedidoItem`-com-chassi até a NF real — risco R1).
- **Skills do Agente Lojas HORA** (`conferindo-recebimento`, `rastreando-chassi`): leem `recebimento.nf` → funcionam (NF existe). Distinguir provisória na narrativa = cosmético.

## UI e rotas

`app/hora/routes/recebimentos.py`:
- `recebimentos_novo` (GET): remove o autocomplete de NF; só select de loja.
- `recebimentos_novo` (POST): chama `criar_recebimento_sem_nf(loja_id)` (não mais `nf_id`).
- **Nova** `recebimentos_anexar_nf` (POST, upload PDF): `anexar_nf_real_ao_recebimento`.
- `recebimentos_wizard`: cores sugeridas vêm do snapshot quando `rec.nf.provisoria` (em vez de `rec.nf.itens`).

Templates (`app/templates/hora/`):
- `recebimento_novo.html`: remove o bloco "NF de entrada".
- `recebimento_wizard.html:235`, `recebimentos_lista.html:61`, `recebimento_detalhe.html:57-59,71-76`: badge "Provisória" no lugar do número fiscal; esconder link `nfs_detalhe` e valor "Esperado NF" quando provisória; botão "Anexar NF real".

## Migration

`hora_58_recebimento_sem_nf.{sql,py}` (par idempotente — regra do projeto):
- `ALTER TABLE hora_nf_entrada ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'REAL';`
- `CREATE TABLE IF NOT EXISTS hora_recebimento_esperado (...)` + índices.
- `.py` espelha via `SQL_DDL` + `main()` (template `hora_48`/`hora_53`).

## Não-objetivos

- Multi-emitente / efeito fiscal real da NF provisória (provisória é gerencial, `valor_total=0`).
- NFC-e, séries por loja, contingência.
- Reconciliar NF importada por fluxo separado `/nfs/upload` (só "anexar dentro" — D4).
- Custo/margem da moto antes da NF real (a moto provisória entra sem `preco_real`; custo chega com a NF).

## Testes

`tests/hora/test_recebimento_sem_nf.py` (novo). Fixtures: `db`, `loja_factory`, `pedido_compra_factory`, `modelo_moto`. Cenários:
1. `criar_recebimento_sem_nf` cria NF `PROVISORIA` + snapshot materializado dos pedidos pendentes da loja.
2. Conferir chassi que casa o snapshot (por chassi e por modelo fungível) → `RECEBIDA`, moto criada com modelo/cor declarados, em estoque.
3. Conferir chassi fora do snapshot → `CHASSI_EXTRA`, **sem** bloquear (D7).
4. `finalizar_recebimento` provisório **não** gera `MOTO_FALTANDO` (D8).
5. `anexar_nf_real_ao_recebimento` promove `PROVISORIA→REAL`, cria itens reais, reprocessa divergências, reusa motos (insert-once), avança status do pedido.
6. NF real que diverge do conferido → gera divergência, **não** sobrescreve a moto (D5).
7. `chassi_protegido` cobre moto provisória (R2).

## Riscos e pontos de atenção

| ID | Risco | Mitigação |
|----|-------|-----------|
| R1 | `assert_item_moto_consistente` pressupõe moto ⟺ item de NF/pedido; moto provisória não tem âncora fiscal. | Validar que a asserção não roda sobre moto provisória; cobrir em teste. |
| R2 | `chassi_protegido` não cobre moto provisória → backfill TagPlus pode sobrescrever. | Estender `chassi_protegido` com "tem conferência de recebimento ativa". |
| R3 | Chave sintética `PROV…` colidindo com NF real ao promover. | uuid garante unicidade; dedup da `chave_44` real antes de promover. |
| R4 | Snapshot grande (filial com muitos pedidos abertos). | Materializa só itens não-faturados; índices por `recebimento_id`. |
