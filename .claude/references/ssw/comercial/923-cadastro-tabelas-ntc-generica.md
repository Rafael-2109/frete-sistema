# Opção 923 — Cadastro das Tabelas NTC e Genérica

> **Módulo**: Comercial
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função
Cadastrar Tabela NTC (referência para desconto) e Tabela Genérica (utilizada para cálculo de frete como última alternativa), definindo generalidades, tarifas por faixa de peso/distância e ad valorem.

## Quando Usar
Necessário para:
- Definir tabela de referência para todos os fretes emitidos (indicador "Desconto sobre a NTC")
- Estabelecer tabela genérica como fallback para cálculo de frete quando cliente não possui tabela específica
- Configurar generalidades (Despacho, ITR, CAT, GRIS, TDE)
- Definir tarifas por faixa de distância (Km) e peso (Kg)

## Pré-requisitos
- Conhecimento dos valores praticáveis pela transportadora (não são valores oficiais NTC — apenas formato)
- Opção 903/Frete configurada (pedágio)
- Opção 530 configurada (TRT Geral)
- Opção 402 configurada (TDA por cidade)

## Campos / Interface

### Tela Inicial — Generalidades

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Despacho | Sim | Valor da generalidade Despacho |
| ITR | Sim | Valor da generalidade ITR |
| CAT | Sim | Valor da generalidade CAT |
| GRIS | Sim | Valor da generalidade GRIS |
| TDE | Sim | Taxa de Dificuldade de Entrega — NÃO compõe Tabela NTC, mas é usada pela Tabela Genérica |

### Tela Tarifas

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Tarifa | Sim | Número da tarifa (corresponde a faixa de Km) |
| Faixa de Km | Sim | Limite superior da faixa de distância para esta tarifa |
| Até Kg | Sim | Valor a ser cobrado para cada faixa de peso disponível (múltiplas faixas) |
| Acima/ton | Sim | Valor por tonelada quando peso ultrapassar a última faixa — cobrado sobre peso total |
| Advalor | Sim | Percentual a ser cobrado sobre valor da mercadoria |

## Fluxo de Uso

### Configuração inicial
1. Acessar opção 923
2. Cadastrar generalidades na tela inicial:
   - Despacho, ITR, CAT, GRIS, TDE
3. Avançar para tela de Tarifas
4. Para cada tarifa (faixa de Km):
   - Definir limite superior da faixa de distância
   - Cadastrar valores para faixas de peso ("Até Kg")
   - Informar "Acima/ton" (valor por tonelada acima da última faixa)
   - Informar "Advalor" (percentual sobre valor da mercadoria)
5. Salvar — tabela fica disponível para cálculo de frete e referência

### Consulta e impressão (opção 427)
6. Acessar opção 427
7. Visualizar generalidades cadastradas
8. Clicar "Continuar" para ver valores por faixas de peso × distância e AD VALOR
9. Clicar "Imprimir" para gerar relatório da tabela

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 427 | Consulta de Tabela NTC — visualiza e imprime tabela cadastrada na 923 |
| 903/Frete | Pedágio — parcela adicional usada pela Tabela Genérica |
| 530 | TRT Geral — parcela adicional usada pela Tabela Genérica |
| 402 | TDA por cidade — parcela adicional usada pela Tabela Genérica |
| 406 | Densidade (cubagem) — se configurada com "S" em Calcula Frete, tem prioridade sobre densidade padrão 300Kg/m³ |
| 423 | Densidade — NÃO é considerada pela Tabela Genérica (usar opção 406) |

## Observações e Gotchas

- **Tabela NTC vs Tabela Genérica**:
  - **Tabela NTC**: Cadastrada por esta opção, usada como **referência** para indicador "Desconto sobre a NTC" em todos os fretes
  - **Tabela Genérica**: Tabela NTC + parcelas adicionais (Pedágio, TDE, TRT Geral, TDA) — usada para **cálculo de frete** como última alternativa

- **IMPORTANTE — Valores definidos pela transportadora**: Os valores são definidos pela própria transportadora e devem ser praticáveis. **Apenas o formato é da NTC** — não são valores oficiais da Tabela NTC

- **Hierarquia de cálculo de frete**: Tabela Genérica é usada como **última alternativa** quando cliente não possui tabela específica — consultar "Visão Geral/Comercial" para entender fluxo completo

- **Parcelas da Tabela Genérica**:
  1. Valores da Tabela NTC (generalidades + tarifas)
  2. **+** Pedágio (opção 903/Frete)
  3. **+** TDE (cadastrado nesta opção 923, mas não compõe Tabela NTC)
  4. **+** TRT Geral (opção 530)
  5. **+** TDA (opção 402)
  6. **+** Imposto Repassado (até domínio 1031, ano 2012)

- **TDE**: Cadastrada na tela de generalidades mas **NÃO compõe a Tabela NTC** — é usada apenas pela Tabela Genérica

- **Densidade (cubagem)**:
  - **Padrão**: 300Kg/m³ na Tabela Genérica
  - **Prioridade 1**: Densidade configurada na opção 406 com "S" em Calcula Frete
  - **NÃO considerada**: Densidade da opção 423

- **Acima/ton**: Valor por tonelada é cobrado sobre **peso total da mercadoria** quando peso ultrapassar a última faixa cadastrada — não é proporcional

- **Advalor**: Percentual aplicado sobre valor da mercadoria — formato percentual (ex: 0,5 para 0,5%)

- **Tarifas por faixa de Km**: Cada tarifa corresponde a uma faixa de distância — cadastrar limites superiores crescentes (ex: Tarifa 1 até 100Km, Tarifa 2 até 200Km, etc.)

- **Faixas de peso**: Para cada tarifa, múltiplas faixas de peso podem ser cadastradas com valores diferentes — sistema escolhe valor correspondente ao peso da carga

- **Consulta via opção 427**: Permite visualizar tabela cadastrada e gerar relatório — útil para conferência e envio a clientes

- **Generalidades**: Despacho, ITR, CAT e GRIS são parcelas fixas somadas ao frete calculado — TDE é específica para entregas difíceis

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
| [POP-A07](../pops/POP-A07-cadastrar-tabelas-preco.md) | Cadastrar tabelas preco |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
