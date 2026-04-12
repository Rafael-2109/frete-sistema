# Auditoria admin_service.py — Bypass de Guards

**Data**: 2026-04-12 (Sprint 0 — Fundacao)
**Arquivo**: `app/carvia/services/admin/admin_service.py` (1246 LOC)

## Contexto

`admin_service.py` implementa operacoes administrativas (HARD_DELETE, FIELD_EDIT, RELINK) que **bypassam guards das rotas normais**. Esta auditoria mapeia os metodos e identifica gaps onde o admin pode corromper integridade que as rotas normalmente protegem.

**Principio**: Admin NAO deve ser atalho para violar integridade. Cada bypass e um risco. O que e bloqueado nas rotas normais deve ser bloqueado aqui (com override explicito + audit trail, se necessario).

---

## Inventario de Metodos

| Metodo | Linha | Bloqueios Atuais | Gaps |
|--------|-------|------------------|------|
| `excluir_nf` | 156 | **ZERO** | A-1, A-2 |
| `excluir_operacao` | 219 | Subs com FT em FATURADO/CONFERIDO | A-3, A-4 (=W8) |
| `excluir_subcontrato` | 337 | `fatura_transportadora_id != NULL` | A-5 |
| `excluir_fatura_cliente` | 391 | `conciliado=True` | A-6 |
| `excluir_fatura_transportadora` | 469 | `CarviaConciliacao` existente | A-7 |
| `excluir_cte_complementar` | 547 | `status=FATURADO` | A-8 |
| `excluir_custo_entrega` | 620 | `status=PAGO` | A-9 |
| `excluir_despesa` | 677 | `status=PAGO` | A-10 (=W13) |
| `excluir_receita` | 727 | `status=RECEBIDO` | (OK) |
| `editar_entidade` (FIELD_EDIT) | 854 | **ZERO** | A-11 (CRITICO) |
| `relink_operacao_nfs` | 949 | **ZERO** | A-12 |

---

## Gaps Identificados

### A-1: `excluir_nf` sem NENHUM guard — CRITICO

**Linha**: 156-213. Zero verificacoes antes de deletar.

**O que acontece**: Admin pode hard-deletar uma NF que esta ATIVA em qualquer CTe, Fatura, Subcontrato, CTe Comp, CustoEntrega. O metodo apenas nullifica FKs de `CarviaFaturaClienteItem.nf_id` e `CarviaFaturaTransportadoraItem.nf_id`. Deixa junctions `CarviaOperacaoNf` serem deletadas manualmente (mas a operacao continua existindo sem a NF).

**Deveria**: Chamar `nf.pode_cancelar()` do Sprint 0. Se ha dependencias, bloquear com listagem. Permitir override apenas com flag explicita `force=True` + audit detalhado.

### A-2: `excluir_nf` nao checa status da NF

Admin pode deletar NF ja CANCELADA (duplicata) ou ATIVA sem distincao.

**Deveria**: Bloquear se ATIVA com dependencias (usar A-1 guard).

### A-3: `excluir_operacao` nao checa CarviaCteComplementar/CustoEntrega ativos

Os cascade-deleta (L275-284) sem verificacao de status. Se ha CTe Complementar FATURADO ou CustoEntrega PAGO, deveria bloquear — hoje cascadeia silenciosamente.

**Deveria**: Chamar `operacao.pode_cancelar()` do Sprint 0 como pre-check adicional.

### A-4: `excluir_operacao` nao checa CarviaFrete — Gap W8 do plano

**Linha**: 219-331. Nao verifica `CarviaFrete.operacao_id`.

**O que acontece**: Hard-delete deixa CarviaFrete com FK pendente apontando para linha inexistente.

**Deveria**: Verificar `CarviaFrete.query.filter_by(operacao_id=op_id).count() > 0`. Se existir, bloquear com instrucao "Desvincule do Frete #X primeiro."

### A-5: `excluir_subcontrato` nao checa CarviaFrete.frete_id

**Linha**: 337-385. Checa apenas `fatura_transportadora_id != NULL`.

**O que acontece**: Sub vinculado a CarviaFrete via `frete_id` pode ser deletado. Frete perde o subcontrato mas mantem o valor referenciado.

**Deveria**: Verificar `sub.frete_id` (nao so fatura) e verificar tambem `CarviaFrete.subcontrato_id` (FK deprecated).

### A-6: `excluir_fatura_cliente` — divergencia entre `conciliado=True` e `status='PAGA'`

**Linha**: 408. Checa `getattr(fatura, 'conciliado', False)`.

**Problema**: CarviaFaturaCliente tem DOIS indicadores financeiros:
- `status == 'PAGA'` (estado do status machine)
- `conciliado == True` (flag booleano)

Sao sincronizados? Normalmente sim, mas se divergirem (ex: PAGA sem conciliado, via FC direto), o guard falha.

**Deveria**: Checar ambos — `if fatura.status == 'PAGA' or fatura.conciliado: block`.

### A-7: `excluir_fatura_transportadora` — nao checa status_conferencia

**Linha**: 486. Checa apenas `CarviaConciliacao` existente.

**Problema**: Uma fatura CONFERIDA mas nao conciliada passaria. Isso contradiz a regra "CONFERIDO = trava" estabelecida no plano.

**Deveria**: Adicionar check `if fatura.status_conferencia == 'CONFERIDO': block`.

