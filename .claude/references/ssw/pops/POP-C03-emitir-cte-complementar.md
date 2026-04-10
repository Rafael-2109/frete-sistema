# POP-C03 — Emitir CT-e Complementar

> **Versao**: 2.0
> **Criado em**: 2026-02-16
> **Atualizado em**: 2026-04-09 (automacao Playwright opcao 222 implantada)
> **Status CarVia**: ATIVO (via automacao Playwright — opcao 222)
> **Opcoes SSW**: 222 (emissao), 007 (envio SEFAZ), 101 (consulta XML/DACTE)
> **Executor atual**: Rafael
> **Executor futuro**: Rafael / Jaqueline

---

## Objetivo

Emitir CT-e complementar para ajustar valores, impostos ou dados de um CT-e ja autorizado. O CT-e complementar e um documento fiscal que "completa" um CT-e original, sendo usado quando o CT-e original foi emitido com valores menores que os devidos.

---

## Quando Executar (Trigger)

- CT-e emitido com valor de frete menor que o devido
- Complemento de ICMS (base de calculo ou aliquota errada)
- Ajuste de peso ou cubagem (gerando diferenca de frete)
- Cobranca de custos extras acordados posteriormente (TDE, diaria, pernoite)
- Cliente solicitou complemento por divergencia contratual

---

## Frequencia

Por demanda — processo excepcional, mas importante conhecer.

---

## Pre-requisitos

- CT-e original JA autorizado pelo SEFAZ
- CTRC do CT-e pai (formato `FILIAL-NUMERO-DV`, ex: `CAR-113-9`)
- CT-e pai consultavel na opcao 101 (necessario para `--valor-base` funcionar com auto-calc)
- Motivo do complemento claramente definido (C/D/V/E/R)
- Valores corretos calculados (valor bruto OU valor final pos-grossing up)
- Cliente ciente do complemento (se aplicavel)

---

## Passo-a-Passo

### ETAPA 1 — Identificar o CT-e Original

1. Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) (consulta de CTRC)
2. Pesquisar pelo CT-e original (por numero, chave ou NF-e)
3. Anotar:
   - [ ] Numero do CT-e original (serie + numero)
   - [ ] Chave de acesso (44 digitos)
   - [ ] Valor original do frete
   - [ ] Valor correto (que deveria ter sido cobrado)
   - [ ] Diferenca a complementar

---

### ETAPA 2 — Calcular Valores do Complemento

4. Definir tipo de complemento:

| Tipo | Quando usar | Exemplo |
|------|-------------|---------|
| **Complemento de Valor de Frete** | Frete calculado errado, tabela desatualizada | Frete era R$ 500, cobrado R$ 400 → complementar R$ 100 |
| **Complemento de ICMS** | Base de calculo ou aliquota errada | ICMS era 12%, cobrado 7% → complementar diferenca |
| **Complemento de Peso** | Peso real maior que declarado | Peso declarado 500kg, real 800kg → recalcular frete |
| **Complemento de Outros Valores** | TDE, diaria, pernoite nao incluidos | TDE de R$ 150 nao cobrada → complementar R$ 150 |

5. Calcular valores:
   - Valor do complemento = Valor correto - Valor original
   - ICMS do complemento (se aplicavel)
   - Componentes do frete (frete peso, GRIS, pedagio, etc.)

---

### ETAPA 3 — Emitir CT-e Complementar (Opcao 222)

> **CORRECAO 2026-04-09**: A opcao real para emissao de CT-e Complementar e a **222**
> (nao a 007 como inicialmente documentado). A opcao 007 e usada APENAS para envio ao SEFAZ
> apos a gravacao na 222.

6. Acessar **opcao 222** (CT-e Complementar) — **NAO e dentro da 007**
7. Preencher tela inicial (page1):
   - **Motivo**: `C` (correcao), `D` (diferenca), `V` (valor), `E` (estorno) ou `R` (retificacao)
   - **Filial do CTe pai**: ex: `CAR`
   - **CTRC concatenado**: numero+dv SEM hifen, ex: `1139` (para CTRC `113-9`)
8. Click `►` → abre popup secundario (page2)
9. Preencher tela principal (page2):
   - **Valor outros (`vlr_outros`)**: valor final pos-grossing up, formato BR (`227,90`)
   - **Tipo de documento (`tp_doc`)**: `C`
   - **Unidade emissora (`unid_emit`)**: `D` ou `O` — **respeitar se SSW forcar readonly**
     (SSW pode decidir filial do complementar baseado na carga; nao tentar forcar)
