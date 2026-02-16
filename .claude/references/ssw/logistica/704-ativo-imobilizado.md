# Opção 704 — Cadastro do Ativo Imobilizado

> **Módulo**: Logística (Patrimônio/Contabilidade)
> **Páginas de ajuda**: 4 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função

Cadastra bens do ativo imobilizado da empresa (edifícios, máquinas, veículos, equipamentos). Controla depreciação contábil e créditos fiscais de ICMS e PIS/COFINS parcelados conforme legislação.

## Quando Usar

- Aquisição de novo bem destinado ao ativo imobilizado (CFOP 1551/2551)
- Necessidade de controlar depreciação contábil de bens
- Aproveitamento de créditos de ICMS e PIS/COFINS de bens adquiridos
- Controle de localização física de patrimônio
- Geração do Livro CIAP (Controle de Crédito de ICMS do Ativo Permanente)
- Realização de inventário de bens

## Pré-requisitos

- Nota Fiscal do fornecedor com CFOP 1551/2551 (destinado ao ativo imobilizado usado na atividade produtiva)
- Lançamento no Contas a Pagar (opção 475) com item classificado como ativo
- Unidade de aquisição cadastrada (opção 401)
- Fornecedor cadastrado
- Plano de contas contábil configurado (opção 541) para depreciação

## Campos / Interface

### Tela Inicial

**Cadastrar:**
- **Novo imobilizado**: Cadastra novo bem (Número será fornecido ao concluir)
- **Parcelas de depreciação**: Tabela de meses por espécie de bem (quantidade pode ser alterada)

**Consultar:**
- **Número**: Número interno do SSW (gerado automaticamente)
- **Nro identificação**: Etiqueta/código de barras do bem
- **Diversos filtros**: Seleção por múltiplos critérios
- **Termo de responsabilidade**: Documento com bens sob responsabilidade do assinante

### Tela Principal - Dados do Bem

- **Número**: Fornecido após conclusão do cadastro
- **Unid aquisição**: Unidade que adquiriu o bem
- **IE aquisição**: Inscrição Estadual da unidade de aquisição
- **Unid localiz**: Unidade atual do bem (responsável pela posse)
- **Empresa**: Para multiempresa (opção 401)
- **Nro identificação (opc)**: Etiqueta física (código de barras)
- **Setor de localização**: Complemento da unidade de localização
- **Espécie**: Classificação fiscal (define quantidade de meses de depreciação)
- **Tipo do veículo**: Quando espécie for VEÍCULO
- **Placa**: Para veículos
- **Marca, modelo, etc**: Dados descritivos do bem

### Dados do Documento Fiscal

- **CNPJ Fornecedor**: Fornecedor do bem
- **Modelo doc fiscal**: Geralmente 55 (NF-e)
- **Série/Número NF**: Da Nota Fiscal
- **Número sequencial do item**: Item na NF ou DANFE
- **Chave**: Chave da DANFE
- **Num C Pagar**: Número do lançamento no Contas a Pagar (opção 475)
- **Data aquisição**: Inicia contagem de tempo fiscal/contábil
- **Valor da aquisição**: Valor de compra
- **Dif Alíquota**: DIFAL (ICMS devido à UF de destino)
- **Valor contábil**: Valor a ser contabilizado
- **Código da Cta Contábil**: Conta contábil do Ativo (para SPED Fiscal - opção 512)

### Crédito Fiscal - ICMS

- **Credita ICMS**: S-utiliza ICMS para crédito
- **Qtde parcelas para ICMS**: Sugerida pela espécie (padrão 48 meses)
- **ICMS para crédito**: Valor parcelado mensalmente
- **Data baixa ICMS**: Data de finalização do crédito

### Crédito Fiscal - PIS/COFINS

- **Credita PIS/COFINS**: S-utiliza para crédito
- **Qtde parcelas para PIS/COFINS**: Sugerida pela espécie
- **Tipo de crédito PIS/COFINS**: A-data de aquisição, D-parcelas de depreciação
- **Data baixa PIS/COFINS**: Data de finalização do crédito

### Depreciação

- **Qtde parcelas depreciação**: Padrão 48 meses (IN RFB 1.700 - Anexo III, 14/03/2017)

### Links no Rodapé (Após Cadastro)

- **Depreciação contábil**: Altera/exclui parcelas
  - Lançar mensalmente: Valor a partir de mês/ano, X vezes
  - Lançar: Lançamento contábil individual (opção 541)
  - Excluir: Remove parcela com estornos contábeis
