# POP-B04 — Analisar Resultado por CTRC

**Categoria**: B — Comercial e Precificação
**Prioridade**: P1 (Alta — "CTRC tem que dar LUCRO")
**Status**: A IMPLANTAR
**Executor Atual**: Rafael
**Executor Futuro**: Rafael/Jessica
**Autor**: Claude (Agente Logístico)
**Data**: 2026-02-16

---

## Objetivo

Analisar a margem comercial (Resultado Comercial) de cada CTRC emitido, verificando se o frete cobrado do cliente cobre todas as despesas (ICMS, PIS/COFINS, seguro, GRIS, transferência, transbordos, recepção, expedição, despesas diversas). Garantir que nenhum CTRC seja emitido com prejuízo ou margem abaixo do mínimo estabelecido.

**Resultado esperado**: 100% dos CTRCs com RC% (Resultado Comercial %) positivo e acima do RC Mínimo configurado na [opção 062](../comercial/062-parametros-frete.md).

---

## Trigger

- **Automático (diário)**: Revisar relatório 031 (Indicadores de Gestão) — CTRCs emitidos ontem com prejuízo
- **Manual (antes de emitir)**: Consultar [opção 101](../comercial/101-resultado-ctrc.md) (Resultado/Consulta CTRC) ao negociar frete com cliente ou parceiro
- **Corretivo**: Cliente questiona preço ou ocorre prejuízo recorrente em rota específica

---

## Frequência

- **Relatório 031**: Diário, primeira coisa do dia (verifica CTRCs de ontem)
- **Análise individual ([opção 101](../comercial/101-resultado-ctrc.md))**: Antes de cada cotação/emissão de CTRC, especialmente em rotas novas ou clientes novos
- **Revisão mensal**: Relatório 449 (Resultado por Cliente) para identificar clientes com margem consistentemente baixa

---

## Pré-requisitos

1. **Cadastros SSW atualizados**:
   - [Opção 408](../comercial/408-comissao-unidades.md) (Componentes Cálculo Frete/Serviços) — custos parceiro (TRANSFER, EXPED, TRANSBOR, RECEPCAO)
   - Opção 420 (Tabela Preços Venda) — fretes vendidos ao cliente
   - [Opção 903](../cadastros/903-parametros-gerais.md)/OUTROS (Alíquotas Tributárias e Seguros) — ICMS, PIS/COFINS, Seguro, GRIS
   - [Opção 062](../comercial/062-parametros-frete.md) (Parâmetros Gerais/Resultado Comercial) — RC Mínimo e Desconto NTC Máximo

2. **Conhecimento**:
   - Estrutura CTRC: Receita (FRETE) - Despesas = RESULTADO
   - Prioridade de fontes: ROTA (403) > transportadora ([903](../cadastros/903-parametros-gerais.md)) para TRANSFER

3. **Acesso SSW**: Perfil com permissão para [opção 101](../comercial/101-resultado-ctrc.md) e 056

---

## Passo-a-Passo

### ETAPA 1 — Acessar relatório de CTRCs com prejuízo (diário)

1. No Menu Principal SSW, acessar **Opção 056** (Informações Gerenciais)
2. Na lista "Gerados hoje", localizar **Relatório 031** — "CTRCs com Prejuízo (ontem)"
3. Clicar no relatório para abrir
4. Verificar colunas:
   - **CTRC**: Número do conhecimento
   - **REMETENTE/DESTINATÁRIO**: Quem embarcou/recebeu
   - **RESULTADO**: Valor do prejuízo (R$ negativo)
   - **RC%**: Percentual de resultado (negativo = prejuízo)
   - **RESM**: Resultado Comercial Mínimo (parâmetro da [opção 062](../comercial/062-parametros-frete.md))

5. **Se houver CTRCs listados**: Anotar números para análise detalhada (próxima etapa)
6. **Se lista estiver vazia**: Operação do dia anterior OK, prosseguir para verificação manual de novos CTRCs

---

### ETAPA 2 — Analisar CTRC específico (opção 101)

