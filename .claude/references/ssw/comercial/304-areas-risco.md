# Opcao 304 — Areas de Risco

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Define areas de risco de assaltos, furtos, etc., utilizando faixas de CEP, para uso em alertas/bloqueios em outras opcoes do SSW e cobranca de TAR (Taxa Adicional de Risco) em tabelas de frete.

## Quando Usar
- Cadastrar areas geograficas com alto indice de criminalidade
- Configurar alertas ou bloqueios para operacoes em areas perigosas
- Limitar valor de mercadoria por romaneio em areas de risco
- Habilitar cobranca automatica de TAR (Taxa Adicional de Risco) nas tabelas de frete

## Pre-requisitos
- Conhecimento das faixas de CEP que configuram areas de risco
- Definicao da politica de bloqueio vs. alerta

## Campos / Interface

### Tela Inicial (Filtros)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| UF | Condicional | Traz areas ja cadastradas da UF informada |
| Unidade | Condicional | Traz areas ja cadastradas na unidade informada |
| Cidade/UF | Condicional | Traz areas ja cadastradas na cidade informada |
| Importar arq CSV / Baixar | Nao | Baixar=gera CSV conforme filtros; Importar=importa CSV editado, sobrepondo dados |
| Importar de parceiro | Nao | Importa on-line areas de parceiro (dominio SSW) cadastradas na UF/Unidade/Cidade, sobrepondo dados |

### Tela Principal (Cadastro)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CEP inicial | Sim | CEP inicial da faixa que define Area de Risco. Deve ser do mesmo municipio do CEP final |
| CEP final | Sim | CEP final da faixa que define Area de Risco. Deve ser do mesmo municipio do CEP inicial |
| Bloquear | Sim | Define se efetua bloqueio ou apenas alerta para ocorrencia na Area de Risco |
| Valor mercadoria maximo por Romaneio | Nao | Limite de valor de mercadoria para Area de Risco por Romaneio (opcao 035). Se diversas areas forem romaneadas, o menor valor sera utilizado |
| Alterar/Excluir | Nao | Links para editar ou remover area de risco |

## Fluxo de Uso
1. Selecionar filtro (UF, Unidade ou Cidade) para visualizar areas existentes
2. Definir faixa de CEP (inicial e final do mesmo municipio)
3. Configurar comportamento (Bloquear=bloqueio, desligado=alerta)
4. Opcionalmente definir limite de valor de mercadoria por romaneio
5. Salvar cadastro
6. Areas de risco passam a ser verificadas automaticamente em:
   - Coleta (opcao 001)
   - Cotacao (opcao 002)
   - Emissao de CTRC (opcoes 004, 005, 006)
   - Emissao de Romaneio (opcao 035)
7. Tabelas de frete podem cobrar TAR automaticamente para estas areas

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 001 | Coleta — verifica area de risco para CEP origem e destino (se destinatario informado) |
| 002 | Cotacao — verifica area de risco para CEP origem e destino |
| 004 | Emissao de CTRC (normal) — verifica area de risco para CEP destino |
| 005 | Emissao de CTRC (alternativa) — verifica area de risco para CEP destino |
| 006 | Emissao de CTRC (alternativa) — verifica area de risco para CEP destino |
| 035 | Emissao de Romaneio — aplica limite de valor de mercadoria. Se multiplas areas, usa menor valor |
| 417 | Tabela de frete — pode cobrar TAR (Taxa Adicional de Risco) para coletas/entregas nestas areas |
| 418 | Tabela de frete — pode cobrar TAR (Taxa Adicional de Risco) para coletas/entregas nestas areas |

## Observacoes e Gotchas
- **CEPs da mesma cidade**: CEP inicial e final de uma faixa DEVEM ser do mesmo municipio
- **Area de Risco = faixa de CEP**: cada area e definida por uma faixa continua de CEPs
- **Bloqueio vs. Alerta**: configuravel por area (bloqueio impede operacao; alerta apenas notifica)
- **Limite de mercadoria em romaneios**: se romaneio tem entregas em multiplas areas de risco, o MENOR valor de mercadoria entre as areas sera utilizado como limite
- **TAR (Taxa Adicional de Risco)**: tabelas de frete (opcoes 417, 418, etc.) podem cobrar automaticamente TAR quando coletas/entregas ocorrerem nestas areas
- **Importacao de parceiro**: funcionalidade para importar areas de risco ja cadastradas por outro dominio SSW (parceiro)
- **Importacao CSV**: permite edicao massiva em Excel e reimportacao sobrepondo dados existentes
- **Verificacao em Coleta (001)**: valida AMBOS CEP origem E CEP destino (se destinatario for informado)
- **Verificacao em Cotacao (002)**: valida AMBOS CEP origem E CEP destino
- **Verificacao em CTRC (004/005/006)**: valida APENAS CEP destino da operacao

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
