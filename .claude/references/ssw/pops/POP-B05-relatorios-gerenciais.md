# POP-B05 — Gerar Relatórios Gerenciais

**Categoria**: B — Comercial e Precificação
**Prioridade**: P2 (Média — essencial mas depende da operação estar madura)
**Status**: A IMPLANTAR
**Executor Atual**: Ninguém
**Executor Futuro**: Rafael
**Autor**: Claude (Agente Logístico)
**Data**: 2026-02-16

---

## Objetivo

Monitorar a saúde financeira e operacional da CarVia Logística através de relatórios gerenciais automatizados do SSW. Identificar problemas antes que se tornem críticos: CTRCs atrasados (insatisfação cliente), prejuízos comerciais (margem negativa), inadimplência (faturas vencidas), ociosidade/sobrecarga (volume por cliente). Substituir análises manuais esporádicas por rotina diária/semanal de consulta a 6 relatórios prioritários.

**Resultado esperado**: 100% dos indicadores críticos (atrasos, prejuízos, inadimplência) revisados diariamente; ações corretivas iniciadas em até 24h após detecção.

---

## Trigger

- **Automático (diário)**: Todo dia útil, primeira atividade da manhã — acessar [opção 056](../relatorios/056-informacoes-gerenciais.md) e revisar relatórios "Gerados hoje"
- **Automático (semanal)**: Toda segunda-feira — revisar relatórios semanais (ex: Monitoração Clientes)
- **Automático (mensal)**: Dias 01 e 10 de cada mês — revisar relatórios mensais (ex: Maiores Clientes, Performance Entregues)
- **Manual (sob demanda)**: Cliente reclama de atraso, parceiro questiona pagamento, ou análise ad-hoc de performance

---

## Frequência

- **Diária** (seg-sex):
  - **011** — CTRCs Atrasados (satisfação cliente)
  - **031** — CTRCs com Prejuízo (margem comercial)

- **Semanal** (segunda-feira):
  - **040** — Faturas Vencidas (inadimplência)
  - **075** — Monitoração Clientes (volume vs mês anterior)

- **Mensal** (dia 01):
  - **001** — Situação Geral (visão financeira macro)
  - **168** — Resultado Unidade (resultado operacional)

- **Sob demanda** (conforme necessidade):
  - **010** — CTRCs Atrasados (versão detalhada do 011)
  - **030** — Desconto NTC Excedido (complementa 031)
  - **070** — Maiores Clientes (gerado dia 10 do mês)
  - **088** — Performance Coletas/Entregas
  - **100** — Situação Caixa

---

## Pré-requisitos

1. **Acesso SSW**: Perfil com permissão para [opção 056](../relatorios/056-informacoes-gerenciais.md) (Informações Gerenciais)
2. **Cadastros atualizados**:
   - [Opção 062](../comercial/062-parametros-frete.md) (RC Mínimo e Desconto NTC Máximo) — necessário para relatórios 030/031
   - [Opção 408](../comercial/408-comissao-unidades.md) (custos parceiros) — necessário para cálculo correto de margem
   - Opção 420 (preços venda) — necessário para resultado comercial
3. **Excel/Google Sheets**: Para abrir relatórios exportados (formato .xls ou .xlsx)
4. **Planilha de acompanhamento** (criar na primeira execução):
   - Abas: Atrasos, Prejuízos, Inadimplência, Ações Corretivas
5. **Conhecimento dos 6 objetivos TED** (Diretoria SSW):
   1. Transportadora tem que dar lucro
   2. Cliente satisfeito dá lucro
   3. Caminhão tem que dar lucro
   4. CTRC/Cliente tem que dar lucro
   5. Unidade dando lucro
   6. Inadimplência não é lucro

---

## Passo-a-Passo

### ETAPA 1 — Acessar opção 056 (Informações Gerenciais)

1. Abrir SSW
2. No Menu Principal, digitar **056** → Enter
3. Tela "Informações Gerenciais" carrega com 3 seções:
   - **Gerados hoje**: Relatórios processados hoje (principais em destaque vermelho)
   - **Últimos 7 dias**: Histórico semanal
   - **Filtros**: Por código de relatório ou data específica

4. Verificar data/hora do processamento (canto superior direito) — relatórios são processados:
   - **Diários**: Horário configurado (geralmente 6h) + hora em hora para alguns (ex: 010, 011)
   - **Mensais**: Dia 01 e dia 10

