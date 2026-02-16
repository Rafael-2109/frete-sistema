# Opção 587 — Gera Arquivo SPED EFD Reinf (Atualizada)

> **Módulo**: Financeiro/Fiscal
> **Páginas de ajuda**: 1 página consolidada (referência da opção 574 desatualizada)
> **Atualizado em**: 2026-02-15

## Função
Gerar arquivo SPED EFD Reinf para envio à Receita Federal via webservice em complemento ao e-Social, contemplando retenções de INSS e Previdência Social de Pessoas Jurídicas.

## Quando Usar
Necessário mensalmente para:
- Transmitir informações de retenções tributárias (INSS, Previdência Social) à Receita Federal
- Complementar obrigações do e-Social
- Atender exigências fiscais federais relacionadas a despesas e receitas com PJ

## Pré-requisitos
- Despesas com PJ lançadas no Contas a Pagar (opção 475) com retenções de INSS e/ou Previdência Social
- Receitas com PJ lançadas (opção 733) com retenções, apenas RPSs
- Eventos (opção 503) com classificações dos serviços prestados devidamente vinculadas (obrigatório para geração do arquivo)
- Certificado digital configurado para transmissão via webservice
- Dados do informante (contador) cadastrados

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ da empresa | Sim | CNPJ da matriz |
| Mês/Ano de referência | Sim | Mês/Ano de apuração |
| Outras receitas tributadas | Não | Valor de outras receitas tributadas pela CPRB — somado às receitas operacionais |
| Valor exclusões | Não | Valores a serem excluídos da contribuição previdenciária |
| Arquivo prévio | Não | Gera arquivo de conferência mostrando erros e resumo ANTES do envio definitivo |
| Comprovante de envio | Não | Gera arquivo com informações enviadas e respectivos Recibos |
| Dados do informante | Sim | Informante (geralmente o contador) |

## Fluxo de Uso

### Preparação (executar uma vez)
1. Cadastrar eventos (opção 503) com classificações dos serviços prestados vinculadas
2. Configurar dados do informante (contador)
3. Configurar certificado digital para webservice

### Processamento mensal
4. Lançar despesas com PJ no Contas a Pagar (opção 475) com retenções de INSS/Previdência Social
5. Lançar receitas com PJ (opção 733) com retenções, apenas RPSs
6. Acessar opção 587
7. Informar CNPJ da matriz e Mês/Ano de referência
8. Informar "Outras receitas tributadas" e "Valor exclusões" (se aplicável)
9. **RECOMENDADO**: Marcar "Arquivo prévio" para conferência
10. Verificar erros e resumo de valores no arquivo prévio
11. Se houver erros: corrigir despesas (opção 475) nos dados fiscais e repetir geração
12. Desmarcar "Arquivo prévio" e marcar "Comprovante de envio"
13. Confirmar — sistema transmite via webservice à Receita Federal
14. Recibo de comprovação do envio é fornecido ao final da transmissão
15. Arquivar comprovante de envio

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 475 | Contas a Pagar — despesas com PJ e retenções de INSS/Previdência Social (Evento R-2010) |
| 733 | Receitas com PJ — retenções de INSS/Previdência Social, apenas RPSs (Evento R2020) |
| 503 | Eventos — classificações dos serviços prestados vinculadas (obrigatório) |
| 515 | SPED PIS/COFINS — valor total da receita mensal (mesmo enviado no bloco P, Evento R2060) |
| 489 | Relação de retenções de PF — para envio à contabilidade (e-Social, NÃO gerado pelo SSW) |
| 574 | Opção DESATUALIZADA — usar opção 587 (esta) |

## Observações e Gotchas

- **Opção 587 é a ATUALIZADA**: Opção 574 está desatualizada — SEMPRE usar opção 587

- **Envio online via webservice**: Transmissão ocorre de forma online — ao final é fornecido Recibo de comprovação do envio

- **Classificação de serviços obrigatória**: Eventos (opção 503) DEVEM ter classificações dos serviços prestados vinculadas — SEM isso o arquivo Reinf NÃO é gerado

- **Escopo da versão atual**:
  - **Evento R-2010**: Despesas (opção 475) com retenções de INSS/Previdência Social, apenas modelo 99 (Nota Fiscais de Serviços)
  - **Evento R2020**: Receitas (opção 733) com retenções de INSS/Previdência Social, apenas RPSs
  - **Evento R2060**: Valor total da receita mensal (mesmo enviado no SPED PIS/COFINS, opção 515, bloco P)
  - **Evento R-2070**: Futura implementação pelo SEFAZ — retenções de IR, CSLL, PIS e COFINS

- **Pessoas Físicas**: Retenções de PF são tratadas via e-Social (NÃO gerado pelo SSW). Relação pode ser obtida pela opção 489 e encaminhada à Contabilidade

- **Arquivo prévio**: SEMPRE gerar arquivo prévio para conferência ANTES do envio definitivo — permite identificar erros e corrigir despesas (opção 475)

- **Correções**: Se houver erros, corrigir nos dados fiscais das despesas (opção 475) e **reenviar** o SPED EFD Reinf pela opção 587 — sistema permite reenvio

- **Outras receitas tributadas**: Campo permite incluir receitas tributadas pela CPRB não capturadas automaticamente — são somadas às receitas operacionais

- **Valor exclusões**: Campo permite excluir valores da contribuição previdenciária conforme legislação

- **Comprovante de envio**: Gera arquivo com informações enviadas e Recibos — OBRIGATÓRIO arquivar para auditoria fiscal

- **SPED PIS/COFINS**: Valor total da receita mensal (Evento R2060) é o mesmo já enviado no SPED PIS/COFINS (opção 515) no bloco P — sistema usa mesma base de dados
