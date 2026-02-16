# Opção 442 — Solicitar Crédito/Débito em CTRC/Fatura

> **Módulo**: Financeiro
> **Páginas de ajuda**: 3 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Cadastra créditos e débitos adicionais em CTRCs e faturas, permitindo ajustes financeiros pós-emissão. Suporta aprovação centralizada e integra automaticamente com liquidações e próximo faturamento.

## Quando Usar
- Ajustes financeiros em CTRCs já emitidos
- Lançamento de descontos ou acréscimos em faturas
- Correção de valores sem alterar documento fiscal
- Adicionais que serão incluídos no próximo faturamento

## Pré-requisitos
- CTRC ou fatura emitidos
- Usuário com permissão de acesso (opção 918)
- Aprovação centralizada ativada (opcional, opção 903/Cobrança)

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Empresa** | Não | Escolha quando multiempresa ativada |
| **CTRC** | Condicional | Número do CTRC (com DV) para lançar adicional |
| **Fatura** | Condicional | Número da fatura para lançar adicional |
| **Valor** | Sim | Valor do crédito ou débito |
| **Tipo** | Sim | Crédito (reduz valor) ou Débito (aumenta valor) |
| **Justificativa** | Sim | Motivo do lançamento |

## Abas / Sub-telas

**Cadastrar crédito/débito:**
- CTRC ou Fatura
- Valor e tipo
- Justificativa

**Situação:**
- Lista todos créditos/débitos lançados
- Filtros: Emissão CT-e/fatura, Data crédito/débito
- Exportação para Excel

## Fluxo de Uso

### Lançar Adicional
1. Acessar opção 442
2. Informar CTRC ou Fatura
3. Informar valor e tipo (crédito/débito)
4. Informar justificativa
5. Confirmar lançamento
6. Se aprovação centralizada ativa:
   - Aguardar aprovação (opção 527)
7. Adicional incluído automaticamente em:
   - Próximo faturamento (opção 436, 437)
   - Liquidação (opção 048 CTRC, opção 457 fatura)

### Consultar Situação
1. Acessar link "Situação"
2. Informar período (opcional)
3. Gerar relatório Excel
4. Verificar colunas:
   - CT-E/FATURA ORI: Documento origem
   - CT-E/FATURA DES: Documento que assumiu adicional
   - USUARIO EMIT: Quem emitiu documento
   - USUARIO CRE/DEB: Quem lançou adicional

### Excluir Adicional
1. Acessar opção 459
2. Filtrar adicionais disponíveis
3. Selecionar para exclusão
4. Confirmar exclusão

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 048 | Liquidação de CTRCs (reconhece créditos/débitos) |
| 101 | Consulta CTRC (ocorrências mostram status aprovação) |
| 104 | Consulta fatura (ocorrências mostram status aprovação) |
| 384 | Separação de adicionais em fatura (configuração cliente) |
| 436 | Faturamento geral (inclui adicionais automaticamente) |
| 437 | Faturamento manual (pode apontar adicionais) |
| 457 | Controle de faturas (lançar e liquidar com adicionais) |
| 459 | Relaciona adicionais disponíveis para faturar |
| 527 | Aprovação centralizada de crédito/débito |
| 903 | Ativa aprovação centralizada (Cobrança) |
| 918 | Controle de acesso de usuários |

## Observações e Gotchas

- **Acesso restrito**: Usuários precisam permissão (opção 918)
- **Aprovação centralizada**:
  - Ativar via opção 903/Cobrança
  - Aprovar via opção 527
  - Consultar resultado em ocorrências (opção 101/104)
- **Inclusão automática**: Adicionais incluídos automaticamente no próximo faturamento
- **Faturamento automático**: Adicionais considerados mesmo que CTRC/fatura já faturados ou liquidados
- **Separação**: Cliente pode ter configuração para separar adicionais em fatura própria (opção 384)
- **Crédito**: Reduz valor da fatura/CTRC
- **Débito**: Aumenta valor da fatura/CTRC
- **Liquidação**: Opções 048 (CTRC) e 457 (fatura) reconhecem adicionais automaticamente
- **Rastreamento**: Relatório Excel mostra origem e destino dos adicionais
- **Exclusão**: Via opção 459 antes do faturamento
- **Fatura grande**: Adicionais excessivos podem impedir geração (crédito > frete)

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-E06](../pops/POP-E06-manutencao-faturas.md) | Manutencao faturas |
