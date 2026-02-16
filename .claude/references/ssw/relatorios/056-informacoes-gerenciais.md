# Opção 056 — Informações Gerenciais (Relatórios Diários)

> **Módulo**: Info Gerenciais
> **Páginas de ajuda**: 15 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Dezenas de relatórios diários agrupados em torno de 6 objetivos vitais para direção da transportadora com foco no LUCRO. Processados automaticamente e disponibilizados por até 1 ano, sem necessidade de BI ou gráficos coloridos.

## Quando Usar
- Diariamente pela direção, gerentes de filiais e alta administração
- Acompanhamento de metas e ações corretivas (Big Brother SSW)
- Avaliação de performance em videoconferência
- Monitoramento de objetivos estratégicos da transportadora

## Conceitos Fundamentais

### 6 Objetivos (TED - Direção)
1. **Transportadora tem que dar lucro** (Objetivo 1)
2. **Cliente satisfeito dá lucro** (Objetivo 2 - Entregas no prazo)
3. **CTRC/Cliente tem que dar lucro** (Objetivo 4)
4. **Caminhão tem que dar lucro** (Objetivo 3)
5. **Unidade tem que dar lucro** (Objetivo 5)
6. **Inadimplência não é lucro** (Objetivo 6)

### Resultados-chave (Velocidade)
- Metas numéricas com tempo definido
- Agressivos, mas realistas
- Mensuráveis e verificáveis

## Interface

### Tela Inicial
| Elemento | Descrição |
|----------|-----------|
| **Gerados hoje** | Relatórios processados hoje (fatos até meia-noite de ontem). Principais em vermelho |
| **Últimos 7 dias** | Link para relatórios da semana |
| **Filtros** | Por código do relatório ou data |
| **Abrir relatório** | Clique sobre a linha |
| **Período** | MENSAIS acumulam até ontem. Disponível ano corrente e anterior |

### Recursos nos Relatórios
| Recurso | Função |
|---------|--------|
| **Excel** | Transforma em planilha (corte no +) |
| **Localizar** | Busca caracteres no relatório |
| **Ajuda (?)** | Vitais (linha vermelha) têm instruções de uso |

## Relatórios Disponíveis

### OBJETIVO 1 — Transportadora tem que dar LUCRO

#### 001 - SITUAÇÃO GERAL
- Mostra ENTRADAS e SAÍDAS para viabilidade do negócio
- [Mais detalhes](ssw0344.htm)

#### 075 - MONITORAÇÃO DE CLIENTES - POR UNIDADE
- Volume acumulado do mês por cliente da unidade vs mês anterior
- Acompanhamento por vendedor da unidade
- Disponível nas unidades
- [Mais detalhes](ssw0663.htm)

#### 050 e 052 - VOLUMES EXPEDIDOS
- 050: Volume diário (dia anterior)
- 052: Volume acumulado no mês
- Analítico por cliente, RESUMO por unidade (MTZ)
- Não considera: cancelados, anulados, de anulação (opção 520), unificadores (opção 172)
- [Mais detalhes](ssw1296.htm)

#### 054 e 056 - VOLUMES RECEBIDOS
- 054: Volume diário
- 056: Volume acumulado no mês
- Analítico por cliente, RESUMO por unidade (MTZ)
- [Mais detalhes](ssw1297.htm)

#### 058 e 059 - VOLUMES EXPEDIDOS E RECEBIDOS - POR CIDADE
- Por unidade e cidade
- Cidades com setores de coleta/entrega (opção 404) mostram totais por setor
- [Mais detalhes](ssw0529.htm)

#### 060 e 061 - VOLUMES DE CARGAS TRANSBORDADAS
- 060: Volume diário
- 061: Volume acumulado no mês
- RESUMO por unidade (MTZ)
- [Mais detalhes](ssw1298.htm)

#### 069 - MAIORES CLIENTES - DA TRANSPORTADORA EXCEL
- Mesmo relatório 070, em Excel

