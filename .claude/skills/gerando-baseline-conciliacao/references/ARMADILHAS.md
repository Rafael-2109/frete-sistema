# Armadilhas documentadas

Erros ja cometidos pelo agente em sessoes anteriores do Marcus (user_id=18). Estas armadilhas sao REAIS — cada uma exigiu correcao interativa pelo usuario.

---

## 1. Usar tabela local `extrato_item` como fonte

**Sintoma**: contagem 2-3x maior que a real no Odoo.

**Exemplo real** (16/04/2026): tabela local reportou **18.158 linhas**, Odoo real era **6.985 linhas**. Diferenca de 11.173 linhas — todas ja conciliadas no Odoo mas sincronizacao local atrasada.

**Causa**: `extrato_item` acumula linhas ja conciliadas no Odoo por defasagem do job de sync.

**Correcao**: SEMPRE consultar Odoo diretamente — `account.bank.statement.line` com `is_reconciled=False`. Tabela local pode ser usada para lookups de metadados, NUNCA para contagem ou baseline.

**Referencia**: memoria empresa id=532 (heuristica nivel 5).

---

## 2. Nomear aba "Baseline" em vez de "Pendentes Mes x Journal"

**Sintoma**: arquivo entregue com `wb.sheetnames[0] == "Baseline"` em vez de `"Pendentes Mes x Journal"`.

**Causa**: agente interpretou "baseline" como nome literal da aba, ao inves de descricao do relatorio.

**Correcao**: o arquivo e o **baseline**. As abas tem nomes especificos, ver FORMATO_ABAS.md. Nomes corretos:
1. "Pendentes Mes x Journal"
2. "Pendentes"
3. "Conciliacoes Dia Anterior"
4. "Resumo"

---

## 3. Valor Debitos positivo (com abs)

**Sintoma**: coluna "Valor Debitos" mostra valores positivos (ex: 125.000,00) em vez de negativos (-125.000,00).

**Causa**: agente aplicou `ABS()` ou inverteu sinal pensando que era erro.

**Correcao**: NUNCA aplicar abs. Debitos sao negativos por natureza (saida de caixa). Formato Excel: `#.##0,00;[Red]-#.##0,00`.

---

## 4. Omitir secao "Evolucao Baseline" no rodape

**Sintoma**: aba 1 termina na linha TOTAL, sem historico de baselines anteriores.

**Causa**: agente esqueceu ou considerou redundante.

**Correcao**: apos linha TOTAL, inserir:
```
(linha em branco)
Evolucao Baseline
09/Abr/2026 | 8.684
16/Abr/2026 | 6.985 | delta=-1.699
<data_atual> | <total> | delta=<total - 6.985>
```

---

## 5. Exibir `SYNC_ODOO_WRITE_DATE` como nome de usuario

**Sintoma**: aba 3 (Conciliacoes D-1) mostra `SYNC_ODOO_WRITE_DATE` ou `SYNC_BATCH_2026_04_15` no lugar do nome real.

**Causa**: uso de identificador interno de sync ao inves de `write_uid`.

**Correcao**: resolver nome real via `SELECT name FROM res_users WHERE id = write_uid`. Nomes esperados: Martha, Allanda, Vanderleia, Marcus. Se `write_uid=False` OU nome comeca com `SYNC_*`, NAO EXIBIR.

**Referencia**: memoria empresa id=529 (armadilha nivel 4).

---

## 6. Omitir a aba "Conciliacoes Dia Anterior"

**Sintoma**: arquivo entregue com apenas 3 abas em vez de 4. Aba D-1 nao existe.

**Causa**: agente considerou opcional ou pulou por faltar dados.

**Correcao**: a aba e OBRIGATORIA. Se nao houver conciliacoes em D-1, gerar com cabecalho e linha "Nenhuma conciliacao registrada" — NUNCA omitir a aba.

---

## 7. Calcular PGTOS/RECEB via `payment_id IS NOT NULL`

**Sintoma**: coluna PGTOS zerada ou valores muito baixos.

**Causa**: agente usou `COUNT(*) FILTER (WHERE payment_id IS NOT NULL)` achando que payment_id indica pagamento. Errado: pendentes por definicao NAO tem payment_id.

**Correcao**: usar sinal do `amount`:
- `PGTOS = COUNT(*) FILTER (WHERE amount < 0)` — debitos/pagamentos.
- `RECEB = COUNT(*) FILTER (WHERE amount > 0)` — creditos/recebimentos.

NUNCA usar `payment_id IS NOT NULL`, `sum(amount)`, ou status de pagamento.

**Referencia**: memoria empresa id=531 (armadilha nivel 4).

---

## 8. Consultar apenas 1 fonte para aba D-1

**Sintoma**: aba 3 reporta 89 conciliacoes quando o total correto era 134.

**Causa**: agente consultou apenas `extrato_item` (maior fonte) e achou que era completa.

**Correcao**: aba 3 exige UNIAO de 3 fontes obrigatorias:
1. Odoo `account.bank.statement.line` com `write_date::date = CURRENT_DATE - 1` e `is_reconciled=True`
2. Local `lancamento_comprovante` com `data_conciliacao = CURRENT_DATE - 1`
3. Local `carvia_conciliacoes` com `data = CURRENT_DATE - 1`

Omitir qualquer fonte produz contagem, valores e usuarios incorretos SEM sinalizacao de erro.

**Referencia**: memoria empresa id=529 (armadilha nivel 4).

---

## Matriz de prevencao

| Armadilha | Camada de defesa |
|-----------|------------------|
| 1. Tabela local | preferences.xml `<fonte>` + heuristica 532 |
| 2. Nome aba errada | preferences.xml `<aba nome="...">` + checkpoint 4 |
| 3. Debitos positivo | FORMATO_ABAS.md + SQL_ODOO.md (preserva sinal) |
| 4. Sem Evolucao Baseline | FORMATO_ABAS.md rodape obrigatorio |
| 5. SYNC_* | SQL_ODOO.md Query 3 (resolve write_uid) + checkpoint 3 |
| 6. Faltando aba D-1 | SKILL.md fluxo + checkpoint 4 |
| 7. payment_id IS NOT NULL | heuristica 531 + SQL_ODOO.md Query 1 |
| 8. Apenas 1 fonte D-1 | SQL_ODOO.md Query 3 (uniao obrigatoria) + heuristica 529 |