- **Ocorrências**: Informações do ativo
- **Duplicar**: Gera novo cadastro com novo Número
- **Excluir**: Remove cadastro do imobilizado
- **Crédito ICMS**: Parcelas para contabilização
- **Crédito PIS/COFINS**: Parcelas para contabilização
- **Baixa imobilizado**: Para bens inativos (gera lançamentos contábeis)
  - Ganho/Perda na alienação (Venda - Depreciação acumulada - Valor ICMS)
  - Ser/Nro NF: NF de venda (opção 551, CFOP 5551/6551)
  - Data alienação: Para lançamentos contábeis
  - Informe conta contábil: Se não vinculado ao Contas a Pagar
  - Estornar baixa: Reverte baixa (bloqueado se NF tiver fatura - opção 547)

## Fluxo de Uso

### Processo Completo de Ativo Imobilizado

```
1. Opção 475 → Contas a Pagar
   - Lançar despesa com CFOP 1551/2551
   - Chamar opção 704 automaticamente (dados pré-preenchidos)

2. Opção 704 → Cadastro do Ativo
   - Complementar dados do bem
   - Configurar créditos de ICMS e PIS/COFINS
   - Definir depreciação

3. Opção 705 → Contabilização da Depreciação (mensal)
   - Lançar parcelas mensais na contabilidade
   - Envolver contas de Ativo e Resultado

4. Opção 706 → Realização do Inventário
   - Controle de localização física
   - Termo de responsabilidade

5. Opção 546 → Emissão do Livro CIAP
   - Controle de Crédito de ICMS do Ativo Permanente

6. Baixa do Ativo (quando vendido/descartado)
   - Opção 551: Emissão de NF de venda (CFOP 5551/6551)
   - Opção 704: Link "Baixa imobilizado"
   - Cálculo de ganho/perda na alienação
```

### Chamada via Contas a Pagar

```
1. Opção 475 → Lançar despesa com CFOP 1551/2551
2. Sistema abre opção 704 automaticamente
3. Campos pré-preenchidos:
   - CNPJ Fornecedor
   - NF (série, número, chave)
   - Num C Pagar
   - Data aquisição
   - Valor da aquisição
   - Valores de ICMS e PIS/COFINS
4. Completar dados complementares (espécie, localização, etc.)
```

## Integração com Outras Opções

### Cadastros e Configuração

- **Opção 401**: Cadastro de unidades (aquisição e localização)
  - Multiempresa
- **Opção 541**: Lançamentos automáticos contábeis
  - Sequências 49-52 e 70: Ativo
  - Sequências 53-56 e 71: Resultado

### Contas a Pagar

- **Opção 475**: Lançamento de despesas
  - CFOP 1551/2551: Chama opção 704 automaticamente
  - Link habilitado apenas para produtos com CFOP Entrada 1551

### Depreciação e Controles

- **Opção 705**: Contabilização da depreciação mensal
  - Depreciação integral do ativo
  - Crédito de ICMS
  - Crédito de PIS/COFINS
  - Lançamento único no mês (não duplica)
- **Opção 706**: Inventário de bens
  - Filtros: unidade aquisição, localização, espécie, período
  - Termo de responsabilidade
  - Etiquetas autoadesivas com código de barras
- **Opção 546**: Livro CIAP (Modelo C)
  - AJUSTE SINIEF 03/01 do CONFAZ
  - Usa coeficiente de creditamento do Livro Fiscal ICMS

### Documentos Fiscais

- **Opção 551**: Emissão de NF de venda (baixa do ativo)
  - CFOP 5551/6551
- **Opção 433**: Livro Fiscal do ICMS
  - Valores de TRIBUTADAS E EXPORTAÇÃO
  - TOTAL DAS SAÍDAS
  - Cálculo do COEFICIENTE DE CREDITAMENTO (para Livro CIAP)
- **Opção 496**: SINTEGRA (informação de créditos parcelados)
- **Opção 512**: SPED Fiscal
  - Regime Débito/Crédito: usa dados do Livro CIAP
  - Regime Crédito Presumido: não usa Livro CIAP
  - Registros específicos de crédito parcelado
- **Opção 515**: SPED PIS/COFINS (créditos parcelados)

### Faturamento

- **Opção 547**: Fatura de NF de venda
  - Bloqueia estorno de baixa se fatura emitida