1. No Menu Principal SSW, acessar **Opção 101** (Resultado/Consulta CTRC)
2. Informar número do CTRC (da ETAPA 1 ou CTRC que deseja analisar antes de emitir)
3. Clicar em **Resultado** (botão na tela de consulta)
4. Tela exibirá composição do Resultado Comercial:

   ```
   RECEITA:
   - FRETE (Base de Cálculo): R$ X.XXX,XX

   DESPESAS:
   - ICMS: R$ XXX,XX (fonte: 392/TRIBUTAÇÃO)
   - PIS COFINS: R$ XX,XX (fonte: 903/OUTROS)
   - SEGURO: R$ XX,XX (fonte: 903/OUTROS, % sobre valor mercadoria)
   - GRIS: R$ X,XX (fonte: 903/OUTROS, % sobre valor mercadoria)
   - EXPED: R$ XXX,XX (fonte: 408, comissão expedidora)
   - TRANSFER: R$ XXX,XX (fonte: ROTA 403 ou transportadora 903)
   - TRANSBOR: R$ XX,XX (fonte: 408 ou 401)
   - RECEPCAO: R$ XX,XX (fonte: 408)
   - DESP DIV: R$ XX,XX (fonte: 475, despesas específicas CTRC)

   RESULTADO: R$ XXX,XX (FRETE - DESPESAS)
   RC%: XX,X% (RESULTADO / FRETE * 100)
   ```

5. Comparar **RC%** com **RC Mínimo** ([opção 062](../comercial/062-parametros-frete.md)):
   - RC% < 0 → **PREJUÍZO** (jamais aceitar)
   - RC% < RC Mínimo → **MARGEM INSUFICIENTE** (corrigir ou justificar)
   - RC% ≥ RC Mínimo → **OK**

---

### ETAPA 3 — Identificar causa do prejuízo/margem baixa

1. Verificar cada despesa na composição:
   - **TRANSFER muito alto?** Renegociar com parceiro ([opção 408](../comercial/408-comissao-unidades.md)) ou trocar parceiro
   - **ICMS/PIS/COFINS acima do esperado?** Verificar tributação na [opção 903](../cadastros/903-parametros-gerais.md)/OUTROS (alíquotas erradas ou destinação incorreta)
   - **SEGURO/GRIS excessivos?** Verificar % na [opção 903](../cadastros/903-parametros-gerais.md)/OUTROS (padrão: Seguro ~0,3%, GRIS ~0,08%)
   - **FRETE vendido muito baixo?** Cliente negociou desconto acima do aceitável — revisar opção 420

2. Anotar **QUAL despesa** está desbalanceada e **VALOR esperado vs VALOR real**

---

### ETAPA 4 — Corrigir parâmetros no SSW

**Se problema é CUSTO PARCEIRO (TRANSFER, EXPED, TRANSBOR, RECEPCAO)**:
1. Acessar **Opção 408** (Componentes Cálculo Frete/Serviços)
2. Localizar rota/parceiro correspondente
3. Ajustar valores de custo
4. Salvar

**Se problema é TRIBUTAÇÃO (ICMS, PIS/COFINS)**:
1. Acessar **[Opção 903](../cadastros/903-parametros-gerais.md)/OUTROS** (Alíquotas Tributárias)
2. Verificar alíquotas por UF de origem/destino
3. Corrigir se divergente da legislação
4. Salvar

**Se problema é SEGURO/GRIS**:
1. Acessar **[Opção 903](../cadastros/903-parametros-gerais.md)/OUTROS**
2. Verificar % de Seguro (padrão ~0,3%) e GRIS (padrão ~0,08%)
3. Ajustar se fora do mercado
4. Salvar

**Se problema é PREÇO DE VENDA baixo**:
1. Acessar **Opção 420** (Tabela Preços Venda)
2. Localizar cliente/rota correspondente
3. Aumentar frete de venda ou remover desconto excessivo
4. Salvar
5. **Comunicar cliente**: "Frete anterior estava com margem negativa, novo valor é R$ X,XX"

---

### ETAPA 5 — Verificar RC Mínimo e Desconto NTC Máximo (opção 062)

1. Acessar **Opção 062** (Parâmetros Gerais/Resultado Comercial)
2. Verificar campos:
   - **RC Mínimo (%)**: Margem mínima aceitável (ex: 10%)
   - **Desconto NTC Máximo (%)**: Desconto máximo permitido sobre tabela NTC (ex: 30%)
3. **Se nunca configurado**: Definir valores iniciais (sugestão: RC Mínimo 8%, Desconto NTC Máximo 25%)
4. Salvar
5. A partir de agora, relatório 031 comparará RC% de cada CTRC com esses parâmetros

---

### ETAPA 6 — Documentar e prevenir recorrência

1. Criar planilha de acompanhamento (Excel ou Google Sheets):
   - Colunas: Data, CTRC, Cliente, Rota, RC%, Causa Prejuízo, Ação Tomada, Status
2. Registrar cada CTRC com prejuízo ou margem baixa
3. **Se mesma rota/cliente repetir problema**: Considerar:
   - Renegociar contrato com cliente (aumentar frete)
   - Trocar parceiro subcontratado (reduzir TRANSFER)
   - Desativar rota (inviável comercialmente)

