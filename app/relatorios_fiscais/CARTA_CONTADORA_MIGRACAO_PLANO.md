# SPED ECD 2024 — Migração de Plano de Contas (jul/2024)

**Para**: Contadora (Tamiris Salles)
**De**: NACOM Goya
**Assunto**: Esclarecimento sobre I157 + pedido do de-para Odoo → plano antigo de contas

---

## Resumo do problema

Em jul/2024 a NACOM migrou seu sistema contábil para o **Odoo CIEL IT**. A ECD 1S 2024 (jan-jun) foi gerada no sistema anterior — plano com codes formato `1.1.1.01.01`. A nossa ECD 2S 2024 (jul-dez) está sendo gerada direto do Odoo — plano com codes formato `1110100002`.

Os saldos foram migrados corretamente (saldo final 30/jun = saldo inicial 1/jul, confere conta a conta), mas como os **codes das contas são diferentes**, ao importar nossa ECD 2S no PVA e tentar recuperar a 1S são reportados 262 erros — todos do tipo "conta não consta no C155" ou "saldo não recuperado".

## Esclarecimento sobre o I157 — confirmação

Conforme você comentou, no SPED 2S que você gerou (arquivo `SpedContabil-...17_20240701_20241231_G.txt`) aparece o saldo inicial do CAIXA:

```
|I155|1.1.1.01.01||4037,31|D|0|0|4037,31|D|
```

**Esse 4037,31 é o campo VL_SLD_INI do próprio I155 (campo 4)** — não é o registro I157 do Manual ECD. Verifiquei o arquivo com `grep -c "^|I157|"` e o resultado foi **0 ocorrências** — o SPED 2S não emite nenhum I157.

Isso não é problema **no seu SPED** porque você manteve o plano antigo de contas **idêntico** entre 1S e 2S (584 contas, codes `1.1.1.x.y` em ambos os semestres). Como o plano não mudou do lado do SPED gerado, a recuperação do C155 (vindo da 1S) bate código por código com o I155 (do 2S), e o PVA aceita sem precisar de I157.

(Observação técnica: o campo 22 do 0000 do seu SPED 2S está marcado `IND_MUDANC_PC=1` (com mudança de plano), o que pelo Manual exigiria emissão obrigatória de I157. O PVA aparentemente tolera essa situação porque o mapping é trivial 1:1.)

## Por que o nosso SPED Odoo precisa de I157

No nosso lado o plano de contas mudou de verdade: codes `1.1.1.x.y` → codes `1110xxxxxx`. Para a recuperação da ECD 1S funcionar na nossa ECD 2S, precisamos emitir explicitamente o registro I157 (sub-registro do I155) apontando da conta nova para a equivalente do plano antigo. Exemplo concreto:

```
|I155|1110100002||4037,31|D|0|0|4037,31|D|     ← nosso CAIXA (Odoo) com saldo inicial
  |I157|1.1.1.01.01||4037,31|D|                ← novo: aponta para CAIXA do plano antigo
```

Com isso o PVA vai reconhecer que o saldo do CAIXA `1110100002` no nosso plano corresponde ao CAIXA `1.1.1.01.01` do plano antigo (recuperado do C155), e os 262 erros desaparecem.

**Referência**: Manual de Orientação ECD Leiaute 9 (Anexo ADE Cofis 01/2026), páginas 140-141 (registro I157) e página 86 (registro 0000, campo 22 IND_MUDANC_PC).

## O que precisamos de você

Para emitir o I157 corretamente em cada uma das ~584 contas, precisamos do **de-para Odoo → plano antigo de contas**.

Você deve ter esse mapeamento em algum lugar, porque é como os saldos do Odoo são "traduzidos" para o plano antigo mensalmente quando você gera o SPED oficial. As formas possíveis são:

### Forma 1 — Planilha (mais provável)
Uma planilha Excel/CSV usada para conferir/preencher os saldos, com 2 colunas:

| code_odoo | code_plano_antigo |
|-----------|-------------------|
| 1110100002 | 1.1.1.01.01 |
| 1110100003 | 1.1.1.01.02 |
| 1110200001 | 1.1.1.02.01 |
| 1110200006 | 1.1.1.02.06 |
| ... | ... |

### Forma 2 — Campo customizado no Odoo
Pode existir no Odoo um campo customizado em cada conta do plano (ex: "Código contábil anterior", "Código histórico", "Referência externa") que armazena o code do plano antigo. Se for o caso, basta confirmar o nome do campo e extraímos direto do banco do Odoo — não precisa enviar planilha.

### Forma 3 — Tabela interna no sistema de geração do SPED
Se o de-para vive só dentro do sistema usado para gerar o SPED (não em Excel nem no Odoo), você pode exportar uma listagem das contas com os 2 codes lado a lado.

## Próximos passos

1. **Você** envia o de-para (planilha, indicação do campo Odoo, ou export do sistema de geração)
2. **Nós** ajustamos o gerador SPED Nacom para:
   - Marcar `IND_MUDANC_PC=1` no registro 0000
   - Emitir um I157 para cada conta no primeiro mês (jul/2024) com o code equivalente do plano antigo
3. **Re-validamos** nosso SPED 2S no PVA importando junto a ECD 1S — esperamos os 262 erros zerarem
4. **Resultado**: passamos a ter um SPED 2S Odoo "drop-in" compatível com a ECD 1S, validado pelo PVA

## Observação sobre escopo

A ECD 2S 2024 oficial que você gera (a que vai para a RFB) **continua válida e prevalece**. O nosso SPED Odoo é uma alternativa interna que precisa estar consistente com a oficial para fins de validação cruzada — não para substituir a entrega.