#### 070 - MAIORES CLIENTES
- Disponível dias 01 e 10
- Ordenado por faturamento do mês anterior
- Classificação ABC e indicadores
- Filiais veem seus clientes, MTZ vê todas
- Coluna REAJNE: % reajuste necessário para atingir resultado (opção 469)
- [Mais detalhes](ssw0664.htm)

#### 100 - SITUAÇÃO DO CAIXA
- Fluxo financeiro de 15 dias futuros
- Entradas por conta bancária, saídas por eventos
- [Mais detalhes](ssw0365.htm)

#### 150 e 152 - VOLUMES DOS PAGADORES/NÃO PAGADORES
- 150: Volume diário
- 152: Volume acumulado do mês
- Separado por pagadores e não pagadores
- [Mais detalhes](ssw1085.htm)

#### 151 e 153 - VOLUMES DOS PAGADORES
- 151: Volume diário
- 153: Volume acumulado do mês
- Analítico por clientes pagadores, RESUMO por unidade (MTZ)
- [Mais detalhes](ssw1298.htm)

---

### OBJETIVO 2 — Entregas no prazo (Cliente satisfeito dá lucro)

#### 010, 011 e 013 - CTRCS ATRASADOS DE ENTREGA
- CTRCs com entrega vencida e não baixados
- 013: Mesmo que 011, em Excel
- Mais importante sob perspectiva do cliente
- [Mais detalhes](ssw0133.htm)

#### 088 - PERFORMANCE DE COLETAS E ENTREGAS
- Situação atual: não coletados e não entregues
- Últimos 7 dias e 30 dias
- Relatório diário
- [Mais detalhes](ssw0722.htm)

#### 080 - SITUAÇÃO DE SAÍDAS E CHEGADAS DE VEÍCULOS
- Veículos (Manifestos) que saíram/chegaram nas últimas 24h
- Comparação com horários limites (opção 403)
- [Mais detalhes](ssw0355.htm)

#### 164 - TEMPO DE TRANSBORDO POR UNIDADE
- Tempo de permanência de CTRCs por unidade
- Separado: saídos ontem vs ainda na unidade
- Relatório diário
- [Mais detalhes](ssw0858.htm)

#### 012 - PERFORMANCE DOS CTRCS ENTREGUES
- CTRCs entregues ontem
- Gráfico: quantos dias úteis antes/depois da previsão
- Relatório diário
- [Mais detalhes](ssw0878.htm)

#### 087 - OCORRÊNCIAS DADAS FORA DO CLIENTE
- Veículos e CTRCs entregues
- Indica se ocorrência foi via SSWMobile no local de entrega ou não
- [Mais detalhes](ssw3201.htm)

#### 084 - PERFORMANCE DE ENTREGAS POR CIDADE DESTINO
- Performance para todas as cidades atendidas
- Relatório mensal (dias 01 e 10)
- [Mais detalhes](ssw0088.htm)

#### 083 - PERFORMANCE DE ENTREGAS POR CLIENTE EMITENTE
- Performance para todos clientes emitentes
- Relatório mensal (dias 01 e 10)
- [Mais detalhes](ssw0088.htm)

#### 081 - PERFORMANCE ENTREGA UNID DESTINATÁRIA (SEM TRANSFERÊNCIA)
- Avalia parceiro entregador
- Considera só prazo de entrega, sem transferência
- [Mais detalhes](ssw0088.htm)

---

### OBJETIVO 4 — CTRC e o cliente têm que dar LUCRO

#### 030 e 031 - CTRCS COM PREJUÍZO
- CTRCs emitidos no dia anterior com resultado abaixo do estabelecido (opção 469)
- Duas avaliações: Resultado Comercial Mínimo e Desconto Máximo sobre NTC
- "Nenhuma transportadora quebrou com armazém vazio, e sim com armazém cheio de CTRCs com frete ruim"
- [Mais detalhes](ssw0190.htm)

#### SITUAÇÃO DO CLIENTE (opção 102)
- Item GERAL e link PRODUÇÃO MENSAL
- Dados de até 24 meses