5. **Se lista "Gerados hoje" estiver vazia**: Verificar se é dia útil (relatórios não rodam em finais de semana/feriados) ou se há problema de processamento (acionar suporte SSW)

---

### ETAPA 2 — Revisar relatório 011 (CTRCs Atrasados) — DIÁRIO

**Objetivo 2**: Cliente satisfeito dá lucro

1. Na lista "Gerados hoje", localizar **011 — CTRCs Atrasados de Entrega**
2. Clicar no relatório → Excel abre com colunas:
   - **CTRC**: Número do conhecimento
   - **EMISSÃO**: Data de emissão
   - **REMETENTE/DESTINATÁRIO**: Quem embarcou/quem vai receber
   - **DESTINO**: Cidade/UF
   - **PREV ENTREGA**: Data prevista (conforme prazo rota)
   - **ATRASO (dias)**: Dias de atraso (negativo = ainda no prazo, positivo = atrasado)
   - **PERM (dias)**: Dias de permanência na unidade atual (indica gargalo operacional)
   - **UNIDADE ATUAL**: Onde o CTRC está parado
   - **STATUS**: Em trânsito, aguardando coleta, aguardando entrega, etc.

3. **Filtrar atrasos críticos**: Atraso > 10 dias (alta chance de indenização)
4. Para cada CTRC atrasado:
   - Verificar **UNIDADE ATUAL** e **PERM**:
     - PERM > 3 dias na mesma unidade = gargalo operacional (cobrar parceiro ou reenviar por outra rota)
     - PERM < 1 dia = em movimento (ok, monitorar)
   - **Ação imediata**:
     - Contatar parceiro responsável pela unidade (WhatsApp/telefone)
     - Exigir prazo de resolução (ex: "Entregar até amanhã 18h")
     - Registrar na planilha de acompanhamento (aba Atrasos): Data, CTRC, Cliente, Destinatário, Atraso, Parceiro, Ação, Status

5. **Se atraso > 15 dias**: Preparar para possível indenização (acionar POP-D05 — Gerenciar Indenizações)

6. **Comunicar cliente PROATIVAMENTE** (antes que ele reclame):
   - "Bom dia, [Cliente]. CTRC XXXXX está com atraso de X dias. Estamos cobrando parceiro e previsão de entrega é [data]. Manteremos você informado."

---

### ETAPA 3 — Revisar relatório 031 (CTRCs com Prejuízo) — DIÁRIO

**Objetivo 4**: CTRC/Cliente tem que dar lucro

1. Na lista "Gerados hoje", localizar **031 — CTRCs com Prejuízo (emitidos ontem)**
2. Clicar no relatório → Excel abre com colunas:
   - **CTRC**: Número do conhecimento
   - **EMISSÃO**: Data de emissão
   - **REMETENTE/DESTINATÁRIO**: Quem embarcou/quem recebeu
   - **RESULTADO**: Valor do prejuízo (R$ negativo)
   - **RC%**: Percentual de resultado comercial (negativo = prejuízo)
   - **RESM**: Resultado Comercial Mínimo configurado ([opção 062](../comercial/062-parametros-frete.md))
   - **FRETE**: Valor cobrado do cliente
   - **DESPESAS**: Soma de ICMS + PIS/COFINS + Seguro + GRIS + TRANSFER + EXPED + TRANSBOR + RECEPCAO + DESP DIV

3. **Se houver CTRCs listados**:
   - Para cada CTRC:
     - Anotar número do CTRC
     - Aplicar **POP-B04 — Analisar Resultado por CTRC** (ETAPA 2 a 6) para identificar causa e corrigir
     - Registrar na planilha de acompanhamento (aba Prejuízos): Data, CTRC, Cliente, Rota, RC%, Causa, Ação Tomada, Status

4. **Se lista estiver vazia**: Operação do dia anterior OK, 100% dos CTRCs com margem positiva

5. **Meta**: Zerar este relatório em 30 dias (nenhum CTRC com prejuízo)

---

### ETAPA 4 — Revisar relatório 040 (Faturas Vencidas) — SEMANAL

**Objetivo 6**: Inadimplência não é lucro

