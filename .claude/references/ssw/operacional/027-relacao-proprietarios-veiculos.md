# Opcao 027 — Relacao de Proprietarios de Veiculos

> **Modulo**: Operacional — Frota
> **Paginas de ajuda**: 1 pagina consolidada (tambem referencia opcao 046)
> **Atualizado em**: 2026-02-14

## Funcao
Gera relacao de proprietarios de veiculos cadastrados, com filtros por tipo de pessoa, periodo de cadastramento e vigencia de CIOT.

## Quando Usar
- Consultar base de proprietarios cadastrados
- Filtrar proprietarios com CIOTs em aberto
- Exportar dados para Excel
- Auditar cadastros de proprietarios

## Pre-requisitos
- Proprietarios cadastrados via opcao 027
- (Opcional) CIOTs cadastrados para filtrar por vigencia

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| **PESSOA** | Sim | F = Pessoa Fisica (CPF), J = Pessoa Juridica (CNPJ), A = Ambos |
| **PERIODO DE CADASTRAMENTO** | Nao | Periodo em que os proprietarios foram cadastrados |
| **PERIODO DE VIGENCIA DO CIOT** | Nao | Filtra proprietarios com CIOTs em aberto dentro do periodo |
| **ARQUIVO EM EXCEL** | Sim | S = gera planilha Excel, N = formato texto |

## Fluxo de Uso
1. Selecionar tipo de pessoa (F/J/A)
2. (Opcional) Informar periodo de cadastramento
3. (Opcional) Informar periodo de vigencia de CIOT para filtrar apenas com CIOTs ativos
4. Escolher formato de saida (Excel ou texto)
5. Gerar relatorio

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| **027** | Cadastro de proprietarios de veiculos (fonte dos dados) |
| **026** | Cadastro de veiculos — vincula proprietario ao veiculo |
| **072** | Contratacao de veiculos — usa dados do proprietario |

## Observacoes e Gotchas
- **Filtro CIOT** — busca apenas proprietarios com CIOTs **em aberto** (nao encerrados)
- **Formato Excel** — util para analises e manipulacao de dados
- **Formato texto** — padrao para integracao ou visualizacao rapida
- Periodo de cadastramento e periodo de vigencia CIOT sao filtros independentes
- Opcao **046** (citada na ajuda) e o numero alternativo para acessar esta funcionalidade

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