#### RESULTADO POR CLIENTE (opção 449)
- Por rota e por peso
- Resultados comerciais do cliente

#### 032 - VERIFICAÇÃO FRETE CALCULADO PELO CLIENTE(EDI)
- Clientes que enviam valor do frete no EDI
- Compara frete do EDI com calculado pelas tabelas
- Mostra diferença
- [Mais detalhes](ssw0190.htm)

#### 130 - TAXAS ADICIONAIS NÃO COBRADAS
- CTRCs com serviços adicionais prestados mas não cobrados
- Geralmente por falta de tabelas ou não emissão de CTRC Complementar
- [Mais detalhes](ssw0476.htm)

---

### OBJETIVO 3 — Caminhão tem que dar LUCRO

#### 020 e 023 - RESULTADO DE VIAGENS
- Monitora principal despesa: CAMINHÃO
- Compara frete recebido (manifestos) com custo CTRB
- Custo não pode ultrapassar % estabelecido em modelo de resultados
- Mesmo raciocínio para coletas/entregas (Romaneio vs Remuneração)
- [Mais detalhes](ssw0136.htm, ssw0702.htm)

#### 021 - RESULTADO DE TRANSFERÊNCIAS REALIZADAS (MENSAL)
- Disponível todo dia 01
- Por veículo, motorista e rota
- Quanto veículo de transferência comprometeu do frete no mês
- [Mais detalhes](ssw0511.htm)

#### 023 - RESULTADO DAS COLETAS/ENTREGAS
- Diário, por unidade
- Quanto veículos de coletas/entregas comprometeram dos fretes
- [Mais detalhes](ssw0702.htm)

#### 022 - RESULTADO DE COLETAS/ENTREGAS REALIZADAS (MENSAL)
- Disponível dia 01 do mês seguinte
- Todos CTRBs Coleta/Entrega emitidos
- Respectivos fretes e índice de comprometimento
- [Mais detalhes](ssw0514.htm)

---

### OBJETIVO 5 — Unidade dando LUCRO

#### 168 - RESULTADO DA UNIDADE
- Resultado = receita dos serviços (opção 408, inclusive filiais) - despesas (opção 475)

#### 166 e 167 - RESULTADO COMERCIAL
- Alternativa: soma dos resultados individuais de todos CTRCs emitidos (opção 101) no dia
- Receita: fretes dos CTRCs
- Despesas: pagamentos às unidades (expedição, recepção, etc) + transferência (opção 403)
- [Mais detalhes](ssw1068.htm)

---

### OBJETIVO 6 — Inadimplência

#### 040 - FATURAS VENCIDAS
- Por cliente, todas faturas atrasadas de liquidação
- Processado às 09:30h (após recepção de retornos bancários)
- Para cobrança por vendedores, gerentes e outros (usar opção 480 para registrar esforço)
- [Mais detalhes](ssw0087.htm)

#### 157 - E-MAILS ENVIADOS - ENVIO DE FATURAS
- Faturas enviadas via e-mail conforme cadastro cliente (opção 384/Envia fatura bloqueto)
- [Mais detalhes](ssw0506.htm)

#### 154 - FATURA POR EMAIL NÃO IMPRESSA
- Faturas por e-mail não impressas a 4 dias ou menos antes do vencimento
- [Mais detalhes](ssw0506.htm)

#### 156 - E-MAILS ENVIADOS - ATRASO DE LIQUIDAÇÃO
- E-mails disparados por atraso conforme cadastro cliente (opção 384/Envia aviso atraso) e opção 903/Prazos
- [Mais detalhes](ssw0087.htm)

#### 041 - FRETE A VISTA NÃO LIQUIDADO
- CTRCs A VISTA não liquidados (CIF ou FOB)
- Processado de hora em hora
- CIF relacionado na origem, FOB no destino
- Excel disponível também no relatório 44
- Colunas: TIPO, ROMANEIO, PLACA, VENCIMEN, ATRASO, M (arquivo morto), PIX (QR Code ativo)
- [Mais detalhes](ssw0085.htm)