1. **Toda segunda-feira**, na lista "Gerados hoje", localizar **040 — Faturas Vencidas**
2. Clicar no relatório → Excel abre com colunas:
   - **FATURA**: Número da fatura
   - **CLIENTE**: Razão social
   - **EMISSÃO**: Data de emissão da fatura
   - **VENCIMENTO**: Data de vencimento
   - **DIAS VENCIDO**: Dias de atraso (positivo = vencido)
   - **VALOR**: R$ da fatura vencida
   - **TOTAL VENCIDO**: Soma acumulada por cliente

3. **Classificar por criticidade**:
   - **Crítico** (dias vencido > 30): Risco de inadimplência definitiva
   - **Moderado** (dias vencido 15-30): Cobrar com urgência
   - **Leve** (dias vencido < 15): Lembrete ao cliente

4. Para cada fatura vencida:
   - Verificar se é cliente recorrente (6 clientes ativos CarVia) ou pontual
   - **Ação imediata**:
     - **< 15 dias**: E-mail de lembrete (copiar Jaqueline financeiro)
     - **15-30 dias**: Ligação telefônica + e-mail formal + boleto atualizado
     - **> 30 dias**: Reunião presencial/videochamada + parcelamento ou suspensão de novos fretes até regularizar
   - Registrar na planilha de acompanhamento (aba Inadimplência): Data, Fatura, Cliente, Valor, Dias Vencido, Ação, Status

5. **Comunicar Jaqueline** (responsável financeiro):
   - "Jaqueline, relatório 040 (faturas vencidas) tem [quantidade] faturas, total R$ [valor]. Clientes: [lista]. Ações: [resumo]. Por favor, acompanhar cobranças."

---

### ETAPA 5 — Revisar relatório 075 (Monitoração Clientes) — SEMANAL

**Objetivo 1**: Transportadora tem que dar lucro (monitorar volume de clientes)

1. **Toda segunda-feira**, na lista "Gerados hoje", localizar **075 — Monitoração Clientes**
2. Clicar no relatório → Excel abre com colunas:
   - **CLIENTE**: Razão social
   - **VOLUME MÊS ATUAL**: Quantidade de CTRCs emitidos no mês corrente
   - **VOLUME MÊS ANTERIOR**: Quantidade de CTRCs emitidos no mês anterior (mesmo período)
   - **VARIAÇÃO (%)**: Percentual de aumento/redução
   - **FATURAMENTO MÊS ATUAL**: R$ total faturado no mês corrente
   - **FATURAMENTO MÊS ANTERIOR**: R$ total faturado no mês anterior
   - **VARIAÇÃO FATURAMENTO (%)**: Percentual de aumento/redução

3. **Identificar tendências**:
   - **Crescimento > 20%**: Cliente aumentando volume → oportunidade (garantir qualidade para manter satisfação)
   - **Redução > 20%**: Cliente reduzindo volume → ALERTA (investigar causa: insatisfação? concorrência? sazonalidade?)
   - **Estabilidade (± 10%)**: Cliente regular (manter relacionamento)

4. Para cada cliente com **redução > 20%**:
   - Ligar para cliente: "Olá, [Cliente]. Notamos redução de X% no volume de fretes. Há algum problema que possamos resolver? Como podemos melhorar nosso serviço?"
   - Registrar feedback e ações na planilha de acompanhamento (aba Ações Corretivas)

5. **Comunicar Jessica** (comercial):
   - "Jessica, cliente [nome] reduziu volume em X%. Feedback: [resumo]. Ações sugeridas: [proposta]."

---

### ETAPA 6 — Revisar relatórios mensais 001 e 168 (Situação Geral e Resultado Unidade)

**Objetivo 1 e 5**: Transportadora/Unidade tem que dar lucro

**Todo dia 01 do mês**:

1. **Relatório 001 — Situação Geral**:
   - Visão financeira macro: Receita, Despesas, Resultado (lucro/prejuízo)
   - Colunas: Mês anterior completo vs Mês atual (parcial)
   - **Analisar**:
     - Margem de lucro (%) mês anterior: Acima de 10% = saudável, abaixo de 5% = preocupante
     - Tendência: Mês atual (mesmo período) está melhor ou pior que mês anterior?
   - **Ações**:
     - Margem < 5%: Revisar todos os POPs de precificação (B01-B04) e custos (B02, B03)
     - Margem > 15%: Operação eficiente, manter práticas