10. Click `►` → loop de "Continuar" (multiplos avisos CFOP/ICMS/GNRE — clicar todos)
11. Capturar mensagem dialog **"Novo CTRC: FILIAL000NUMERO-DV"** (ex: `CAR002037-1`)
12. Trocar para a filial do complementar (se diferente da filial do pai)
13. Acessar **opcao 007** → click "Enviar a SEFAZ"
14. Acessar **opcao 101** → consultar CTRC complementar → baixar XML + DACTE
   - [CONFIRMAR] A funcao pode estar em menu lateral ou botao na tela inicial da 007

8. Informar dados do CT-e original:

| Campo | Valor |
|-------|-------|
| **CT-e original** | Serie + numero do CT-e a complementar |
| **Chave de acesso** | 44 digitos do CT-e original |
| **Tipo de complemento** | Valor / ICMS / Outros |

9. Informar valores do complemento:

| Campo | Valor | Observacao |
|-------|-------|------------|
| **Valor do complemento** | Diferenca entre correto e original | Ex: R$ 100,00 |
| **Frete Peso** | Diferenca no frete peso | Se aplicavel |
| **GRIS** | Diferenca no GRIS | Se aplicavel |
| **Pedagio** | Diferenca no pedagio | Se aplicavel |
| **TDE/TDC/TAR** | Taxas adicionais | Se aplicavel |
| **ICMS do complemento** | Calculado automaticamente | Ou informar manualmente |
| **Observacao** | Motivo do complemento | Texto livre, explicar ao cliente |

10. Gravar pre-CTRC complementar
11. Enviar ao SEFAZ (botao "Enviar CT-es ao SEFAZ")
12. Aguardar autorizacao:
    - **Autorizado**: CT-e complementar recebe numero proprio e protocolo
    - **Rejeitado**: Verificar motivo (comum: CT-e original cancelado, valores zerados)

---

### ETAPA 4 — Verificar Vinculacao

13. Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) e pesquisar pelo CT-e complementar
14. Verificar:
    - [ ] CT-e complementar autorizado
    - [ ] Campo "CT-e referenciado" aponta para o CT-e original
    - [ ] Valor total = valor do CT-e original + valor do complemento

15. Acessar [opcao **101**](../comercial/101-resultado-ctrc.md) e pesquisar pelo CT-e original
16. Verificar:
    - [ ] CT-e original mostra vinculo com o complementar
    - [ ] Status permanece "Autorizado" (nao e cancelado)

---

### ETAPA 5 — Faturamento do Complemento

17. O CT-e complementar entra automaticamente no faturamento (opcao [435](../financeiro/435-pre-faturamento.md)/[437](../financeiro/437-faturamento-manual.md))
18. Opcoes de faturamento:
    - **Fatura separada**: Emitir fatura apenas com o CT-e complementar
    - **Fatura conjunta**: Incluir complemento na proxima fatura periodica do cliente
    - **Boleto avulso**: Se cliente ja pagou o CT-e original

19. Enviar fatura ao cliente com EXPLICACAO clara do motivo do complemento

---

## Automacao CarVia (CarviaEmissaoCteComplementar + Playwright)

> **Implantado em 2026-04-09** — automacao end-to-end via Playwright (commits `1b2e1ac0`, `06f27d0d`, `6ca7b942`).

### Script Playwright (uso direto)

```bash
# Com auto-calculo de valor (consulta 101 do pai → grossing up):
python .claude/skills/operando-ssw/scripts/emitir_cte_complementar_222.py \
  --ctrc-pai CAR-113-9 \
  --motivo D \
  --valor-base 200.00 \
  --enviar-sefaz

# Com valor final ja calculado:
python .claude/skills/operando-ssw/scripts/emitir_cte_complementar_222.py \
  --ctrc-pai CAR-113-9 \
  --motivo D \
  --valor-outros 227.90 \
  --enviar-sefaz
```

Detalhes: [`.claude/skills/operando-ssw/SCRIPTS.md` secao 5](../../../skills/operando-ssw/SCRIPTS.md) e [`references/CTE.md`](../../../skills/operando-ssw/references/CTE.md).

### Integracao CarVia (via worker RQ)

| Componente | Caminho |
|------------|---------|
| **Model** | `app/carvia/models/cte_custos.py` → `CarviaEmissaoCteComplementar` (tracking lifecycle) |
| **Worker** | `app/carvia/workers/ssw_cte_complementar_jobs.py` → `emitir_cte_complementar_job(id)` |
| **Persistencia** | `app/carvia/services/cte_complementar_persistencia.py` |
| **Route retry** | `POST /carvia/api/custos-entrega/emissao-comp/<id>/retry` |
| **Download S3** | `GET /carvia/ctes-complementares/<id>/download-xml` e `download-dacte` |

