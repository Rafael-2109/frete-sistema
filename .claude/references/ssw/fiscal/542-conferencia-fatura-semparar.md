# Opcao 542 — Conferencia da Fatura SEMPARAR

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Confere fatura SEMPARAR com arquivo de Passagem enviado pelo sistema de pedagios. Gera relatorio concatenando cronologicamente dados de pedagios cobrados em Pracas com informacoes de Manifestos, Romaneios e CTRBs/OSs emitidos pelo SSW.

## Quando Usar
- Conferencia de fatura mensal SEMPARAR (pedagios)
- Auditoria de pedagios cobrados vs passagens reais
- Verificacao de pedagios por veiculo especifico
- Atualizacao de tabela de Pracas de Pedagio do SSW

## Pre-requisitos
- Extrato SEMPARAR em TXT obtido do site
- Arquivo de Passagem SEMPARAR com pedagios cobrados
- Manifestos, Romaneios e CTRBs/OSs emitidos no periodo
- Opcionalmente: arquivo de Pracas de Pedagio do SEMPARAR

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Arquivo Passagem | Sim | Arquivo TXT do SEMPARAR com pedagios cobrados na fatura |
| Periodo | Sim | Periodo de emissao de Manifestos, Romaneios e CTRBs/OSs (relacionado ao periodo da fatura) |
| Placa | Nao | Filtro para verificar apenas veiculo especifico |
| Arquivo Praca | Nao | Arquivo com relacao de Pracas de Pedagio (para atualizar tabela SSW) |

## Fluxo de Uso
1. Obter Extrato SEMPARAR em TXT via site: https://appsol.viafacil.com.br/sol/jsp/sol/html/index.jsp
2. Acessar opcao 542
3. Informar arquivo de Passagem (TXT do SEMPARAR)
4. Informar periodo de emissao de Manifestos/Romaneios/CTRBs/OSs
5. Opcionalmente informar placa para filtrar veiculo especifico
6. Opcionalmente informar arquivo de Pracas (para atualizar tabela SSW)
7. Executar geracao do relatorio
8. Analisar relatorio concatenado cronologicamente
9. Avaliar correcao da cobranca (veiculo de fato passou na praca)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| Sistema Manifestos | Fonte de dados de manifestos emitidos |
| Sistema Romaneios | Fonte de dados de romaneios emitidos |
| Sistema CTRBs/OSs | Fonte de dados de CTRBs/OSs emitidos |

## Observacoes e Gotchas

### Obtencao de Extrato
- **Site SEMPARAR**: extrato on-line em TXT deve ser obtido via https://appsol.viafacil.com.br/sol/jsp/sol/html/index.jsp
- Formato TXT e obrigatorio para importacao

### Relatorio Gerado
- **Concatenacao cronologica**: relatorio organiza dados de pedagios + manifestos + romaneios + CTRBs/OSs em ordem cronologica
- **Correlacao automatica**: sistema tenta correlacionar pedagios cobrados com movimentacoes registradas no SSW
- **Facilitacao de auditoria**: formato facilita identificacao de divergencias

### Avaliacao Manual
- **Responsabilidade do usuario**: avaliacao da correcao da cobranca (se veiculo de fato passou na praca) DEVE ser realizada pelo usuario
- Sistema NAO faz validacao automatica de correcao/incorrecao
- Relatorio fornece dados organizados para analise humana

### Filtro por Veiculo
- **Opcional**: informar placa quando desejar verificar apenas um veiculo especifico
- Util para auditoria focada ou investigacao de divergencias

### Arquivo de Pracas
- **Atualizacao de tabela**: arquivo de Pracas de Pedagio do SEMPARAR pode ser usado para atualizar tabela de Pracas do SSW
- Campo opcional, mas util para manter cadastro atualizado
- Garante que nomes de pracas estejam consistentes entre SEMPARAR e SSW

### Periodo
- Periodo informado deve coincidir com periodo da fatura SEMPARAR
- Inclui emissao de Manifestos, Romaneios e CTRBs/OSs
- Periodo correto e essencial para correlacao precisa