#### 155 - E-MAILS ENVIADOS AUTOMATICAMENTE
- E-mails disparados pela opção 100: faturas não liquidadas mensal, aniversário, mensagens diversas
- [Mais detalhes](ssw0597.htm)

---

## Relatórios Comerciais

### Monitoração de Clientes

#### 075 - MONITORAÇÃO DE CLIENTES - POR UNIDADE
- Volume acumulado do mês dos clientes da unidade vs mês anterior
- Por vendedor da unidade
- Disponível nas unidades
- [Mais detalhes](ssw0663.htm)

#### 073 - MONITORAÇÃO DE CLIENTES - REF MÊS ANTERIOR
- Volume acumulado do mês dos clientes da transportadora vs mês anterior
- Por vendedor de toda transportadora
- Disponível na matriz
- [Mais detalhes](ssw0663.htm)

### Produção de Vendedores

Não considera: cancelados, de anulação (opção 520), unificadores (opção 172), CTRCs da MTZ

#### 125 - PRODUÇÃO DE VENDEDOR
- Diário: quanto cada vendedor produziu no mês
- Totalizado por cliente
- Cliente pode ser ALVO, com METAS por cliente e vendedor
- Disponível nas unidades
- [Mais detalhes](ssw0356.htm)

#### 126 - PRODUÇÃO DE VENDEDOR - RESUMO
- Relatório 125 mostrando apenas totais por vendedor de todas unidades
- Disponível apenas para matriz
- [Mais detalhes](ssw0356.htm)

### Comissionamento de Vendedores

#### Uso das Unidades

**120 - COMISSÃO DE VENDEDOR**
- Mapa analítico (por CTRC)
- Vendedores da unidade
- [Mais detalhes](ssw0342.htm)

**121 - COMISSÃO DE VENDEDOR - EXCEL**
- Mapa em Excel dos vendedores da unidade
- [Mais detalhes](ssw0342.htm)

**127 - COMISSÃO DE VENDEDOR - PREVISÃO**
- Por vendedor, comissões (CTRCs) previstas para pagamento
- PROX COM (já garantidas), PREV COM (dependentes de condição, ex: liquidação)
- Útil para identificar comissões não pagas mas incluídas na previsão
- [Mais detalhes](ssw0361.htm)

**123 - CLIENTES SEM MOVIMENTAÇÃO - POR VENDEDOR**
- Clientes vinculados ao vendedor sem movimentação no período de comissionamento

#### Uso da Matriz

**124 - COMISSÃO DE VENDEDOR - RESUMO**
- Mapa (120) totalizado por cliente
- Para pagamento das comissões
- Por unidades, todos vendedores
- [Mais detalhes](ssw0343.htm)

**128 - COMISSÃO DE VENDEDOR - PREVISÃO SINTÉTICO**
- Relatório 127 das unidades, apenas para Matriz
- Apenas por vendedor
- Comissões futuras a serem pagas
- [Mais detalhes](ssw0361.htm)

### Comissionamento de Cotação

#### 131 - COMISSÃO DE COTAÇÃO
- Mapa analítico (por CTRC) dos cotadores da unidade
- Processado junto com comissão de vendedores (relatório 120)
- [Mais detalhes](ssw0577.htm)

#### 132 - COMISSÃO DE COTAÇÃO - RESUMO
- Valores dos cotadores de todas unidades
- Resumo do 131, para matriz
- [Mais detalhes](ssw0577.htm)

---

## Outros Relatórios

#### 110 - COMISSÃO DE AGENCIAMENTO
- Comissão de agências e parceiros conforme opção 408
- Agendado pela opção 903/Processamento batch
- Uso das unidades
- [Mais detalhes](ssw0342.htm)

#### 111 - COMISSÃO DE AGENCIAMENTO - PREVISÃO
- Comissões devidas mas não pagas (condição não atendida)
- [Mais detalhes](ssw0342.htm)

