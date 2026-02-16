# Opção 944 — Manutenção da Tabela de CEPs

> **Módulo**: Cadastros
> **Páginas de ajuda**: 1 página consolidada (referência da opção 044 de consulta)
> **Atualizado em**: 2026-02-15

## Função
Efetuar alterações na tabela de CEPs, permitindo atualização de faixas de CEP de cidades conforme mudanças dos Correios.

## Quando Usar
Necessário quando:
- Correios alteram faixas de CEP de cidades
- Precisa corrigir CEP inicial ou final de uma cidade
- Precisa incluir nova cidade com faixa de CEP
- Precisa atualizar Código IBGE de cidade

## Pré-requisitos
- Informação oficial dos Correios sobre alteração de CEP
- Permissão de acesso à opção (alterações impactam operação)
- Consultar opção 044 para verificar dados atuais antes de alterar

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Cidade/UF | Sim | Nome da cidade e UF |
| CEP inicial | Sim | CEP inicial da faixa da cidade (8 dígitos) |
| CEP final | Sim | CEP final da faixa da cidade (8 dígitos) |
| Código IBGE | Sim | Código IBGE da cidade |

## Fluxo de Uso

### Alteração de CEP
1. Acessar opção 044 (Consulta de cidades)
2. Localizar cidade a ser alterada
3. Anotar dados atuais (CEP inicial/final, Código IBGE)
4. Acessar opção 944
5. Localizar cidade
6. Alterar CEP inicial e/ou CEP final conforme informação dos Correios
7. Atualizar Código IBGE se necessário
8. Salvar alterações
9. Conferir na opção 044 se alteração foi aplicada

### Inclusão de nova cidade
10. Acessar opção 944
11. Informar nome da cidade e UF
12. Informar CEP inicial e CEP final
13. Informar Código IBGE
14. Salvar
15. Acessar opção 402 para cadastrar unidade operacional, praça, tipo de frete e pedágios

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 044 | Consulta de cidades — visualiza dados cadastrados (CEP, Código IBGE, unidade, praça, frete, pedágios) |
| 402 | Cadastro de cidades — define unidade operacional, praça, tipo de frete e pedágios (NÃO altera CEPs) |

## Observações e Gotchas

- **Opção 944 vs 402**:
  - **944**: Altera APENAS **tabela de CEPs** (CEP inicial, CEP final, Código IBGE)
  - **402**: Cadastra **dados operacionais** (unidade, praça, frete, pedágios) — NÃO altera CEPs

- **Consultar antes de alterar**: SEMPRE usar opção 044 para visualizar dados atuais ANTES de fazer alterações na opção 944 — evita sobrescrever dados corretos

- **Faixa de CEP**: CEP inicial e final definem faixa completa de CEPs da cidade — verificar no site dos Correios se faixa está correta

- **Código IBGE**: Código oficial de 7 dígitos do IBGE — não confundir com código interno da transportadora

- **Impacto operacional**: Alterações em CEPs impactam:
  - Cálculo de frete (identificação de cidade)
  - Roteamento de cargas
  - Emissão de CT-e (cidade destino)
  - Relatórios e consultas

- **Validação**: Após alterar, SEMPRE conferir na opção 044 se alteração foi aplicada corretamente

- **Fonte oficial**: Usar SEMPRE informações oficiais dos Correios — não alterar baseado em suposições

- **Site dos Correios**: Consultar site oficial dos Correios para verificar faixas de CEP atualizadas antes de fazer alterações

- **Backup**: Se possível, anotar dados antes de alterar — facilita reversão em caso de erro

- **Nova cidade**: Ao incluir nova cidade, LEMBRAR de cadastrar dados operacionais na opção 402 depois — sem isso, cidade não será atendida operacionalmente

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A03](../pops/POP-A03-cadastrar-cidades.md) | Cadastrar cidades |
