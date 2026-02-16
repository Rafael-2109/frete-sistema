# Opção 404 — Cadastro de Setores de Coleta/Entrega

> **Módulo**: Cadastros
> **Páginas de ajuda**: 3 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Cadastra setores de coleta e entrega dentro de cidades atendidas pela transportadora. Setores permitem diferenciar remunerações de veículos, filtrar relatórios e organizar operações em função de distâncias e dificuldades operacionais.

## Quando Usar
- Dividir cidade em setores para diferenciação de remuneração de agregados
- Configurar Taxa de Difícil Acesso (TDA) específica por faixa de CEP
- Organizar relatórios de volumes expedidos/recebidos por setor
- Filtrar coletas e entregas por região da cidade
- Definir remuneração diferenciada por setor na opção 409

## Pré-requisitos
- Opção 401: Cadastro de unidades
- Opção 402: Cidades atendidas (a cidade deve estar cadastrada)
- Opção 405: Cadastro de ocorrências (para definir quais ocorrências remuneram agregado)
- Opção 409: Tabela de remuneração de veículos (para usar setores na remuneração)

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Cidade/UF | Sim | Cidade que terá setores definidos |
| Código do Setor | Sim | Código numérico do setor (999 = setor padrão para CEPs não setorizados) |
| Descrição | Sim | Nome ou descrição do setor |
| Faixas de CEP | Sim | Faixas de CEP que compõem o setor (CEP inicial - CEP final) |
| Valor TDA | Não | Taxa de Difícil Acesso em R$ específica do setor (prioridade sobre opção 402 e 423) |

## Fluxo de Uso

### Cadastrar Setores em uma Cidade
1. Acessar opção 404
2. Selecionar cidade
3. Criar novo setor (informar código e descrição)
4. Definir faixas de CEP que compõem o setor
5. Configurar valor TDA (se aplicável)
6. Salvar setor

### Usar Setores na Remuneração de Agregados
1. Cadastrar setores na opção 404
2. Configurar ocorrências que remuneram na opção 405
3. Cadastrar tabela de remuneração na opção 409
4. Na tabela (opção 409), definir valores diferenciados por setor:
   - Diária por setor
   - Mínimo por setor
   - Valor sobre E/C (Eventos/Clientes) por setor
   - **Setor 999**: valores usados para CEPs não setorizados ou setores sem valor cadastrado

### Filtrar Relatórios por Setor
- Opção 050: Relatório de coletas (filtro por setor)
- Opção 058: Volumes expedidos por cidade (subtotais por setor)
- Opção 059: Volumes recebidos por cidade (subtotais por setor)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 050 | Relatório de coletas (filtro por setor) |
| 058 | Volumes expedidos por cidade (mostra subtotais por setor) |
| 059 | Volumes recebidos por cidade (mostra subtotais por setor) |
| 076 | Demonstrativo de remuneração (usa setores no cálculo) |
| 401 | Cadastro de unidades |
| 402 | Cidades atendidas (TDA da opção 404 tem prioridade sobre 402) |
| 405 | Ocorrências (define quais remuneram agregado) |
| 409 | Tabela de remuneração de veículos (usa setores para cálculo) |
| 423 | Tabela de fretes por cliente (TDA da opção 404 tem prioridade sobre 423 quando aplicável) |

## Observações e Gotchas

### Setor 999 (Padrão)
- Valores do setor 999 são utilizados para:
  - CEPs não setorizados na cidade
  - Setores que não possuem nenhum valor cadastrado na tabela de remuneração
- É recomendável sempre configurar valores para o setor 999

### Faixas de CEP
- Não pode haver sobreposição de faixas de CEP entre setores
- CEPs não incluídos em nenhuma faixa usam valores do setor 999
- Faixas devem ser definidas com CEP inicial e CEP final

### Remuneração por Setor (opção 409)
- O cálculo ocorre por setor de forma individualizada
- Setores sem valor cadastrado usam valores do setor 999
- Tipos de valores diferenciáveis por setor:
  - **Diária**: Valor fixo diário por setor
  - **Mínimo**: Valor mínimo garantido por setor
  - **Valor sobre E/C**: Valor por evento ou cliente (faixas progressivas)

### Taxa de Difícil Acesso (TDA)
- **Ordem de prioridade**: opção 404 (setor/CEP) > opção 423 (cliente) > opção 402 (cidade)
- TDA do setor só se aplica se o CEP da coleta/entrega estiver na faixa do setor
- Permite cobrar TDA diferenciada para regiões mais difíceis dentro da mesma cidade

### Relatórios
- Cidades com setores configurados terão subtotais por setor em relatórios gerenciais
- Filtro por setor permite análise mais granular da operação
- Útil para identificar setores com melhor/pior desempenho

### CTRCs Unitizados
- Em operações de Marketplace, onde vários CTRCs são unitizados (opção 101/DANFES/NR/NR Unitizador), o cálculo de remuneração soma dados de todos os CTRCs unitizados e distribui linearmente

### Unidades do Mesmo Armazém
- CTRCs de unidades do mesmo armazém (opção 431) são reconhecidos para emissão num mesmo demonstrativo
- Todo o processo (opções 409, 076, 075) deve ser executado na mesma unidade

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