#### 112 - COMISSÃO DE AGENCIAMENTO - RESUMO
- Resumido por unidade, de todas unidades
- [Mais detalhes](ssw0342.htm)

#### 165 - RELATÓRIO PARA CONFERÊNCIA DE AVERBAÇÃO
- Dados do arquivo de averbação (opção 600)
- Valores de mercadorias para avaliar correção
- Gerado junto com arquivo de averbação
- [Mais detalhes](ssw0304.htm)

#### 090 - DIVERGÊNCIAS DE UNIDADES DO CADASTRO DE CLIENTES
- Alterações frequentes em cadastros (opção 483 e 402) desorganizam unidades
- Alerta diferenças entre Unidade Responsável, Cobrança e Operacional (opção 402)
- [Mais detalhes](ssw0249.htm)

#### 074 - CLIENTES PESSOA JURÍDICA NÃO CONTRIBUINTE
- Pessoas jurídicas cadastradas ontem com IE ISENTO
- Alerta: IE Isento gera frete com alíquota interna
- [Mais detalhes](ssw0758.htm)

---

## Fluxo de Uso

1. Acesse a opção 056
2. Visualize relatórios gerados hoje (principais em vermelho)
3. Para períodos anteriores, use filtros ou "Últimos 7 dias"
4. Clique sobre a linha para abrir relatório
5. Use Excel para exportar, Localizar para buscar, Ajuda (?) para instruções
6. Relatórios MENSAIS acumulam até ontem (dia corrente e anterior disponíveis)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 902 | Libera relatórios ao GRUPO de usuários |
| 300 | Relatórios Pessoais (uso individual, não compartilhado) |
| 918 | Liberação de grupos |
| 144 | Big Brother SSW - cadastra usuários/ações para monitoramento |
| 145 | Big Brother SSW - monitora gerentes (MTZ) |
| 355 | Reimpressão de relatórios (sem recálculo) |

## Observações e Gotchas

### Processamento
- Relatórios processados **diariamente** (alguns de hora-em-hora)
- Disponíveis por até **1 ano**
- Não requer BI, gráficos, planilhas ou "torre de controle"
- Compartilháveis com todas unidades no mesmo formato (acompanhamento sistematizado)

### Permissões
- Cada usuário vê da sua unidade
- MTZ vê de todas com resumos ao final
- Liberação por opção 902 e opção 300

### Ajuda Contextual
- Relatórios possuem Ajuda (?) no cabeçalho superior direito
- Auxilia interpretação e dicas de uso

### Big Brother SSW
- Senhas mudam diariamente nos relatórios vitais
- Gerentes devem informar senhas no Menu Principal
- Sem senha, acesso bloqueado ao restante do SSW
- MTZ monitora via opção 145

### CTRCs Excluídos
- Não considera: cancelados, anulados, de anulação (opção 520), unificadores (opção 172)
- Exceção: alguns relatórios específicos têm regras próprias

### Diferença de Valores
- Opção 455: usa **Valor do Frete** (a receber)
- Situação Geral (056): usa **Base de Cálculo** (dos impostos)
- Podem mostrar valores diferentes

### Disponibilização
- Relatórios mensais: dias 01 e 10 de cada mês (ex: 070, 084, 083)
- CNPJ de cliente: raiz (8 primeiros) considera todos CNPJs dessa raiz
- Período de dados: até meia-noite de ontem

### Modelo de Resultados
- Conceitos: Resultado Comercial, Resultado Real, Desconto sobre NTC
- Configuração: opção 469 (resultados mínimos)
- Visualização por CTRC: opção 101, opção 393

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A06](../pops/POP-A06-cadastrar-custos-comissoes.md) | Cadastrar custos comissoes |
| [POP-B04](../pops/POP-B04-resultado-ctrc.md) | Resultado ctrc |
| [POP-B05](../pops/POP-B05-relatorios-gerenciais.md) | Relatorios gerenciais |
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-E05](../pops/POP-E05-liquidar-fatura.md) | Liquidar fatura |
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
| [POP-G02](../pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist gerenciadora risco |
