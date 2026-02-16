# POP-A06 — Cadastrar Custos/Comissoes (Subcontratacao)

> **Categoria**: A — Implantacao e Cadastros
> **Prioridade**: P1 (Alta — define custo de subcontratacao, base para resultado do CTRC)
> **Status anterior**: JA FAZ
> **Criado em**: 2026-02-16
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Cadastrar a tabela de custos de subcontratacao na [opcao 408](../comercial/408-comissao-unidades.md) (Comissao de Unidades) do SSW da CarVia, refletindo os precos que a CarVia paga a cada transportadora parceira. Os valores da 408 sao copia exata do Sistema Fretes (app Nacom), que e a fonte de verdade para precos de parceiros.

A diferenca entre a tabela 420 (preco de venda ao cliente) e a tabela 408 (custo do parceiro) constitui a margem da CarVia. Sem a 408 configurada, o SSW nao consegue calcular resultado do CTRC ([opcao 101](../comercial/101-resultado-ctrc.md)), comissao de unidades ([opcao 056](../relatorios/056-informacoes-gerenciais.md)) e nem creditar a CCF do fornecedor corretamente.

---

## Trigger

- Apos cadastrar fornecedor (POP-A05) e definir condicoes comerciais com parceiro
- Nova tabela de precos negociada com transportadora parceira
- Reajuste de precos de parceiro existente (nova vigencia)
- Processo composto POP-A10 (Implantar Nova Rota) aciona este POP como etapa 6

---

## Frequencia

Por demanda — a cada novo parceiro ou reajuste de tabela. Estimativa: 10-20 minutos por tabela completa.

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Unidade cadastrada | [401](../cadastros/401-cadastro-unidades.md) | Sigla IATA criada (tipo T para parceiros) |
| Fornecedor cadastrado | [478](../financeiro/478-cadastro-fornecedores.md) | CNPJ, Ativo=S, **CCF ativada=S** |
| Transportadora cadastrada | [485](../financeiro/485-cadastro-transportadoras.md) | CNPJ com sigla unica e status ativo |
| Tabela de precos do parceiro | Sistema Fretes | Faixas de peso, despacho, adicionais (fonte de verdade) |
| Rota cadastrada (recomendado) | [403](../cadastros/403-rotas.md) | Rota CAR → [SIGLA] para tabelas especificas por rota |

> **ORDEM OBRIGATORIA**: 401 (unidade) → 478 (fornecedor com CCF) → 485 (transportadora) → **408** (custos). Pular qualquer etapa causa erro na 408.

> **PRE-REQUISITO CRITICO**: O fornecedor DEVE ter CCF ativada=S na 478 E estar cadastrado como transportadora na 485. Sem ambos, a [opcao 408](../comercial/408-comissao-unidades.md) rejeita o CNPJ.

---

## Passo-a-Passo

### ETAPA 1 — Verificar Pre-requisitos

1. Confirmar que a **unidade** existe na [opcao **401**](../cadastros/401-cadastro-unidades.md):
   - Pesquisar pela sigla (ex: CGR)
   - Verificar tipo = T (Terceiro)

2. Confirmar que o **fornecedor** existe na [opcao **478**](../financeiro/478-cadastro-fornecedores.md):
   - Pesquisar por CNPJ do parceiro
   - Verificar **CCF ativada = S**
   - Verificar **Ativo = S**

3. Confirmar que a **transportadora** existe na [opcao **485**](../financeiro/485-cadastro-transportadoras.md):
   - Pesquisar por CNPJ do parceiro
   - Verificar sigla e dados cadastrais

> **SE ALGUM PRE-REQUISITO FALTAR**: Executar POP-A02 (unidade), POP-A05 (fornecedor/transportadora) antes de prosseguir.

---

### ETAPA 2 — Acessar Opcao 408 e Selecionar Unidade

4. Acessar [opcao **408**](../comercial/408-comissao-unidades.md) (Comissao de Unidades)
5. Na tela inicial, selecionar a **unidade** para a qual sera cadastrada a comissao:

| Campo | Valor | Exemplo |
|-------|-------|---------|
| **Unidade** | Sigla da unidade parceira | CGR |

6. O SSW apresenta as opcoes de comissao:
   - **Comissao geral** — tabela padrao da unidade (usar esta)
   - **Tabelas especificas** — por Cliente, Cidade, Rota, Tipo Mercadoria, CIF/FOB, Empresa
   - **Comissao de transbordo** — para unidades intermediarias

