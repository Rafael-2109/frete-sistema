# Opção 590 — Gerar Arquivo DIRF (Declaração do Imposto de Renda Retido na Fonte)

> **Módulo**: Financeiro/Fiscal
> **Páginas de ajuda**: 1 página consolidada (referência da opção 490 relacionada)
> **Atualizado em**: 2026-02-15

## Função
Gerar arquivo DIRF utilizando software oficial da Receita Federal para declarar rendimentos pagos e impostos retidos na fonte (alternativa à opção 490 que gera comprovantes sem o software da RF).

## Quando Usar
Necessário anualmente para:
- Cumprir obrigação fiscal de declarar rendimentos pagos a Pessoas Físicas e Jurídicas
- Informar à Receita Federal valores de impostos retidos na fonte (IR, INSS, etc.)
- Gerar arquivo DIRF para envio oficial ao Fisco
- Permitir que Pessoas Físicas (proprietários de veículos, prestadores) declarem seus rendimentos ao IR

## Pré-requisitos
- CTRBs emitidos durante o ano de referência
- Retenções efetuadas nas despesas (PF e PJ) cadastradas no sistema
- Software DIRF da Receita Federal instalado (para opção 590)
- Dados dos proprietários/fornecedores cadastrados (CPF/CNPJ, endereço)

## Campos / Interface

### Opção 490 (Comprovante DIRF sem software RF)

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Ano de referência | Sim | Ano de emissão dos CTRBs |
| Pessoa | Sim | **F** (física) ou **J** (jurídica) |
| CNPJ do proprietário | Não | CNPJ do proprietário do veículo — se não informado, considera todos |
| Gerar etiquetas | Não | Gera etiquetas com endereço do proprietário para envio por Correios |

### Opção 590 (Arquivo DIRF oficial)

Campos não especificados na documentação disponível — interface gera arquivo para importação no software oficial da Receita Federal.

## Fluxo de Uso

### Preparação anual
1. Garantir que todos CTRBs do ano foram emitidos
2. Verificar retenções efetuadas nas despesas (opção 489 para PF, opção 544 para PJ)
3. Conferir dados cadastrais de proprietários/fornecedores (CPF/CNPJ, endereço)

### Geração de arquivo DIRF (opção 590)
4. Acessar opção 590
5. Informar ano de referência
6. Confirmar — sistema gera arquivo DIRF
7. Importar arquivo no software oficial da Receita Federal
8. Validar e transmitir DIRF pelo software da RF

### Geração de comprovantes alternativos (opção 490)
9. Acessar opção 490
10. Informar ano de referência, tipo de pessoa (F ou J)
11. Filtrar por CNPJ de proprietário (se desejado)
12. Marcar "Gerar etiquetas" (se for enviar por Correios)
13. Gerar comprovantes
14. Imprimir e enviar aos proprietários/prestadores

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 490 | Comprovante DIRF sem software RF — alternativa para gerar comprovantes impressos |
| 599 | Gera arquivo DIRF (documentação indica como relacionada à opção 490) |
| 489 | Relatório de CTRBs emitidos — usado para preenchimento de guias de recolhimento (PF) |
| 544 | Relatório de retenções efetuadas nas despesas (PJ) |
| 151 | Comprovante Anual de Rendimentos e Retenções de IR na fonte (PJ) |

## Observações e Gotchas

- **Opção 590 vs 490**:
  - **590**: Gera arquivo DIRF para importação no software oficial da Receita Federal (obrigatório para transmissão ao Fisco)
  - **490**: Gera comprovantes impressos DIRF sem uso do software da RF (alternativa para entregar aos proprietários)

- **Uso combinado recomendado**:
  1. Usar **opção 590** para gerar arquivo oficial e transmitir DIRF ao Fisco
  2. Usar **opção 490** para gerar comprovantes impressos e enviar aos proprietários

- **Etiquetas para Correios**: Opção 490 oferece geração de etiquetas com endereço do proprietário — útil para envio em lote de comprovantes

- **Pessoas Físicas**: Proprietários de veículos (PF) precisam receber comprovantes para declarar rendimentos no IRPF — usar opção 490 para gerar e enviar

- **Pessoas Jurídicas**: Fornecedores PJ também recebem comprovantes — opção 151 oferece formato específico para PJ

- **Validação antes de transmitir**: Conferir relatórios de retenções (opção 489 para PF, 544 para PJ) ANTES de gerar arquivo DIRF — corrigir inconsistências evita retificações

- **Guias de recolhimento**: Opção 489 gera relatório de CTRBs emitidos usado para preencher guias de recolhimento das retenções — conferir antes de gerar DIRF

- **Prazo de entrega**: DIRF tem prazo legal de entrega (geralmente último dia útil de fevereiro) — planejar geração com antecedência

- **Retificação**: Se houver erros após transmissão, será necessário gerar DIRF retificadora — manter backup dos arquivos originais