### Auto-calculo de valor (grossing up)

`--valor-base` aciona pre-fase no script:

1. Delega para `consultar_ctrc_101.py` (consulta 101 do pai)
2. Extrai `ICMS/ISS (R$)` e `Valor frete (R$)` do body via regex
3. Calcula `aliquota = (valor_icms / valor_frete) * 100`
4. Aplica grossing up: `valor_outros = valor_base / 0.9075 / (1 - aliquota / 100)`
5. Constante: `PISCOFINS_DIVISOR = 0.9075` (mesma formula de `app/carvia/routes/custo_entrega_routes.py`)

### Retry de emissao travada em ERRO

```
POST /carvia/api/custos-entrega/emissao-comp/<id>/retry
```

Valida `emissao.status == ERRO` e `cte_comp.status == RASCUNHO`, reseta `status=PENDENTE` e re-enfileira o job RQ.

---

## Contexto CarVia

### Hoje (2026-04-09)
Automacao Playwright implantada via opcao 222. Fluxo end-to-end funcionando: extracao
automatica de ICMS via 101 → grossing up → emissao → SEFAZ → backfill XML/DACTE no S3.

### Antes da automacao (pre-2026-04-09)
Rafael nunca havia emitido CT-e complementar. Se houvesse erro de valor, ele:
- Cancelava o CT-e original (se dentro do prazo de 7 dias)
- Reemitia com valor correto
- Ou "deixava pra la" se diferenca fosse pequena

### Futuro
- Treinar Jaqueline no fluxo via UI (`/carvia/custos-entrega/<id>` → botao "Emitir CTe Complementar")
- Monitorar emissoes em ERRO via dashboard CarVia (rota retry disponivel)
- Avaliar abertura de fluxo manual via UI para casos edge nao cobertos pelo auto-calc

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| SEFAZ rejeita: CT-e original cancelado | CT-e original foi cancelado antes do complemento | Nao e possivel complementar CT-e cancelado. Emitir novo CT-e normal |
| SEFAZ rejeita: valor zerado | Complemento com valor R$ 0,00 | Verificar se valores foram informados corretamente |
| SEFAZ rejeita: chave invalida | Chave do CT-e original errada | Conferir chave de acesso (44 digitos) na [opcao 101](../comercial/101-resultado-ctrc.md) |
| Cliente reclama do complemento | Falta de comunicacao previa | Avisar cliente ANTES de emitir complemento |
| Complemento nao aparece no faturamento | CT-e complementar nao vinculado ao cliente | Verificar [opcao 435](../financeiro/435-pre-faturamento.md) — deve aparecer na lista |
| Valor do complemento divergente | Calculo manual errado | Usar simulacao da [opcao 004](../operacional/004-emissao-ctrcs.md) para calcular diferenca |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| CT-e complementar autorizado | [Opcao 007](../operacional/007-emissao-cte-complementar.md) → fila "Autorizados" → CT-e complementar presente |
| Vinculacao correta | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e complementar → campo "CT-e referenciado" = CT-e original |
| CT-e original nao cancelado | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e original → status = "Autorizado" |
| Valor total correto | [Opcao 101](../comercial/101-resultado-ctrc.md) → CT-e original + complementar = valor correto |
| Faturamento disponivel | [Opcao 435](../financeiro/435-pre-faturamento.md) → CT-e complementar na lista |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-C01 | Emitir CTe fracionado — processo base |
| POP-C02 | Emitir CTe carga direta — processo base |
| POP-C04 | Custos extras — alternativa ao complemento para TDE/diaria |
| POP-C06 | Cancelar CTe — alternativa quando prazo permite |
| POP-E02 | Faturar — proximo passo (faturar o complemento) |

---

## Historico

| Data | Versao | Alteracao |
|------|--------|-----------|
| 2026-02-16 | 1.0 | Criacao inicial (Onda 5) |
| 2026-04-09 | 2.0 | Correcao: opcao real e 222 (nao 007). Status: NAO IMPLANTADO → ATIVO. Adicionada secao "Automacao CarVia" com script Playwright + worker RQ + auto-calc de ICMS via 101 do pai. Commits: `1b2e1ac0`, `06f27d0d`, `6ca7b942`. |