> **PARA CARVIA**: Iniciar sempre pela **Comissao Geral**. Tabelas especificas sao usadas apenas quando um cliente/rota tem custo diferenciado.

---

### ETAPA 3 — Criar Comissao Geral como Expedidora

7. Clicar em **Comissao Geral**
8. Selecionar **"Como Expedidora"** (CarVia envia carga para o parceiro entregar)
9. Preencher os campos de cabecalho:

| Campo | Obrigatorio | Valor | Observacao |
|-------|-------------|-------|------------|
| **Subcontratado** | Sim | CNPJ da transportadora parceira | Digitado ou selecionado |
| **Data inicial** | Sim | Data de inicio da vigencia | Data de hoje ou data negociada |
| **Data final** | Nao | Data de fim da vigencia | Deixar vazio = indeterminada |
| **Tipo Frete** | Sim | **Ambas** | CarVia atende CIF e FOB — usar Ambas |

> **DATA FINAL VAZIA**: Na CarVia, deixar sem data final. Quando houver reajuste, criar nova comissao com nova data inicial — a anterior sera substituida automaticamente.

---

### ETAPA 4 — Configurar Parametros de Custo

10. Preencher os **11 itens** de custo conforme tabela do parceiro no Sistema Fretes:

#### Item 1 — Sobre Frete (% sobre frete do CTRC) — raramente usado pela CarVia

Preencher % Polo, % Regiao, % Interior somente se parceiro cobra percentual sobre frete. A maioria dos parceiros CarVia cobra por faixa de peso (item 3).

#### Item 3 — Sobre Peso (modelo principal CarVia)

11. Preencher os campos fixos:

| Campo | Valor | Exemplo |
|-------|-------|---------|
| **Despacho** | R$ fixo por CTRC | R$ 45,00 |
| **Cubagem** | Kg/m3 para calculo peso cubado | 300 |

12. Preencher a **tabela por faixas de peso** (copiar do Sistema Fretes):

| Faixa (ate Kg) | Valor R$ ou R$/Kg | Observacao |
|----------------|-------------------|------------|
| 50 | R$ 120,00 | Valor fixo (frete minimo) |
| [100](../comercial/100-geracao-emails-clientes.md) | R$ 180,00 | Valor fixo |
| 200 | R$ 2,10/Kg | Valor por Kg |
| [500](../comercial/500-liquidacao-parcial-fatura-arquivo.md) | R$ 1,80/Kg | Valor por Kg |
| 1.000 | R$ 1,50/Kg | Valor por Kg |
| 5.000 | R$ 1,20/Kg | Valor por Kg |
| 10.000 | R$ 0,95/Kg | Valor por Kg |

> **NOTA**: Valores acima sao ILUSTRATIVOS. Os valores reais vem do Sistema Fretes. Cada parceiro tem faixas e valores diferentes. Copiar exatamente conforme fonte de verdade.

> **CUBAGEM**: Se cubagem = 0, SSW usa peso real do CTRC. Se cubagem = 999,99, usa peso calculo do CTRC. Valor padrao CarVia: **300** Kg/m3.

---

#### Item 4 — Comissao Minima

13. Preencher o valor minimo (se parceiro tem frete minimo):

| Campo | Valor | Observacao |
|-------|-------|------------|
| **R$/ton** | Valor minimo por tonelada | Maior entre as 3 opcoes e usado |
| **R$** | Valor minimo fixo por CTRC | Ex: R$ 80,00 |
| **% frete** | % minimo sobre frete | Raramente usado |

> **CALCULO**: O SSW compara os 3 valores e usa o MAIOR. Para CarVia, o mais comum e o R$ fixo (frete minimo do parceiro).

---

#### Item 5 — Adicionar TDC/TRT/TDA/TAR/Pedagio

14. Preencher adicionais conforme acordo com parceiro:

| Campo | Significado | Valor tipico | Observacao |
|-------|-------------|-------------|------------|
| **TDC** | Taxa Dificil Coleta | % ou R$ | Se parceiro cobra coleta especial |
| **TRT** | Taxa Restituicao | % ou R$ | Retorno de documentacao |
| **TDA** | Taxa Dificil Acesso | % ou R$ | Entrega em local de dificil acesso |
| **TAR** | Taxa de Armazenagem | % ou R$ | Armazenagem em transito |
| **Pedagio** | Pedagio rodoviario | R$/frac 100Kg | Valor pedagio por fracao de 100Kg |

