# Opcao 398 — Escanear Comprovantes de Entregas

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Efetua escaneamento de comprovantes de entregas e associa imagens digitalizadas aos CTRCs. Permite anexar comprovantes manualmente quando o SSWScan nao funcionar ou para complementar documentacao.

## Quando Usar
- Anexar comprovante de entrega escaneado manualmente (sem SSWScan)
- Complementar documentacao de CTRCs previamente baixados
- Casos onde SSWScan nao funcionou ou nao esta disponivel
- Escanear comprovantes de parcerias/subcontratacoes

## Pre-requisitos
- CTRC deve estar previamente baixado (opcao 038)
- Imagem escaneada salva no micro (max 200 KB)
- SSWScan2 instalado (versao 3.3.0.0.0) - opcional

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Chave DACTE | Nao | Codigo de barras do CTRC da transportadora executante |
| CTRC | Sim | Serie e numero com digito verificador do CTRC |
| Buscar no micro | Sim | Seleciona imagem escaneada numa pasta do micro |

## Fluxo de Uso

### Fluxo Normal (Manual):
1. Escanear comprovante fisico para arquivo (max 200 KB)
2. Acessar opcao 398
3. Informar CTRC (serie + numero)
4. Clicar em "Buscar no micro"
5. Selecionar arquivo da imagem
6. Confirmar anexacao

### Fluxo com SSWScan2:
1. Clicar em "SSWScan 2" na tela 1
2. Seguir processo automatizado do SSWScan
3. Sistema faz baixa de entrega automaticamente

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 033 | Ocorrencias - grava SSW 19 (ANEXADO COMPROVANTE DE ENTREGA COMPLEMENTAR) |
| 038 | Baixa de entrega - CTRC deve estar baixado antes de anexar comprovante manual |
| 040 | Comprovantes fisicos - armazenamento papel |

## Observacoes e Gotchas

- **SSWMobile e preferido**: captura on-line pelo motorista e faz baixa automatica da entrega
- **SSWScan**: usa codigo de barras da DACTE para baixar entrega E anexar comprovante automaticamente
- **Tamanho maximo**: 200 KB por imagem (configurar no escaner). Imagens maiores sao reduzidas automaticamente
- **Parcerias**: escanear comprovante do subcontratante contratado pelo cliente embarcador. SSW atualiza todos os documentos envolvidos
- **Ocorrencia SSW 19**: gravada automaticamente ao anexar comprovante. Data/hora NAO considerada para cronologia de novas ocorrencias
- **Reinstalacao SSWScan2**: se link "SSWScan 2" nao funcionar, usar "Instalar SSWScan 2"
- **Socket Error - Host not found**: existe Proxy na rede e SSWScan2 nao foi configurado. Acionar TI ou Suporte SSW
- **Uso manual**: apenas quando SSWScan nao funciona ou para complementar comprovantes ja escaneados
- Opcao 398 e para anexacao COMPLEMENTAR - baixa da entrega deve ser feita antes (opcao 038)
