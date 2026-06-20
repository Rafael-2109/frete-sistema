<!-- doc:meta
tipo: reference
camada: L3
sot_de: backfill manual / modelo de dados do modulo motos_assai (para o agente)
hub: .claude/skills/corrigindo-dados-assai/SKILL.md
superseded_by: —
atualizado: 2026-06-20
-->
# Mapa do Modulo Motos Assai — para backfill e scripts ad-hoc

> **Papel:** da ao agente o modelo de dados, a maquina de status, os services
> reutilizaveis e os guard-rails do modulo Motos Assai, para operar a skill
> `corrigindo-dados-assai` e escrever scripts Python sob medida quando ela nao
> cobrir um caso. **Abra quando:** for fazer backfill/correcao no modulo ou
> escrever um script ad-hoc para a Rayssa.

Fonte de campos: SEMPRE os schemas JSON em
`.claude/skills/consultando-sql/schemas/tables/assai_*.json` — este doc resume
relacoes e regras de negocio, NAO substitui o schema. Autonomia para scripts
ad-hoc autorizada pelo Rafael, desde que o agente entenda tabelas e relacoes.

## Indice
- [1. Fronteira: o que isola da Nacom](#1-fronteira-o-que-isola-da-nacom)
- [2. Maquina de status por entidade](#2-maquina-de-status-por-entidade)
- [3. Modelo de dados / FKs / ordem de insercao](#3-modelo-de-dados--fks--ordem-de-insercao)
- [4. Services reutilizaveis (nunca SQL cru)](#4-services-reutilizaveis-nunca-sql-cru)
- [5. Guard-rails inegociaveis](#5-guard-rails-inegociaveis)
- [6. Colunas canonicas da planilha](#6-colunas-canonicas-da-planilha)
- [7. Template para script ad-hoc seguro](#7-template-para-script-ad-hoc-seguro)

---

## 1. Fronteira: o que isola da Nacom

O **faturamento das motos Assai (NF Q.P.A.) NAO se mistura com o faturamento da
Nacom Goya** — a Q.P.A. e PJ propria, fora do Odoo/financeiro Nacom (zero escrita
em `faturamento_produto`/`contas_a_receber`/`relatorio_faturamento`).

O **unico** cruzamento e **logistico**: quando uma `AssaiSeparacao` chega a
FECHADA/CARREGADA/FATURADA, o `separacao_mirror_service` cria linhas-espelho em
`separacao` Nacom (`separacao_lote_id='ASSAI-SEP-{id}'`) -> entram em
`Embarque`/`EmbarqueItem` -> `EntregaMonitorada` (origem `OP_ASSAI`). A Nacom so
entra como **transportadora** (cotacao/embarque/frete/monitoramento).

Implicacao para backfill:
- **ENTRADA/ESTOQUE/ESTADO/CADASTRO** (chassis, eventos ESTOQUE/MONTADA/PENDENTE/
  DISPONIVEL/DEMONSTRACAO, loja, modelo, item de pedido ABERTO) = **100% isolado**:
  nao cria espelho, nao toca embarque/frete. Backfill seguro.
- **SEPARACAO FECHADA+ / NF** = aciona o espelho Nacom automaticamente. Por isso a
  skill NAO cria separacao/espelho a mao; faturamento entra pela **NF real**
  (`--importar-nf`), que dispara o caminho oficial.

---

## 2. Maquina de status por entidade

### Chassi (`assai_moto_evento.tipo`) — APPEND-ONLY
Estado de uma moto = **tipo do ULTIMO evento** (`ORDER BY ocorrido_em DESC, id DESC`).
NUNCA UPDATE/DELETE em `assai_moto_evento`; correcao = NOVO evento.

Eventos validos: `ESTOQUE, MONTADA, PENDENTE, PENDENCIA_RESOLVIDA, DISPONIVEL,
REVERTIDA_PARA_MONTADA, SEPARADA, CARREGADA, FATURADA, CANCELADA, MOTO_FALTANDO,
DEMONSTRACAO`.
- `EVENTOS_EM_ESTOQUE` = {ESTOQUE, MONTADA, PENDENTE, DISPONIVEL}
- `EVENTOS_FORA_ESTOQUE` = {SEPARADA, CARREGADA, FATURADA, CANCELADA, MOTO_FALTANDO, **DEMONSTRACAO**}

Transicoes (guard = `status_efetivo` ANTES de emitir):
```
ESTOQUE -> MONTADA            (registrar_montagem)
ESTOQUE -> PENDENTE           (registrar_montagem pendencia=True; descricao>=3)
PENDENTE -> PENDENCIA_RESOLVIDA -> MONTADA   (resolver_pendencia; 2 eventos)
{MONTADA, DISPONIVEL, SEPARADA} -> PENDENTE  (enviar_para_pendencia; defeito tardio)
{MONTADA, REVERTIDA_PARA_MONTADA} -> DISPONIVEL  (disponibilizar)
DISPONIVEL -> REVERTIDA_PARA_MONTADA   (reverter_para_montada; motivo>=3)
DISPONIVEL -> SEPARADA        (registrar_chassi; saldo+lock)
SEPARADA -> DISPONIVEL        (desfazer_chassi / cancelar_separacao)
SEPARADA/FECHADA -> CARREGADA (carregamento finalizado)
SEPARADA -> FATURADA          (NF Q.P.A. BATEU — UNICO caminho)
FATURADA -> CARREGADA/SEPARADA (cancelar_nf_qpa)
FATURADA -> PENDENTE          (devolucao NFd)
```
> **Backfill (a skill) so opera ESTOQUE/MONTADA/PENDENTE/DISPONIVEL/DEMONSTRACAO.**
> SEPARADA/CARREGADA/FATURADA = fluxo oficial (separar / NF).

### Demais entidades (estado / terminais)
| Entidade | Estados | Terminais / regra |
|----------|---------|-------------------|
| `assai_pedido_venda.status` | ABERTO, PARCIALMENTE_FATURADO, FATURADO, CANCELADO | **CALCULADO** por `recalcular_status_pedido` (qtd de SeparacaoItem em sep FATURADA, menos devolvidos). CANCELADO e terminal (nao recalcula). NAO setar a mao. |
| `assai_compra_motochefe.status` | ABERTA, RECEBIMENTO_PARCIAL, FECHADA, CANCELADA | muda so via `finalizar_recebimento` quando todos recibos finais |
| `assai_recibo_motochefe.status` | RESOLVENDO_DUPLICIDADE, RECEBIDO_AGUARDANDO_CONFERENCIA, EM_CONFERENCIA, CONCLUIDO, COM_DIVERGENCIA | CONCLUIDO/COM_DIVERGENCIA finais |
| `assai_separacao.status` | EM_SEPARACAO, FECHADA, CARREGADA, FATURADA, CANCELADA | CANCELADA terminal; FATURADA nao cancela direto (cancele a NF); FECHADA+/espelha Nacom |
| `assai_nf_qpa.status_match` | BATEU, DIVERGENTE, NAO_RECONCILIADO, CANCELADA | CANCELADA terminal; BATEU = unico que sobe pedido p/ FATURADO |
| `assai_cce.status` | PENDENTE, APLICADA, IGNORADA, ERRO | APLICADA terminal (guard `chassis_aplicados`); IGNORADA p/ DUPLICATAS/ENDERECO |
| `assai_carregamento.status` | EM_CARREGAMENTO, FINALIZADO, CANCELADO | CANCELADO terminal; 1 FINALIZADO por sep |
| `assai_divergencia` | pendente (`resolvida_em IS NULL`) vs resolvida | UNICO estado que ADMITE UPDATE (resolver) |

---

## 3. Modelo de dados / FKs / ordem de insercao

PK serial em todas. `*_por_id`/`operador_id` -> `usuarios.id` (ON DELETE SET NULL,
NULLABLE). Para backfill, usar `id=74` (Claude) ou `id=1` (Rafael) — **nunca inventar usuario**.

**Ordem topologica (inserir nivel N depois de N-1):**
```
N0 cadastro:   assai_loja | assai_modelo | assai_cd
N1:            assai_modelo_alias(->modelo) | assai_moto(->modelo) |
               assai_pedido_venda | assai_compra_motochefe
N2:            assai_pedido_venda_loja(->pedido,loja) | assai_compra_motochefe_pedido |
               assai_recibo_motochefe(->compra) | assai_moto_evento(liga por chassi STRING)
N3:            assai_pedido_venda_item(->pedido,pedido_loja,loja,modelo) |
               assai_recibo_item(->recibo,modelo) | assai_separacao(->pedido,loja)
N4:            assai_separacao_item | assai_separacao_saldo_modelo |
               assai_carregamento | assai_nf_qpa(->sep,loja) | assai_pedido_excel
N5:            assai_carregamento_item | assai_nf_qpa_item(->nf,sep_item) | assai_cce(->nf)
N6:            assai_nf_qpa_item_vinculo_historico
```

**Obrigatorios e UNIQUEs criticos para backfill:**
- `assai_moto`: `chassi` UNIQUE NOT NULL (insert-once; normalizar `strip().upper()`), `modelo_id` NOT NULL.
- `assai_moto_evento`: `chassi`, `tipo` NOT NULL. **CHECK `ck_assai_moto_evento_tipo`** valida `tipo` (migration 24/33). Sem FK p/ moto (liga por string). `dados_extras` JSONB.
- `assai_loja`: `numero` (UNIQUE), `nome`, `razao_social`, `cnpj` NOT NULL. ATENCAO: `numero` inconsistente em prod (`014` vs `14`) — normalize.
- `assai_modelo`: `codigo` (UNIQUE), `nome` NOT NULL. Campos uteis: `descricao_qpa`, `codigo_qpa`, `regex_chassi`, `peso_kg`.
- `assai_pedido_venda`: `numero` UNIQUE. `import_resumo` JSON (migration 32 — pode faltar em local).
- `assai_pedido_venda_loja`: UNIQUE `(pedido_id, loja_id)`. `agendamento_confirmado` NOT NULL server_default false.
- `assai_pedido_venda_item`: UNIQUE `(pedido_id, loja_id, modelo_id)`. `pedido_loja_id` NOT NULL (crie cabecalho antes).
- `assai_recibo_item`: UNIQUE PARCIAL `(recibo_id, chassi)` WHERE `ativo=TRUE` **e** UNIQUE PARCIAL `(chassi)` WHERE `ativo=TRUE` (global) — so 1 item ATIVO por chassi no sistema.
- `assai_separacao`: SEM unique hoje (drop migration 13 — N seps ativas por pedido,loja). Unicidade de chassi-em-sep = runtime (lock + status DISPONIVEL), NAO constraint.
- `assai_separacao_saldo_modelo`: UNIQUE `(separacao_id, modelo_id)` + CHECK `qtd_planejada > 0`.
- `assai_nf_qpa`: `chave_44` UNIQUE NOT NULL; UNIQUE PARCIAL `(separacao_id)` WHERE status != CANCELADA.
- `assai_carregamento`: UNIQUE PARCIAL `(separacao_id)` WHERE status='FINALIZADO'.
- `assai_cce`: `protocolo_cce` UNIQUE; `chassis_aplicados` JSON.

> Os UNIQUE/CHECK parciais (recibo_item, carregamento, nf_qpa, pedido_excel)
> existem **so nas migrations SQL**, NAO no model `.py`. Confie nos schemas JSON
> (gerados de prod) para o estado vigente.

---

## 4. Services reutilizaveis (nunca SQL cru)

Padrao de commit: a maioria **commita interno**; uma parte so faz `flush` e o
**caller commita** (compor numa transacao). Em script, prefira os "caller commita"
quando precisar agrupar multiplas operacoes; commite no fim.

| Service.funcao | O que faz | Commit |
|----------------|-----------|--------|
| `moto_evento_service.emitir_evento(chassi, tipo, operador_id, observacao, dados_extras, ocorrido_em)` | ATOMO base de evento; `ocorrido_em` p/ data retroativa (Brasil naive). Valida tipo. | flush (caller) |
| `moto_evento_service.status_efetivo / ultimo_evento / eventos_chassi / chassis_em_estoque` | leitura de estado | read |
| `montagem_service.registrar_montagem / resolver_pendencia / enviar_para_pendencia` | transicoes de montagem (sem `ocorrido_em`) | commit |
| `disponibilizar_service.disponibilizar / reverter_para_montada` | MONTADA<->DISPONIVEL | commit |
| `modelo_resolver.resolver_modelo(texto) / resolver_por_codigo_qpa(cod)` | texto -> AssaiModelo | read |
| `chassi_validator.validar_chassi(chassi, modelo_id)` | regex nao-bloqueante | read |
| `recebimento_service.registrar_conferencia(...)` | cria moto + ESTOQUE via recibo (SOT cor/modelo) | commit |
| `loja_service.criar_loja(dados) / atualizar_loja(id, dados)` | cadastro de loja (+hook re-match NF por CNPJ) | commit |
| `modelo_service.criar_modelo(dados) / atualizar_modelo(id, dados)` | cadastro de modelo | commit |
| `pedido_service.adicionar_item_manual / editar_item_manual / remover_item_manual` | item de pedido **ABERTO** | commit |
| `parsers.nf_qpa_adapter.importar_nf_qpa(pdf_bytes, nome, user)` | grava NF Q.P.A. do PDF + match (pode subir FATURADA) | commit |
| `parsers.nf_qpa_adapter.criar_nf_qpa_de_dados(dados, user)` | grava NF Q.P.A. **sem PDF** (dict: chave_44, numero, loja_id/destinatario_cnpj, valor_total, itens[]) + match. Lastro = a NF. | commit |
| `parsers.nf_qpa_adapter.vincular_nf_manualmente(nf_id, pedido_id, user)` | re-match NF NAO_RECONCILIADO por CNPJ | flush (caller) |
| `cancelamento_nf_service.aplicar_correcao_cce(nf_id, [(antigo,novo)], numero_cce, user)` | troca chassi em NF + reverte FATURADA antigo + re-match | flush (caller) |
| `cancelamento_nf_service.cancelar_nf_qpa(nf_id, motivo, user)` | cancela NF + reverte FATURADA dos chassis | flush (caller) |
| `separacao_service.*` | criar/registrar/finalizar/cancelar/realocar/substituir (toca espelho Nacom) | depende da funcao |
| `pos_venda_service.criar_ocorrencia(chassi, categoria, descricao, user)` | ocorrencia pos-venda (chassi vendido) | commit |
| `pedido_status_service.recalcular_status_pedido(pedido_id)` | recalcula status do pedido (apos mexer em sep/NF) | flush (caller) |

---

## 5. Guard-rails inegociaveis

1. **APPEND-ONLY**: nunca UPDATE/DELETE em `assai_moto_evento`. Correcao = novo evento (compensatorio), com `ocorrido_em` retroativo se preciso.
2. **FATURADA com lastro**: o proibido e o evento FATURADA **orfao** (sem `AssaiNfQpa`). NAO precisa vir de PDF — grave a NF por PDF (`importar_nf_qpa`) OU sem PDF (`criar_nf_qpa_de_dados`, dados estruturados); em ambos a NF e o lastro e o match faz a baixa. **Nunca** emitir FATURADA avulso nem fazer INSERT cru em `separacao`/`assai_nf_qpa`.
3. **Recebimento e SOT de cor/modelo**: so defina cor/modelo ao **criar** a moto; nunca sobrescreva moto existente (use recebimento).
4. **Tipo de evento valido**: so `EVENTOS_VALIDOS` (passe por `emitir_evento`, que valida; nunca instancie `AssaiMotoEvento` na mao). Tipo novo no model exige tambem ALTER da CHECK `ck_assai_moto_evento_tipo` (migration).
5. **Espelho Nacom e automatico**: nunca INSERT/UPDATE direto em `separacao`/`EmbarqueItem`/`EntregaMonitorada`. Use os services de mirror; melhor ainda, deixe o fluxo oficial de NF propagar.
6. **Pedido editavel so ABERTO**: item de pedido so muda em status ABERTO e loja sem separacao ativa.
7. **Idempotencia**: dry-run default + `--confirmar`; tagueie `dados_extras.origem='backfill:...'` e pule por `status_efetivo`. Nunca TRUNCATE/reset em prod.

---

## 6. Colunas canonicas da planilha

A skill (`--planilha-estado`) procura o cabecalho nas 30 primeiras linhas pela
celula da coluna-chassi. Colunas reconhecidas (nomes default, ajustaveis por flag):

| Coluna | Uso | Flag |
|--------|-----|------|
| `CHASSI` | chave (obrigatoria) | `--coluna-chassi` |
| `STATUS` | estado-alvo (mapeado) | `--coluna-status` |
| `MODELO` | texto -> modelo (se criar) | `--coluna-modelo` |
| `COR` | cor (se criar) | `--coluna-cor` |
| `DATA DE CHEGADA` | `ocorrido_em` dos eventos | `--coluna-data` |

Mapa STATUS -> alvo: `ESTOQUE|EM ESTOQUE`->ESTOQUE; `MONTADA|MONTADO`->MONTADA;
`PENDENTE|PENDENCIA`->PENDENTE; `DISPONIVEL|PRONTA`->DISPONIVEL;
`DEMONSTRACAO|DEMO`->DEMONSTRACAO. `FATURADO/SEPARADO/...` = **pulado** (use fluxo oficial).

> **Cronologia fina (2 datas):** para a sequencia PENDENTE@chegada ->
> PENDENCIA_RESOLVIDA/MONTADA@faturamento (caso das 143 motos com defeito), use
> 2 passagens pontuais: `--definir-estado --estado PENDENTE --ocorrido-em <chegada>`
> e depois `--definir-estado --estado MONTADA --ocorrido-em <faturamento>` (a cadeia
> PENDENTE->MONTADA emite PENDENCIA_RESOLVIDA+MONTADA na data de faturamento).

---

## 7. Template para script ad-hoc seguro

Quando a skill nao cobrir (carga com regra propria, reconciliacao complexa),
escreva um script reusando os services. No **agente web** crie o script em `/tmp/`
com a tool **Write** (`permissions.py` so' libera Write/Edit em `/tmp` — fail-closed,
nunca o codigo de producao) e rode via **Bash**; no **Claude Code** (dev/4-maos)
salve em `scripts/migrations/` se for recorrente. **Sempre** dry-run default +
`--confirmar`, idempotente, sem inventar usuario.

```python
#!/usr/bin/env python3
"""Backfill ad-hoc Motos Assai — <descreva>. Dry-run default; --confirmar efetiva."""
import sys, os, argparse, contextlib, io
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
with contextlib.redirect_stdout(io.StringIO()):
    from app import create_app, db

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--user-id', type=int, required=True)
    ap.add_argument('--confirmar', action='store_true')
    args = ap.parse_args()

    with contextlib.redirect_stdout(io.StringIO()):
        app = create_app()
    with app.app_context():
        # 0) autorizacao
        from app.auth.models import Usuario
        u = Usuario.query.get(args.user_id)
        assert u and u.pode_acessar_motos_assai(), 'sem permissao motos_assai'

        # 1) leia o estado atual (status_efetivo) ANTES de decidir (idempotencia)
        from app.motos_assai.services.moto_evento_service import status_efetivo, emitir_evento

        plano = []   # monte a lista do que faria
        # ... percorra sua fonte (planilha/lista), pule o que ja esta no alvo ...

        if not args.confirmar:
            print('DRY-RUN:', plano)         # NADA mutado
            return

        # 2) execute reusando SERVICES (nunca INSERT/UPDATE cru; nunca DELETE evento)
        for item in plano:
            emitir_evento(chassi=item['chassi'], tipo=item['tipo'],
                          operador_id=args.user_id, ocorrido_em=item.get('data'),
                          dados_extras={'origem': 'backfill-adhoc:<nome>'})
        db.session.commit()                  # commit unico no fim (tudo-ou-nada)
        print('OK', len(plano))

if __name__ == '__main__':
    main()
```

**Checklist do script ad-hoc:** (1) autorizacao; (2) ler estado antes (idempotente);
(3) dry-run default; (4) reusar services; (5) respeitar os 7 guard-rails da secao 5;
(6) commit unico no fim, rollback em erro; (7) validar pos-commit; (8) FK de usuario
= 74/1, nunca inventar.

---

## Fontes

- Campos de tabela (SOT): `.claude/skills/consultando-sql/schemas/tables/assai_*.json`
- Regras de negocio / planos do modulo: `app/motos_assai/CLAUDE.md`
- Services (assinaturas/commit): `app/motos_assai/services/*.py` e `services/parsers/nf_qpa_adapter.py`
- Constantes de evento/status: `app/motos_assai/models/*.py`
- Espelhamento Nacom: `app/motos_assai/services/separacao_mirror_service.py`
- CHECK constraint de evento: `scripts/migrations/motos_assai_24_*` + `motos_assai_33_*`