> **PEDAGIO**: O pedagio na 408 e SEMPRE adicionado, mesmo que nao exista parcela de pedagio no CTRC. Diferente das outras taxas que so sao adicionadas se existirem no CTRC.

---

#### Item 10 — Conta Corrente Fornecedor (forma de credito)

15. Definir a forma de credito na CCF:

| Forma | Codigo | Descricao | Quando usar |
|-------|--------|-----------|-------------|
| **Mapa** | M | Processamento batch agendado (903) | Parceiro opera unidade no SSW da CarVia — **padrao CarVia** |
| **Fatura** | F | Conferencia manual (607) | Parceiro envia fatura para conferencia |
| **Capa** | C | Recepcao de Capa de Remessa (428) | Parceiro usa seu proprio SSW — tem PRIORIDADE sobre M/F |

> **CARVIA**: Usar **M (Mapa)** como padrao. O processamento batch (903) credita a CCF automaticamente quando os CTRCs sao processados. Se o parceiro nao usa SSW, avaliar **F (Fatura)**.

> **PRIORIDADE**: Se houver Capa (C) configurada, ela tem prioridade sobre Mapa e Fatura. Cuidado ao configurar formas conflitantes.

---

#### Itens 2, 6, 7, 8, 9, 11 (menos frequentes)

16. Preencher somente se aplicavel ao parceiro:

| Item | Campo | Quando usar | CarVia usa? |
|------|-------|-------------|-------------|
| 2 | Sobre valor mercadoria (%) | Ad Valorem ou seguro | Raramente |
| 6 | Sobre CTRCs complementares | Paletizacao, agendamento, estadia, reentrega | Nao |
| 7 | Sobre Carga Fechada | Destino FEC | Nao |
| 8 | Sobre frete aereo | CTRCs aereos | Nao |
| 9 | Aplicar sobre CTRCs liquidados | Restricao a CTRCs pagos | Nao |
| 11 | Subcontrato/Redespacho | Emissao de subcontrato (S/N), ICMS (%) | Avaliar por parceiro |

---

### ETAPA 5 — Gravar e Verificar Comissao

17. Clicar em **Gravar** para salvar a comissao
18. Verificar que a comissao foi criada:
    - Voltar a tela inicial da 408
    - Selecionar a unidade
    - Clicar em "Comissao geral"
    - Confirmar que o CNPJ do subcontratado aparece com os parametros corretos

---

### ETAPA 6 — (Opcional) Comissao Receptora e Tabelas Especificas

> **Comissao Receptora**: Somente se a unidade parceira tambem RECEBE carga da CarVia (fluxo inverso). Mesmos itens 5, 10, 11 da Expedidora. **CarVia HOJE nao configura**.

> **Tabelas Especificas**: Criar somente quando custo diferir por cliente, cidade, rota, tipo mercadoria, CIF/FOB ou empresa. **Prioridade de calculo**: Cliente > Cidade > Rota > Tipo Mercadoria > CIF > FOB > Empresa > Geral. **CarVia HOJE usa apenas Comissao Geral**.

---

### ETAPA 7 — Verificar Integracao com Resultado

19. (Opcional) Emitir um CT-e de teste na opcao **004** para a unidade configurada
20. Consultar o resultado do CTRC na [opcao **101**](../comercial/101-resultado-ctrc.md):
    - Verificar se a coluna "Custo" ([408](../comercial/408-comissao-unidades.md)) mostra valor calculado
    - Verificar se a coluna "Comissao" reflete os parametros cadastrados
    - Confirmar que a margem (Venda - Custo) e positiva

