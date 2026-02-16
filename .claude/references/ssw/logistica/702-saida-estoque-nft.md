# Opção 702 — Saída de Estoque e Emissão de NF de Transferência

> **Módulo**: Logística/Armazém Geral
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função
Dar saída de produtos do estoque e emitir Notas Fiscais de Transferência (NFT) correspondentes, diferenciando operações de Armazém Geral (NFT obrigatória) e Operador Logístico (usa NF de entrada).

## Quando Usar
Necessário para:
- **Armazém Geral**: Emitir NFT para saída de produtos (cliente vende e transportadora transfere estoque)
- **Operador Logístico**: Dar saída usando mesma NF de entrada (sem emissão de NFT)
- Movimentar estoque de produtos de clientes consignatários
- Gerar NFT para posterior autorização no SEFAZ (opção 707)

## Pré-requisitos
- Produtos cadastrados (opção 741)
- Entrada de produtos no estoque realizada (opção 701)
- Cliente consignatário cadastrado (opção 483)
- **Armazém Geral**: NF de venda do cliente (para emitir NFT correspondente)
- **Operador Logístico**: NF de entrada do estoque (para dar saída)
- Certificado digital configurado (para autorização SEFAZ via opção 707)

## Campos / Interface

### Tela — Saída de Estoque

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ Consignatário | Sim | CNPJ do cliente proprietário dos produtos |
| Tipo de operação | Sim | **Armazém Geral** (emite NFT) ou **Operador Logístico** (usa NF entrada) |
| Código do produto | Sim | Código cadastrado na opção 741 |
| Quantidade | Sim | Quantidade de volumes a dar saída |
| NF de venda (AG) | Condicional | Número da NF de venda do cliente (Armazém Geral) |
| NF de entrada (OL) | Condicional | Número da NF de entrada (Operador Logístico) |

### Tela — Dados da NFT (apenas Armazém Geral)

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Descrição mercadoria | Sim | Preenchido automaticamente da opção 741 |
| NCM/SH | Sim | Nomenclatura Comum do Mercosul (opção 741) |
| CEST | Condicional | Código de substituição tributária (se aplicável) |
| Código Benefício Fiscal | Não | Código de 8 dígitos para operações com benefício fiscal |
| Custo unitário | Sim | Valor unitário médio do saldo atual |
| GTIN | Não | Código GS1 (se aplicável) |
| Origem da mercadoria | Sim | Nacional ou estrangeira (opção 741) |
| CST | Sim | Código de Situação Tributária de ICMS (opção 741) |
| CST IBS/CBS | Não | Código ST do IBS e CBS |
| Classificação Tributária IBS/CBS | Não | Código de Classificação Tributária |

## Fluxo de Uso

### Armazém Geral — Emitir NFT
1. Cliente vende produtos e informa transportadora
2. Acessar opção 702
3. Informar CNPJ consignatário e selecionar "Armazém Geral"
4. Informar código do produto e quantidade
5. Informar número da NF de venda do cliente
6. Sistema preenche dados fiscais automaticamente (opção 741)
7. Revisar dados e confirmar
8. NFT é gerada com status "DIGITADOS"
9. Acessar opção 707 para enviar NFT ao SEFAZ
10. Aguardar autorização (status "AUTORIZADAS")
11. Imprimir DANFE da NFT (opção 707)
12. Saída do estoque é efetivada

### Operador Logístico — Saída sem NFT
1. Acessar opção 702
2. Informar CNPJ consignatário e selecionar "Operador Logístico"
3. Informar código do produto e quantidade
4. Informar número da NF de entrada original
5. Confirmar — saída é dada usando mesma NF de entrada
6. Não há emissão de NFT nem envio ao SEFAZ

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 701 | Entrada de produtos no estoque — necessária antes da saída |
| 741 | Cadastro de mercadorias — fonte de dados fiscais para NFT |
| 707 | Autorização de NFT — envia NFT geradas pela opção 702 ao SEFAZ |
| 734 | Consulta de NFTs — permite consultar número da NFT para reimpressão |
| 733 | Cobrança de serviço de armazenagem — RPS para faturar cliente |
| 009 | Cobrança alternativa de armazenagem |

## Observações e Gotchas

- **Armazém Geral vs Operador Logístico**:
  - **Armazém Geral**: Saída com NF de venda do cliente → emite NFT correspondente → autoriza SEFAZ (707)
  - **Operador Logístico**: Saída com mesma NF de entrada → NÃO emite NFT

- **Fluxo completo para Armazém Geral**:
  1. Opção 701: Entrada (NF cliente transfere para estoque)
  2. **Opção 702**: Saída (NF venda cliente → emite NFT)
  3. Opção 707: Autorização NFT no SEFAZ

- **Cadastro automático de produtos**: Ao importar XML de NF-e pela opção 701, produtos são cadastrados automaticamente na opção 741 — dados fiscais ficam salvos para uso na NFT

- **Dados fiscais da NFT**: Preenchidos automaticamente da opção 741 (origem, CST, NCM/SH, CEST, etc.) — revisar antes de confirmar

- **Custo unitário**: Sistema grava valor unitário **médio do saldo atual** — não é o custo original de entrada

- **Status da NFT (opção 707)**:
  - **DIGITADOS**: NFT geradas pela 702, ainda não enviadas ao SEFAZ
  - **ENVIADOS À RECEITA**: Enviadas mas ainda não autorizadas
  - **AUTORIZADAS (SEM IMPRESSÃO)**: Prontas para impressão
  - **REJEITADOS**: Rejeitadas pelo SEFAZ — clicar para ver motivo
  - **DENEGADOS**: Denegadas por irregularidade fiscal
  - **EM ALTERAÇÃO**: Em edição no momento

- **Reimpressão de NFT**: Usar opção 707 com faixa de NFTs — número da NFT é impresso na parte inferior esquerda da DANFE (consultar opção 734)

- **M2 Empilhado (opção 741)**: Área reduzida ocupada por volume quando empilhamento é possível
  - Exemplo: 1 volume = 1,2 m² → empilhamento de 5 = 1,2/5 = 0,24 m² empilhado
  - 100 volumes = 100 × 0,24 = 24 m² (área com empilhamento)

- **CEST obrigatório**: Apenas para produtos NCM/SH sujeitos a substituição tributária — consultar Tabela CEST no Portal Nacional da NF-e

- **Código Benefício Fiscal**: 8 dígitos para operações com benefício — usar Tabela de Código de Produtos da ANP (Portal Nacional da NF-e)

- **GTIN**: Código GS1 controlado pela Receita Federal — opcional, mas obrigatório se produto possui

- **Endereçamento**: Campo "Endereço" na opção 741 permite localizar item no armazém (rua, número, andar, etc.) — todo armazém deve estar identificado

- **FIFO**: Campo existe na opção 741 mas **ainda sem uso no SSW** — reservado para implementação futura

- **Prazo de validade**: Campo existe na opção 741 mas **ainda sem uso no SSW**