## Observações e Gotchas

### Objetivos do Sistema

**Contábil:**
- Depreciação lançada como despesa mensal em parcelas
- Aquisição do bem não pode ser diretamente considerada como despesa

**Fiscal:**
- ICMS e PIS/COFINS abatidos (creditados) em parcelas mensais
- Controle conforme legislação vigente

**Propriedade:**
- Controle físico dos bens
- Manutenção da propriedade

### CFOP e Classificação

**CFOP Entrada 1551/2551:**
- "Compra de bem para o ativo imobilizado"
- Produtos destinados ao ativo da empresa
- **Utilizados na atividade produtiva**
- Habilita link para opção 704 no Contas a Pagar (opção 475)

**Espécies de Bens:**
- Define quantidade de meses de depreciação padrão
- Alguns bens não são depreciáveis
- Para VEÍCULO: abre campos adicionais (tipo, placa, marca, modelo)

### Créditos Fiscais

**ICMS:**
- Parcelas normalmente em 48 meses
- Informado em SINTEGRA (opção 496)
- Informado em SPED Fiscal (opção 512)
- Usado no Livro CIAP (opção 546)

**PIS/COFINS:**
- Parcelas conforme espécie do bem
- Tipo A: crédito pela data de aquisição
- Tipo D: crédito de acordo com parcelas de depreciação
- Informado em SPED PIS/COFINS (opção 515)

### Depreciação

**Quantidade de parcelas:**
- Padrão: 48 meses (IN RFB 1.700 - Anexo III)
- Pode ser alterada conforme necessidade
- Sugerida automaticamente pela espécie do bem

**Lançamento contábil:**
- Opção 705: lançamento em lote de todos os bens
- Opção 704: lançamento individual (avulso) por parcela
- **Lançamento único no mês**: parcela já lançada não é relançada
- Envolve contas de Ativo (crédito) e Resultado (débito)

### Baixa do Ativo

**Quando:**
- Venda do bem
- Descarte/sucateamento
- Perda/roubo

**Processo:**
- Emitir NF de venda (opção 551, CFOP 5551/6551)
- Link "Baixa imobilizado" habilitado para inativos
- Sistema calcula ganho/perda: `Venda - Depreciação acumulada - Valor ICMS`
- Data de alienação usada nos lançamentos contábeis

**Estorno de baixa:**
- Possível via link "Estornar baixa"
- **Bloqueado** se NF de venda tiver fatura emitida (opção 547)
- Apenas em domínio com contabilidade habilitada

### Inventário Físico

**Etiquetas:**
- Recomendado usar etiquetas autoadesivas com código de barras
- Vinculadas no campo "Nro identificação"
- Adquiridas pela internet
- Fazem vínculo físico com o ativo

**Realização (opção 706):**
- Filtros múltiplos: unidade, espécie, período
- Termo de responsabilidade impresso
- Identifica bens não localizados (falta/sobra)
- Útil: filtrar por "último inventário" fora do período recente

### Livro CIAP (opção 546)

**Requisitos:**
- Bens cadastrados na opção 704
- Datas de baixa informadas (bens vendidos/baixados antes de 48 meses)
- Depreciação lançada (opção 705)
- Livro Fiscal ICMS gerado (opção 433) para coeficiente de creditamento

**Geração:**
- ANO no formato AAAA
- Inscrição Estadual da unidade adquirente
- Número do livro a ser impresso

**Uso:**
- SPED Fiscal regime Débito/Crédito: usa dados do CIAP
- SPED Fiscal regime Crédito Presumido: não usa CIAP

### Desafio de Implantação

**Maior desafio:**
- Levantamento de dados e documentos de bens antigos
- Todos os campos são necessários para aceitação fiscal
- Nota Fiscal, datas, valores, ICMS, etc.

### Pontos de Atenção

- **Multiempresa**: especificar empresa em todas as operações (opção 401)
- **Conta contábil do Ativo**: necessária para SPED Fiscal (opção 512)
- **Duplicar cadastro**: gera novo Número, útil para bens similares
- **Exclusão**: cuidado com lançamentos contábeis já realizados
- **DIFAL**: informar valor do ICMS devido à UF de destino
- **Parcelas de depreciação**: podem ser alteradas individualmente
- **Lançamento avulso**: possível pela opção 704, mas opção 705 é melhor para lote
- **Termo de responsabilidade**: documento legal assinado pelo responsável