> **SE CUSTO ZERADO**: Verificar se a comissao geral foi gravada, se o CNPJ do subcontratado esta correto e se a CCF esta ativa.

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **Quem cadastra** | Rafael cadastra custos na 408 | Rafael (sem delegacao prevista) |
| **Fonte de verdade** | Sistema Fretes (app Nacom) | Sistema Fretes (possivel automacao de sincronizacao) |
| **Modelo principal** | Item 3 — Sobre peso (faixas) | Manter |
| **Forma CCF** | Provavelmente nao configura (CCF desativada — PEND-07) | **M (Mapa)** — processamento batch |
| **Comissao Receptora** | Nao configura | Avaliar conforme demanda |
| **Tabelas especificas** | Nao usa (apenas Geral) | Criar conforme necessidade |
| **Reajustes** | Manual — Rafael atualiza quando parceiro reajusta | Possivel sincronizacao automatica com Sistema Fretes |
| **Relacao 408 vs 420** | 408 = custo parceiro / 420 = preco venda CarVia | Manter — margem = 420 - 408 |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| "Subcontratado nao encontrado" | Fornecedor nao cadastrado na [opcao 485](../financeiro/485-cadastro-transportadoras.md) (transportadora) | Cadastrar na 485 ANTES de usar na 408 (POP-A05 etapa 6) |
| "Fornecedor sem CCF" | CCF desativada na [opcao 478](../financeiro/478-cadastro-fornecedores.md) | Ativar CCF=S na 478 (POP-A05 etapa 4) |
| Custo zerado no resultado ([101](../comercial/101-resultado-ctrc.md)) | Comissao nao gravada ou parametros vazios | Verificar se comissao geral existe e tem faixas preenchidas |
| Margem negativa (420 < 408) | Preco de venda menor que custo do parceiro | Revisar tabelas — ajustar margem no Sistema Fretes |
| Faixa de peso nao calcula | Peso do CTRC fora das faixas cadastradas | Adicionar faixa que cubra o peso (ex: ate 99.999 Kg) |
| Cubagem errada infla custo | Cubagem (Kg/m3) muito baixa — peso cubado maior que real | Ajustar cubagem para valor correto (padrao CarVia: 300) |
| CCF nao credita apos contratacao | Forma de credito errada ou processamento batch nao executado | Verificar item 10 (M/F/C) e se processamento 903 esta agendado |
| Tabela especifica sobrepoe geral | Existe tabela por rota/cidade que nao deveria existir | Verificar se ha tabelas especificas criadas por engano |
| Comissao duplicada | Mesma unidade/CNPJ com duas comissoes ativas | Verificar datas — encerrar comissao antiga ou ajustar vigencia |
| Pedagio cobrado indevidamente | Pedagio na 408 e SEMPRE adicionado, mesmo sem parcela no CTRC | Zerar campo pedagio se parceiro nao cobra pedagio separado |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| Comissao geral existe | [Opcao 408](../comercial/408-comissao-unidades.md) → selecionar unidade → comissao geral com CNPJ do parceiro |
| CNPJ subcontratado correto | [Opcao 408](../comercial/408-comissao-unidades.md) → comissao geral → campo subcontratado = CNPJ parceiro |
| Datas de vigencia | [Opcao 408](../comercial/408-comissao-unidades.md) → comissao geral → data inicial preenchida |
| Tipo frete = Ambas | [Opcao 408](../comercial/408-comissao-unidades.md) → comissao geral → campo tipo frete = Ambas |
| Faixas de peso preenchidas | [Opcao 408](../comercial/408-comissao-unidades.md) → item 3 → tabela de faixas com valores > 0 |
| Despacho preenchido | [Opcao 408](../comercial/408-comissao-unidades.md) → item 3 → campo despacho R$ > 0 |
| Forma CCF definida | [Opcao 408](../comercial/408-comissao-unidades.md) → item 10 → M, F ou C selecionado |
| Custo calcula no resultado | [Opcao 101](../comercial/101-resultado-ctrc.md) → CTRC da unidade → coluna custo > 0 |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-A10 | Implantar rota completa — este POP e a etapa 6 do A10 |
| POP-A05 | Cadastrar fornecedor (478 + 485) — pre-requisito obrigatorio |
| POP-A02 | Cadastrar unidade parceira ([401](../cadastros/401-cadastro-unidades.md)) — pre-requisito obrigatorio |
| POP-A07 | Cadastrar tabela de preco (420) — proximo passo (preco venda = 408 + margem) |
| POP-F02 | CCF — recebe creditos calculados pela 408 |
| POP-D01 | Contratar veiculo (072) — credita CCF usando parametros da 408 |
| POP-E01 | Pre-faturamento (435) — resultado do CTRC usa 408 para custo |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-16 | Criacao inicial — [opcao 408](../comercial/408-comissao-unidades.md) com 11 itens detalhados e contexto CarVia | Claude (Agente Logistico) |