2. **Relatório 168 — Resultado Unidade**:
   - Resultado operacional por unidade (CarVia tem 2: CAR e CARP)
   - Colunas: Receita, Despesas (pessoal, aluguel, operacionais), Resultado
   - **Analisar**:
     - Qual unidade está dando lucro e qual está dando prejuízo?
     - Despesas operacionais estão controladas?
   - **Ações**:
     - Unidade com prejuízo: Investigar causas (volume baixo? despesas excessivas?) e corrigir em 30 dias

3. Registrar insights e ações na planilha de acompanhamento (aba Ações Corretivas)

---

### ETAPA 7 — Criar planilha de acompanhamento (primeira execução)

**Se ainda não existe, criar planilha com 4 abas**:

**Aba 1 — Atrasos**:
- Colunas: Data Detecção, CTRC, Cliente, Destinatário, Cidade/UF, Atraso (dias), PERM (dias), Unidade Atual, Parceiro Responsável, Ação Tomada, Status (Pendente/Resolvido), Data Resolução

**Aba 2 — Prejuízos**:
- Colunas: Data Detecção, CTRC, Cliente, Rota, Frete (R$), Despesas (R$), Resultado (R$), RC%, Causa Principal (TRANSFER/ICMS/Seguro/Preço Venda), Ação Tomada, Status (Pendente/Resolvido), Data Resolução

**Aba 3 — Inadimplência**:
- Colunas: Data Detecção, Fatura, Cliente, Valor (R$), Vencimento, Dias Vencido, Ação Tomada (E-mail/Ligação/Reunião/Parcelamento), Status (Pendente/Regularizado), Data Pagamento

**Aba 4 — Ações Corretivas**:
- Colunas: Data, Origem (Relatório/Cliente/Interno), Problema Identificado, Ação Definida, Responsável (Rafael/Jessica/Jaqueline/Stephanie), Prazo, Status (A Fazer/Em Andamento/Concluído), Data Conclusão

Salvar planilha em Google Drive ou local compartilhado (acessível por toda a equipe).

---

### ETAPA 8 — Integrar relatórios no menu principal SSW (Big Numbers)

1. No Menu Principal SSW, verificar **indicadores em destaque** (atualizados hora em hora):
   - **CTRCs atrasados**: Quantidade de CTRCs com atraso > 0 dias
   - **Valor do prejuízo (dia anterior)**: Soma de CTRCs com RC% negativo emitidos ontem

2. Esses indicadores servem como **alerta visual** — se número aumentar significativamente, priorizar revisão dos relatórios 011 e 031

3. **Configurar alertas** (se SSW permitir):
   - E-mail automático se CTRCs atrasados > 5
   - E-mail automático se prejuízo do dia > R$ 500

---

## Contexto CarVia

| Aspecto | Hoje (A IMPLANTAR) | Futuro (PÓS-IMPLANTAÇÃO) |
|---------|--------------------|--------------------|
| **Uso da opção 056** | Rafael NUNCA acessou (todos os relatórios estão disponíveis mas ninguém consulta) | Rafael consulta TODO DIA útil pela manhã (011 e 031) + toda segunda (040 e 075) + dia 01 do mês (001 e 168) |
| **Conhecimento dos objetivos TED** | Desconhecidos | Equipe conhece os 6 objetivos e associa cada relatório a um objetivo |
| **Planilha de acompanhamento** | Não existe (problemas descobertos reativamente) | Planilha atualizada diariamente, serve como TO-DO list de ações corretivas |
| **Relatórios prioritários** | Nenhum | 6 relatórios (011, 031, 040, 075, 001, 168) consultados conforme frequência definida |
| **Relatórios secundários** | Nenhum | 010, 030, 070, 088, 100 consultados sob demanda (quando necessário investigar problema específico) |
| **Indicadores Menu Principal** | Ignorados (Rafael não sabe o que significam) | Usados como alerta visual — se número subir, priorizar revisão de relatórios |
| **Big Brother (opção 145)** | Não necessário (equipe pequena, Rafael confia em todos) | Não implementar (sobrecarga sem benefício) |