4. **Comunicar equipe**:
   - Jessica (comercial): Novos preços mínimos por rota
   - Stephanie (operacional): Parceiros com custo elevado

---

## Contexto CarVia

| Aspecto | Hoje (A IMPLANTAR) | Futuro (PÓS-IMPLANTAÇÃO) |
|---------|--------------------|--------------------|
| **Uso da opção 101** | Rafael NÃO usa sistematicamente (sabe que margem existe mas não verifica CTRC por CTRC) | Rafael consulta 101 ANTES de emitir CTRC em rota nova ou cliente novo; Jessica usa em todas as cotações |
| **Relatório 031** | Nunca acessado | Consultado TODO DIA pela manhã (primeira atividade Rafael/Jessica) |
| **[Opção 062](../comercial/062-parametros-frete.md) (RC Mínimo)** | Desconhecida (ver PEND-12) | Configurada com RC Mínimo 8% e Desconto NTC Máximo 25% |
| **Cadastros 408/420** | Já configurados para rotas ativas | Revisados mensalmente para garantir custos atualizados |
| **[Opção 903](../cadastros/903-parametros-gerais.md)/OUTROS** | Possivelmente com valores padrão antigos | Seguro 0,3%, GRIS 0,08%, ICMS/PIS/COFINS conforme legislação atual |
| **Controle de prejuízos** | Nenhum (descoberto só no fechamento mensal, se muito) | Planilha de acompanhamento + ação corretiva imediata |

**Impacto esperado**: Redução de 100% dos CTRCs com prejuízo em 30 dias. Aumento de margem média de 5% para 10-12%.

---

## Erros Comuns e Soluções

| Erro | Sintoma | Causa | Solução |
|------|---------|-------|---------|
| **Relatório 031 sempre vazio, mas sei que há prejuízos** | Lista vazia na [opção 056](../relatorios/056-informacoes-gerenciais.md), mas fechamento mensal mostra prejuízo | [Opção 062](../comercial/062-parametros-frete.md) nunca configurada (RC Mínimo = 0%) | Configurar RC Mínimo na [opção 062](../comercial/062-parametros-frete.md) (sugestão: 8%). SSW só lista CTRCs abaixo do parâmetro configurado |
| **TRANSFER muito alto em CTRC específico** | Despesa TRANSFER = R$ 800, esperado R$ 500 | Custo parceiro desatualizado ([opção 408](../comercial/408-comissao-unidades.md)) ou SSW pegou custo de rota alternativa (403 vs 903) | Verificar prioridade: ROTA (403) > transportadora ([903](../cadastros/903-parametros-gerais.md)). Atualizar custo na [opção 408](../comercial/408-comissao-unidades.md). Se persistir, verificar se CTRC foi emitido com rota errada |
| **ICMS consumindo 15% do frete** | ICMS = R$ 150 em frete R$ 1.000 | Alíquota ICMS errada na [opção 903](../cadastros/903-parametros-gerais.md) (ex: 18% quando deveria ser 12%) ou destinação interestadual tributada como interna | Acessar 903/OUTROS, verificar alíquota ICMS por UF origem/destino. Corrigir conforme legislação vigente. CTRC já emitido: considerar crédito fiscal ou ajuste no próximo frete |
| **Seguro altíssimo em carga de baixo valor** | Seguro = R$ 200 em mercadoria R$ 10.000 (2%) | % Seguro configurado errado na [opção 903](../cadastros/903-parametros-gerais.md) (ex: 2% ao invés de 0,3%) | Corrigir % Seguro na [opção 903](../cadastros/903-parametros-gerais.md)/OUTROS. Valor mercado: ~0,3%. Se CarVia paga menos à ESSOR, usar valor real pago |
| **RC% negativo mas todas as despesas parecem OK** | FRETE = R$ 1.000, DESPESAS = R$ 1.100 | FRETE de venda configurado abaixo do custo total (cliente negociou desconto excessivo ou erro de digitação) | Acessar opção 420, verificar frete de venda. Calcular custo mínimo (soma despesas + RC Mínimo). Renegociar com cliente ou RECUSAR o frete |
| **CTRC com prejuízo já foi emitido e entregue** | Descoberto só no relatório 031 (tarde demais) | Falta de verificação ANTES da emissão | Não há reversão. Aprender com erro, documentar na planilha de acompanhamento. Para PRÓXIMO CTRC dessa rota: aplicar ETAPA 2 (consultar 101 antes) |
| **Relatório 031 lista CTRC mas [opção 101](../comercial/101-resultado-ctrc.md) não mostra Resultado** | Clicar em Resultado na [opção 101](../comercial/101-resultado-ctrc.md) e tela fica em branco ou erro | CTRC ainda não processado (aguardando cálculos batch SSW) ou bug sistema | Aguardar 1 hora e tentar novamente. Se persistir após 24h, acionar suporte SSW. Provisoriamente, calcular margem manualmente: FRETE (opção 420) - soma despesas estimadas |

