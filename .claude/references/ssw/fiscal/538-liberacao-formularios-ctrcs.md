# Opcao 538 — Liberacao de Formularios de CTRCs

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Permite cadastramento de AIDFs (Autorizacao de Impressao de Documentos Fiscais) liberadas e distribuicao dos formularios para filiais e agencias. Controla estoques de formularios de CTRCs por unidade.

## Quando Usar
- Recepcao de lote de formularios de CTRCs da grafica
- Cadastramento de nova AIDF
- Distribuicao de caixas de formularios para unidades emissoras
- Vinculacao de faixas de numeros de controle a caixas

## Pre-requisitos
- AIDF liberada pela SEFAZ
- Lote de formularios recebido da grafica
- Unidades cadastradas (opcao 401)
- Entendimento da estrutura de caixas e faixas de numeros de controle

## Campos / Interface

### Tela Inicial
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| AIDF | Sim* | Informar AIDF ou escolher via link para alteracoes |
| Cadastrar nova AIDF | - | Link para cadastramento de nova AIDF |

*Obrigatorio se for alterar AIDF existente

### Tela de Caixas
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Caixas de Formularios | Sim | Faixas de Numeros de Controle (cada faixa = 1 caixa, sequenciais) |
| Unidade | Sim | Sigla da unidade que recebeu a caixa (MTZ = estoque matriz) |

## Fluxo de Uso
1. Receber lote de formularios da grafica
2. Acessar opcao 538
3. Clicar em "Cadastrar nova AIDF"
4. Informar dados da AIDF
5. Informar caixas de formularios:
   - Faixa de numeros de controle de cada caixa (sequenciais)
   - Unidade destino de cada caixa (MTZ para estoque matriz)
6. Salvar cadastro
7. Informar AIDF em uso pela unidade na opcao 401
8. Acompanhar estoque via opcao 537

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 401 | Informar AIDF em uso pela unidade (OBRIGATORIO) |
| 007 | Impressao de CTRCs (vincula formularios) |
| 537 | Acompanhamento de estoques de formularios |

## Observacoes e Gotchas

### Processo Completo de Controle
1. **Matriz cadastra AIDF**: opcao 538 para cadastrar lote recebido da grafica
2. **Distribuir caixas**: informar unidade destino de cada caixa (faixas sequenciais)
3. **Vincular AIDF na unidade**: opcao 401 OBRIGATORIA para cada unidade emissora
4. **Impressao vincula formularios**: opcao 007 vincula CTRCs a formularios
5. **Acompanhar estoques**: opcao 537 monitora situacao em cada unidade

### AIDF na Unidade (Opcao 401)
- **OBRIGATORIO**: informar AIDF em uso na opcao 401 para cada unidade
- **Sem cadastro = sem AIDF gravada**: se nao informar na opcao 401, AIDF nao sera gravada nos CTRCs (Numero de Controle grava normalmente)
- **Sem validacao**: sem cadastro, sistema nao valida Numero de Controle informado na impressao (opcao 007)
- **Estoque incorreto**: se vinculacao na opcao 401 nao estiver correta, situacao dos estoques (opcao 537) estara errada

### Cadastramento de Caixas
- **Faixas sequenciais**: faixas de numeros de controle devem ser sequenciais
- **Uma faixa = uma caixa**: cada faixa corresponde a uma caixa de formulario
- **MTZ para estoque**: sigla MTZ pode ser usada para controle de estoque da matriz
- **Cadastrar logo**: sugestao e cadastrar TODOS os formularios logo apos recebimento da grafica

### Validacao na Impressao
- Sistema valida Numero de Controle com faixa TOTAL da AIDF (nao por unidade)
- Motivo: podem ocorrer necessidades de impressao de CTRCs de outras unidades
- Validacao so funciona se AIDF estiver cadastrada na unidade (opcao 401)

### Estoque e Reposicao
- Acompanhar estoques via opcao 537
- Monitorar para encomendar novas confeccoes a tempo
- Vinculacao correta na opcao 401 e essencial para estoque correto