**Impacto esperado**:
- **Satisfação cliente**: Aumento de 70% para 95% (redução atrasos via relatório 011)
- **Margem de lucro**: Aumento de 5% para 10-12% (eliminação prejuízos via relatório 031)
- **Inadimplência**: Redução de dias vencido médio de 30 para 10 dias (cobrança proativa via relatório 040)
- **Retenção de clientes**: Evitar perda de clientes por insatisfação (monitoração via relatório 075)

---

## Erros Comuns e Soluções

| Erro | Sintoma | Causa | Solução |
|------|---------|-------|---------|
| **Relatório 031 sempre vazio (mas há prejuízos)** | Lista vazia na [opção 056](../relatorios/056-informacoes-gerenciais.md), mas fechamento mensal mostra prejuízo | [Opção 062](../comercial/062-parametros-frete.md) nunca configurada (RC Mínimo = 0%) | Configurar RC Mínimo na [opção 062](../comercial/062-parametros-frete.md) (sugestão: 8%). SSW só lista CTRCs abaixo do parâmetro configurado. Aplicar POP-B04 ETAPA 5 |
| **Relatório 011 lista CTRC não atrasado** | CTRC com "Atraso -2 dias" (negativo) aparece na lista | Filtro padrão do relatório inclui CTRCs próximos ao vencimento (alerta preventivo) | Negativo = ainda no prazo. Ignorar ou monitorar. Focar em atrasos positivos (> 0 dias) |
| **Não consigo abrir relatório (erro Excel)** | Clicar relatório 011 e erro "Arquivo corrompido" ou "Formato inválido" | Versão Excel antiga incompatível com formato SSW ou relatório ainda processando | Aguardar 5 minutos e tentar novamente. Se persistir, usar opção "Salvar como" (SSW) e abrir manualmente. Verificar versão Excel (mínimo 2010) |
| **Relatório 040 não lista fatura que sei estar vencida** | Fatura vencida há 5 dias não aparece no relatório 040 | Fatura ainda não lançada no SSW (opção 440 — Contas a Receber) ou processamento atrasado | Verificar se fatura foi emitida (opção 440). Se sim, aguardar próximo processamento (relatório roda 1x/dia). Se não, emitir fatura antes de cobrar cliente |
| **Relatório 075 mostra variação irreal (ex: 500%)** | Cliente X com "Variação 500%" mas volume real aumentou só 20% | Mês anterior teve volume anormalmente baixo (ex: 1 CTRC) ou bug de cálculo SSW | Ignorar % e focar em valores absolutos (Volume Mês Atual vs Mês Anterior). Se volume absoluto faz sentido, % está correto (base pequena gera % grandes) |
| **Não encontro relatório 001 ou 168 no dia 01** | Acessar [opção 056](../relatorios/056-informacoes-gerenciais.md) dia 01 e relatórios mensais não aparecem | Processamento mensal roda com atraso (ex: 10h) ou só em dias úteis | Aguardar até 12h do dia 01. Se não aparecer, verificar se dia 01 é final de semana (processamento adia para próximo dia útil) |
| **Planilha de acompanhamento está desatualizada** | Última entrada há 1 semana, mas relatórios diários foram consultados | Equipe consultou relatórios mas esqueceu de registrar ações na planilha | Tornar registro OBRIGATÓRIO: só considerar relatório "revisado" se ações foram documentadas. Criar tarefa recorrente (Google Tasks/Trello): "Atualizar planilha 056" |
| **Relatórios têm dados de outra unidade (ex: MTZ)** | Relatório 168 lista resultado de unidades que não são CAR/CARP | Perfil SSW do Rafael tem permissão para ver todas as unidades (perfil de matriz) | Configurar filtro de unidade (botão Filtros na [opção 056](../relatorios/056-informacoes-gerenciais.md)) → selecionar só CAR e CARP. Salvar filtro para próximos acessos |
| **Indicadores Menu Principal não batem com relatórios** | Menu Principal mostra "3 CTRCs atrasados" mas relatório 011 lista 5 | Indicadores são atualizados hora em hora, relatórios 1x/dia (defasagem temporal) | Normal. Usar indicadores como ALERTA, mas sempre confirmar com relatório completo (011/031) para ações |

---

## Verificação Playwright