---

## Verificação Playwright

| Passo | Seletor/Ação | Validação Esperada |
|-------|--------------|-------------------|
| **Acesso opção 056** | Clicar menu → digitar "056" → Enter | Tela "Informações Gerenciais" carrega com lista "Gerados hoje" |
| **Localizar relatório 031** | Buscar texto "031" ou "CTRCs com Prejuízo" na lista | Relatório 031 aparece na lista (pode ter 0 registros se operação do dia anterior OK) |
| **Abrir relatório 031** | Clicar link relatório 031 | Excel ou visualizador SSW abre com colunas: CTRC, REMETENTE, DESTINATÁRIO, RESULTADO, RC%, RESM |
| **Acesso opção 101** | Clicar menu → digitar "101" → Enter | Tela "Resultado/Consulta CTRC" carrega com campo "Número CTRC" |
| **Consultar CTRC** | Digitar número CTRC → Enter | Dados do CTRC aparecem (data emissão, remetente, destinatário, valor mercadoria, frete) |
| **Visualizar Resultado** | Clicar botão "Resultado" | Tela detalhada com RECEITA, DESPESAS (ICMS, PIS COFINS, SEGURO, GRIS, EXPED, TRANSFER, TRANSBOR, RECEPCAO, DESP DIV), RESULTADO, RC% |
| **Verificar RC%** | Ler campo RC% na tela Resultado | Valor numérico (positivo = lucro, negativo = prejuízo). Ex: "12,5%" ou "-3,2%" |
| **Acesso opção 062** | Clicar menu → digitar "062" → Enter | Tela "Parâmetros Gerais" carrega com abas ou seções (localizar seção Resultado Comercial) |
| **Verificar RC Mínimo** | Navegar até campo "RC Mínimo (%)" | Campo exibe valor configurado (ex: "8,0") ou vazio (nunca configurado) |
| **Salvar RC Mínimo** | Digitar "8" → Salvar | Mensagem "Parâmetros salvos com sucesso" ou similar. Próximo acesso ao campo exibe "8,0" |

**Cobertura**: 90% do fluxo (ETAPA 1, 2, 5). ETAPA 3-4 dependem de contexto (qual despesa corrigir) — validar manualmente caso a caso.

---

## POPs Relacionados

| POP | Título | Relação |
|-----|--------|---------|
| **POP-B01** | Cadastrar Tabela de Preços (Opção 420) | Define FRETE de venda (receita do CTRC). Erro em 420 → RC% incorreto |
| **POP-B02** | Configurar Custos de Parceiros ([Opção 408](../comercial/408-comissao-unidades.md)) | Define TRANSFER, EXPED, TRANSBOR, RECEPCAO (despesas do CTRC). Erro em 408 → prejuízo |
| **POP-B03** | Configurar Tributação e Seguros ([Opção 903](../cadastros/903-parametros-gerais.md)) | Define ICMS, PIS/COFINS, Seguro, GRIS (despesas do CTRC). Erro em 903 → margem distorcida |
| **POP-B05** | Gerar Relatórios Gerenciais ([Opção 056](../relatorios/056-informacoes-gerenciais.md)) | Relatório 031 (CTRCs com prejuízo) é gerado nesta opção |
| **POP-C02** | Emitir CTRC ([Opção 102](../comercial/102-consulta-ctrc.md)) | ANTES de emitir CTRC, aplicar ETAPA 2 deste POP (verificar RC% na [opção 101](../comercial/101-resultado-ctrc.md)) |
| **POP-E02** | Conciliar Contas a Pagar ([Opção 475](../financeiro/475-contas-a-pagar.md)) | DESP DIV (despesas diversas) do CTRC vêm desta opção |

---

## Histórico de Revisões

| Versão | Data | Autor | Alterações |
|--------|------|-------|------------|
| 1.0 | 2026-02-16 | Claude (Agente Logístico) | Criação inicial baseada em doc SSW [opção 101](../comercial/101-resultado-ctrc.md) (636 linhas) e [opção 056](../relatorios/056-informacoes-gerenciais.md) (451 linhas). Prioridade P1. Status: A IMPLANTAR |