### A-8: `excluir_cte_complementar` nao checa CustoEntrega ativos

**Linha**: 562-569. Cascade-deleta custos (L577-582) sem verificar status.

**Deveria**: Bloquear se ha CustoEntrega com `status != 'CANCELADO'` — forcar o admin a cancelar explicitamente cada um.

### A-9: `excluir_custo_entrega` — nao checa vinculo com CTe Complementar

**Linha**: 620-671. Checa apenas `status=PAGO`.

**Problema**: CustoEntrega vinculado a CTe Complementar ja EMITIDO pode ser deletado, deixando o CTe Complementar "pendurado" sem o custo que motivou.

**Deveria**: Se `custo.cte_complementar_id IS NOT NULL`, bloquear ou alertar.

### A-10: `excluir_despesa` nao checa tipo COMISSAO — Gap W13 do plano

**Linha**: 677-721. Checa apenas `status=PAGO`.

**O que acontece**: Admin pode deletar despesa `tipo_despesa='COMISSAO'` mesmo com CarviaComissaoFechamento PENDENTE apontando para ela.

**Deveria**: 
```python
from app.carvia.models import CarviaComissaoFechamento
fechamento = CarviaComissaoFechamento.query.filter_by(despesa_id=despesa_id).first()
if fechamento and fechamento.status != 'CANCELADO':
    return bloquear(f"Despesa vinculada a Fechamento #{fechamento.numero_fechamento}")
```

### A-11: `editar_entidade` (FIELD_EDIT) — bypass COMPLETO — CRITICO

**Linha**: 854-943. ZERO validacao de regras de negocio. Permite setar qualquer campo em qualquer entidade.

**O que acontece**: Admin pode:
- Alterar `operacao.cte_valor` em operacao FATURADA (bypass W1)
- Alterar `operacao.status` direto (violando state machine)
- Alterar `fatura.valor_total` em fatura CONFERIDA (violando imutabilidade)
- Alterar `nf.status` em NF vinculada (bypass W2)
- Alterar `subcontrato.valor_acertado` em FT CONFERIDA (bypass W4)

**Deveria**: Aplicar mesmos guards das rotas normais. Por campo:
- `CarviaOperacao.cte_valor` → chamar `operacao.pode_editar_valor()`
- `CarviaOperacao.status` → validar transicao (state machine)
- `CarviaFaturaCliente.valor_total` → chamar `fatura.pode_editar()`
- `CarviaSubcontrato.valor_acertado` → chamar `ft.pode_editar_sub_valor()` via `sub.fatura_transportadora`
- Outros campos sensiveis: lista explicita de campos protegidos por entidade

**Implementacao recomendada**: Mapa `CAMPOS_PROTEGIDOS = {model_class: {campo: guard_method}}`. Editar campo protegido exige `force=True` e chamada de metodo de validacao.

### A-12: `relink_operacao_nfs` — sem guards

**Linha**: 949. Vincula/desvincula NFs de uma operacao sem verificar:
- Se operacao esta FATURADA
- Se NF esta em outra operacao ja faturada
- Se NF que sera desvinculada esta em item de fatura

**Deveria**: Chamar `nf.pode_desvincular_de_operacao(op_id)` do Sprint 0 para cada desvinculacao.

---

## Resumo Executivo dos Gaps Admin

| Severidade | Qtd | Gaps |
|------------|-----|------|
| CRITICO | 3 | A-1 (excluir_nf sem guard), A-4 (W8), A-11 (FIELD_EDIT bypass total) |
| ALTO | 5 | A-3, A-5, A-7, A-8, A-10 (W13), A-12 |
| MEDIO | 3 | A-2, A-6, A-9 |

---

## Plano de Correcao

### Sprint 1 (integrado com os fixes de rotas)

Cada fix de rota deve ser acompanhado do fix equivalente no admin:

| Fix em Rota | Fix Admin Equivalente |
|-------------|----------------------|
| W1: `editar_cte_valor` usa `pode_editar_valor()` | A-11: FIELD_EDIT valida campos protegidos |
| W6: `cancelar_operacao` usa `pode_cancelar()` | A-3: `excluir_operacao` chama `pode_cancelar()` tambem |
| W8: (novo) guard em excluir_operacao | A-4: check CarviaFrete no admin |
| W13: despesa COMISSAO | A-10: check fechamento no admin |
| W2: NF guards | A-1, A-2: adicionar mesmos guards em `excluir_nf` |

### Sprint 2

- A-5: `excluir_subcontrato` checa `frete_id` e `CarviaFrete.subcontrato_id`
- A-7: `excluir_fatura_transportadora` checa `status_conferencia`
- A-12: `relink_operacao_nfs` usa `pode_desvincular_de_operacao()`

### Sprint 3

- A-11 completo: mapa `CAMPOS_PROTEGIDOS` implementado com todos os guards + flag `force` com audit reinforcado

---

## Principio Arquitetural

**Admin NAO e atalho para bypass**. E caminho para **override explicito com audit reinforcado**:
1. Mesmas validacoes das rotas normais
2. Override exige flag explicita `force=True` + motivo detalhado
3. Override cria audit com nivel `FORCED_OVERRIDE` (nao apenas `HARD_DELETE`)
4. Todos os camps protegidos listados explicitamente
5. Audit trail detalha exatamente quais guards foram bypassed

Isso preserva o admin como ferramenta de emergencia sem transforma-lo em back-door.