| Passo | Seletor/Ação | Validação Esperada |
|-------|--------------|-------------------|
| **Acesso opção 056** | Clicar menu → digitar "056" → Enter | Tela "Informações Gerenciais" carrega com lista "Gerados hoje" |
| **Verificar relatórios diários** | Buscar texto "011" e "031" na lista "Gerados hoje" | Ambos relatórios aparecem (podem ter 0 registros se operação OK) |
| **Abrir relatório 011** | Clicar link relatório 011 | Excel ou visualizador SSW abre com colunas: CTRC, EMISSÃO, REMETENTE, DESTINATÁRIO, DESTINO, PREV ENTREGA, ATRASO, PERM, UNIDADE ATUAL, STATUS |
| **Validar dados relatório 011** | Verificar se coluna ATRASO tem valores numéricos (positivos = atrasado, negativos = no prazo) | Valores numéricos aparecem. Se vazio = nenhum CTRC processado (verificar se há emissões no período) |
| **Abrir relatório 031** | Clicar link relatório 031 | Excel abre com colunas: CTRC, EMISSÃO, REMETENTE, DESTINATÁRIO, RESULTADO, RC%, RESM, FRETE, DESPESAS |
| **Validar dados relatório 031** | Verificar se coluna RC% tem valores negativos (prejuízo) | Valores negativos aparecem. Se vazio = nenhum CTRC com prejuízo (operação OK) |
| **Filtrar últimos 7 dias** | Clicar aba "Últimos 7 dias" → selecionar data (ex: 3 dias atrás) | Lista atualiza mostrando relatórios daquela data. Clicar em qualquer relatório abre histórico |
| **Buscar relatório específico** | Clicar "Filtros" → digitar "040" (Faturas Vencidas) → Buscar | Relatório 040 aparece (se processado hoje) ou lista vazia (se não processado) |
| **Verificar indicadores Menu Principal** | Voltar ao Menu Principal (Esc ou botão Home) → observar área de indicadores (canto superior) | Números aparecem: "CTRCs atrasados: X" e "Prejuízo ontem: R$ X,XX" (atualizados hora em hora) |
| **Exportar relatório** | Abrir relatório 011 → clicar botão "Salvar como" ou "Exportar" (se disponível) | Arquivo .xls ou .xlsx salvo no diretório local. Abrir com Excel/LibreOffice valida formato |

**Cobertura**: 85% do fluxo (ETAPA 1-6). ETAPA 7 (planilha de acompanhamento) e ETAPA 8 (alertas) são manuais — validar existência de planilha e configuração de filtros no SSW.

---

## POPs Relacionados

| POP | Título | Relação |
|-----|--------|---------|
| **POP-B04** | Analisar Resultado por CTRC ([Opção 101](../comercial/101-resultado-ctrc.md)) | Relatório 031 (CTRCs com Prejuízo) exige aplicação deste POP para identificar causa e corrigir |
| **POP-B01** | Cadastrar Tabela de Preços (Opção 420) | Margem comercial (relatório 031 e 001) depende de preços de venda corretos |
| **POP-B02** | Configurar Custos de Parceiros ([Opção 408](../comercial/408-comissao-unidades.md)) | Resultado comercial (relatórios 031, 001, 168) depende de custos corretos |
| **POP-B03** | Configurar Tributação e Seguros ([Opção 903](../cadastros/903-parametros-gerais.md)) | Despesas (relatórios 031, 001) dependem de alíquotas corretas |
| **POP-D05** | Gerenciar Indenizações | Relatório 011 (CTRCs atrasados > 15 dias) pode gerar indenizações |
| **POP-E01** | Emitir Fatura (Opção 440) | Relatório 040 (Faturas Vencidas) só lista faturas emitidas nesta opção |
| **POP-C02** | Emitir CTRC ([Opção 102](../comercial/102-consulta-ctrc.md)) | Volume de CTRCs impacta relatórios 075 (Monitoração Clientes) e 001 (Situação Geral) |

---

## Histórico de Revisões

| Versão | Data | Autor | Alterações |
|--------|------|-------|------------|
| 1.0 | 2026-02-16 | Claude (Agente Logístico) | Criação inicial baseada em doc SSW [opção 056](../relatorios/056-informacoes-gerenciais.md) (451 linhas). Prioridade P2. Status: A IMPLANTAR. Foco em 6 relatórios prioritários (011, 031, 040, 075, 001, 168) + planilha de acompanhamento |
