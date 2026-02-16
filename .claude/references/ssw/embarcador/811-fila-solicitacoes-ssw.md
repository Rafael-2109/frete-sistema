# Opção 811 — Fila de Solicitações (Equipe SSW)

> **Módulo**: Embarcador (Interno SSW)
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Acompanha o trabalho da equipe SSW em homeworking, permitindo cadastro, execução e finalização de solicitações, gerando relatórios diários para cálculo de premiações e PLR.

## Quando Usar
- Para cadastrar novas solicitações de trabalho
- Para executar e finalizar solicitações em andamento
- Para informar férias e ausências justificadas
- Para acompanhar produção da equipe

## Pré-requisitos
- Ser membro da equipe SSW
- Acesso ao sistema SSW

## Conceitos Importantes

### Equipes SSW
- **DEV**: Desenvolvimento (construção e manutenção de programas)
- **EDI**: Equipe EDI
- **SUP**: Suporte aos usuários
- **ASS**: Assessoria (implantação, análise e comercial)

### Horas
Dimensão que mede o esforço necessário para executar a solicitação.

### Validadores
Clientes internos (colaboradores SSW) que validam solicitações finalizadas e atribuem notas:
Hellinton, Katarine, Leandro, Mariana, Sergio, Silvio, Tomio e Weber.

## Campos / Interface

### Tela Cadastrar
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Domínio | Não | Quando solicitação for específica de um domínio |
| Solicitante | Sim | CNPJ ou colaborador SSW |
| Tipo | Sim | P, M, E, S, I, C, A, D, F, J, T, H, R (ver abaixo) |
| Apontar programa | Não | Programa SSW relacionado |
| Solicitação | Sim | Resumo (impresso no relatório 255) |
| Prioridade | Sim | 00 (urgente+importante) a 99 (geladeira) |
| Anexar arquivo | Não | PDF que subsidia a solicitação |
| Observação | Sim | Detalhamento completo |

### Tela Cadastrar 2 (Campos Complementares)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Horas (HHMM) | Sim | Quantidade de horas necessárias |
| Percentual de conclusão | Não | Para Manutenção ou Projeto |
| Executor | Sim | Executor da solicitação |
| Usuário teste | Não | Quem testou (Projeto ou Manutenção) |
| Data de previsão | Não | Previsão de conclusão |

## Tipos de Solicitação

### Exclusivos da Equipe DEV (contabilizam horas)
- **P - Projeto**: Novas funcionalidades para o Sistema SSW
- **M - Manutenção**: Manutenções no Sistema SSW

### Uso Geral (contabilizam horas)
- **E - EDI**: Assunto EDI
- **S - Suporte**: Suporte aos usuários
- **I - Implantação**: Implantação do SSW
- **C - Comercial**: Questões comerciais
- **A - Análise**: Análise de reivindicações de usuários
- **D - Desenvolvimento**: Desenvolvimento que não se enquadra em P ou M
- **F - Férias**: Lançamento diário (8h/dia) de férias
- **J - Ausência justificada**: Ausência amparada por legislação ou autorizada

### Uso Geral (NÃO contabilizam horas do mês)
- **T - Plantão**: Horas de sobreaviso fora do expediente
- **H - Hora Extra 75%**: Atividades fora do expediente (exceto domingos/feriados)
- **R - Hora Extra 100%**: Atividades em domingos e feriados

## Prioridades (Projeto e Manutenção)

| Prioridade | Urgente | Importante |
|------------|---------|------------|
| 00 | X | X |
| 01 | X | |
| 02 | | X |
| 03 | | |
| 99 | geladeira | geladeira |

## Fluxo de Uso

### Cadastrar Solicitação
1. Acessar link "Cadastrar"
2. Informar domínio (se aplicável), solicitante, tipo
3. Apontar programa (opcional)
4. Resumir solicitação
5. Definir prioridade
6. Anexar arquivo (se necessário)
7. Detalhar em observação
8. Clicar em "Incluir"
9. Complementar com horas, executor, data de previsão
10. Clicar em "Iniciar" para começar execução

### Executar Solicitação
1. Link "Iniciar": Informa início da execução
2. Link "Observações": Complementar dados durante execução
3. Link "Pausar": Pausar temporariamente
4. Link "Finalizar": Concluir execução (inabilita todos os links)

### Funcionalidades Adicionais
- **Duplicar**: Duplica solicitação para mês seguinte
- **Excluir**: Exclui solicitação não iniciada
- **Validar**: Validadores validam dados de solicitações finalizadas
- **Restaurar**: Solicitação finalizada pode ser restaurada

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 056 (Rel. 255) | PLR SSW - usa dados para cálculo de premiação mensal e PLR anual |
| 056 (Rel. 252) | Produção da Equipe SSW (sendo substituído pelo 255 a partir de 01/01/2024) |
| 056 (Rel. 254) | Padrinhos dos programas SSW (sem relação com opção 811) |
| 813 | Avaliação da Equipe SSW - notas mensais que complementam cálculo de premiação |

## Observações e Gotchas

### Tipos de Horas
**Horas contabilizadas no mês** (relatório 255):
- Total de tipos: P, M, E, S, I, C, A, D
- Horas de F (férias) e J (ausências justificadas) também são consideradas
- Excluídas: T (plantão), H (hora extra 75%), R (hora extra 100%)

**Horas extras 75%** (tipo H):
- Executadas em dias da semana e sábados
- Incluem horas excedentes em relação às horas de trabalho no mês

**Horas extras 100%** (tipo R):
- Executadas em domingos e feriados

**Horas plantão** (tipo T):
- Tempo de sobre aviso
- Quando trabalho inicia, passar para H ou R (não mais T)

### Férias e Ausências
- **Férias (F)**: Lançamento diário de 8h/dia
- **Ausências justificadas (J)**: Garantidas por legislação ou autorizadas pela administração
- Ambas compõem as horas de execução do mês

### Relatórios Diários (Opção 056)
1. **252 - Produção da Equipe SSW**: Substituído pelo 255 a partir de 01/01/2024
2. **255 - PLR SSW**: Cálculo de premiações mensais e PLR anual
3. **254 - Padrinhos dos programas SSW**: Responsáveis pelos programas (sem relação com opção 811)

### Cálculo de Premiação Mensal
- 1% das liquidações menos impostos
- Dividido para equipes e depois aos remadores
- Proporcional às notas recebidas via dois processos:
  - Opção 813: Notas mensais (1 a 10) atribuídas pelos remadores
  - Notas dos clientes internos: Participantes de reunião semanal

### PLR Anual
- Meio salário base
- Aplicação das notas obtidas ao longo do ano anterior
- Pagamento em janeiro

### Validação
- Validadores validam horas de solicitações finalizadas
- Somente horas validadas são consideradas nos relatórios

### PCT (Percentual)
TOTAL HORAS sobre Total de Horas de Trabalho do mês (contratadas).

### Campos do Relatório 255
- **Total Horas**: Solicitações finalizadas e validadas (exceto T, H, R) + F + J
- **Horas Extras 75%**: Tipo H + horas excedentes
- **Horas Extras 100%**: Tipo R (domingos e feriados)
- **Horas Plantão (T)**: Sobre aviso
- **Horas Justificadas**: Ausências garantidas/autorizadas

### Observação Importante
- Além das solicitações ligadas às atividades, devem ser informadas **férias** e **ausências justificadas** para compor as horas de execução do mês
- Não compõem as horas do mês: **plantão** e **horas extras**
