# Modulo OPERACIONAL — Coleta e Entrega — Indice

> **Sistema**: SSW Sistemas
> **Modulo**: Operacional — Coleta/Entrega
> **Documentacao completa**: 18 opcoes documentadas
> **Ultima atualizacao**: 2026-02-14

## Visao Geral

Este indice relaciona todas as opcoes do modulo OPERACIONAL — sub-area Coleta e Entrega documentadas neste diretorio. Cada arquivo .md contem:
- Funcao da opcao
- Quando usar
- Pre-requisitos
- Campos e interface
- Fluxo de uso
- Integracoes com outras opcoes
- Observacoes e gotchas (armadilhas comuns)

## Opcoes Documentadas

### Coletas

| Opcao | Nome | Arquivo | Funcao Principal |
|-------|------|---------|------------------|
| 001 | Cadastro de Coletas | `001-cadastro-coletas.md` | Registrar solicitacoes de coletas via telefone/API/EDI |
| 002 | Cotacao de Fretes | `002-consulta-coletas.md` | Simular e contratar cotacoes de frete |
| 003 | Ordem de Coleta / Gerenciamento | `003-ordem-coleta-gerenciamento.md` | Comandar coletas para veiculos e atualizar situacoes |
| 013 | Veiculo Sugerido por Setor | `013-veiculo-sugerido-setor.md` | Vincular veiculos a setores para sugestao automatica |

### Entregas

| Opcao | Nome | Arquivo | Funcao Principal |
|-------|------|---------|------------------|
| 035 | Romaneio de Entregas | `035-romaneio-entregas.md` | Relacionar CTRCs para entrega em veiculo |
| 036 | Controle de Entregas | `036-controle-entregas.md` | Consultar Romaneios cancelados |
| 038 | Baixa de Entregas / Ocorrencias | `038-baixa-entregas-ocorrencias.md` | Baixar entregas e registrar pendencias |
| 039 | Acompanhamento | `039-acompanhamento.md` | Avaliar performance de entregas (relatorios) |

### Complementares

| Opcao | Nome | Arquivo | Funcao Principal |
|-------|------|---------|------------------|
| 043 | Agendamento | `043-agendamento.md` | Registrar ocorrencias por Nota Fiscal |
| 045 | Controle | `045-controle.md` | Cadastrar login/senha SSWMobile |
| 048 | Liquidacao a Vista | `048-liquidacao-vista.md` | Liquidar fretes FOB A VISTA |
| 049 | Controle de Comprovantes | `049-controle-comprovantes.md` | Registrar "Saiu para Entrega" / Emitir CTRCs manuais |
| 053 | Consulta Rapida | `053-consulta-rapida.md` | Receber reembolsos e emitir Capa Lote Cheques |
| 054 | Controle | `054-controle.md` | (Duplicado da 053) |
| 055 | Lembretes | `055-lembretes.md` | Cadastrar lembretes do cliente |
| 059 | Consulta | `059-consulta.md` | Cadastrar observacoes em CTRCs/boletos |
| 066 | Controle | `066-controle.md` | Remeter vias de cobranca para Matriz |
| 068 | Controle | `068-controle.md` | Configurar comissao de cotacao |

## Fluxo Operacional Tipico

### 1. Coleta
```
Opcao 001 (Cadastro) → Opcao 003 (Comandar) → SSWMobile (Executar)
```

### 2. Entrega
```
Opcao 035 (Romaneio) → Opcao 038 (Baixar) → SSWMobile (Executar)
```

### 3. Cotacao e Venda
```
Opcao 002 (Cotar) → Opcao 004 (Emitir CTRC) → Opcao 068 (Comissao)
```

### 4. Reembolso
```
Opcao 038 (Entregar) → Opcao 053 (Receber) → Opcao 041 (Capa Lote)
```

## Integracao com SSWMobile

Opcoes integradas com SSWMobile para operacao em tempo real:
- **001**: Atualizar coletas
- **003**: Comandar/informar coletas
- **035**: Receber Romaneio e roteiro
- **038**: Baixar entregas com foto/assinatura
- **045**: Login/senha para acesso

## Opcoes NAO Documentadas (fora do escopo atual)

As seguintes opcoes estavam na lista original mas nao tinham arquivo consolidado disponivel ou foram identificadas como duplicadas:
- Opcao 055 (Lembretes) — documentada com base nas referencias cruzadas

## Referencias Cruzadas

### Cadastros Necessarios
- Opcao 026: Veiculos
- Opcao 028: Motoristas
- Opcao 163: Ajudantes
- Opcao 401: Unidades
- Opcao 402: Cidades
- Opcao 404: Setores
- Opcao 405: Ocorrencias de entrega
- Opcao 519: Ocorrencias de coleta

### Configuracoes Globais
- Opcao 903: Parametros gerais (GR, estadias, papel, etc.)
- Opcao 925: Usuarios e permissoes

### Relatorios e Consultas
- Opcao 050: Relatorio de coletas
- Opcao 056: Relatorios gerenciais
- Opcao 081: CTRCs disponiveis para entrega
- Opcao 088: Situacao veiculos tempo real
- Opcao 101: Situacao do CTRC
- Opcao 102: Situacao do cliente
- Opcao 103: Situacao das coletas
- Opcao 129: CTRCs em Romaneios

## Observacoes Gerais

### Timezone
Todos timestamps armazenados em **Brasil naive** (America/Sao_Paulo). Ver `.claude/references/REGRAS_TIMEZONE.md`.

### Gerenciamento de Risco
Opcoes 003 e 035 integram com GR via Opcao 903. Requisitos:
- Liberacao veiculos/motoristas/ajudantes
- Requisitos valores mercadoria (Opcao 390)
- SMP obrigatorio (Opcao 235)

### Operacao Sem Papel
Ativacao via Opcao 903/Operacao:
- SSWMobile baixa com foto/assinatura
- DACTEs impressos so quando necessario
- Codigo barras DACTE no Romaneio substitui documento

## Documentacao Adicional

- **SSW Sistemas**: `.claude/references/ssw/INDEX.md`
- **Manual SSW completo**: https://sistema.ssw.inf.br/ajuda/
- **APIs SSW**: https://ssw.inf.br/ws/
- [Opcao 004 — Emissao de CTRCs](004-emissao-ctrcs.md)
- [Opção 006 — Emissão de CT-e/CT-e OS em Lote](006-emissao-cte-os.md)
- [Opção 007 — Impressão e Autorização de CT-es](007-emissao-cte-complementar.md)
- [Opcao 009 — Impressao de RPS e Geracao de NFS-e](009-impressao-rps-nfse.md)
- [Opcao 011 — Identificacao de Volumes](011-identificacao-volumes.md)
- [Opção 015 — Agendamento de Entregas](015-agendamento-entregas.md)
- [Opcao 018 — Gerenciamento dos SSWBars](018-gerenciamento-sswbar.md)
- [Opcao 019 — Emissao do Manifesto Operacional](019-manifesto-operacional.md)
- [Opção 020 — Manifesto de Carga](020-manifesto-carga.md)
- [Opcao 021 — Cadastro de Gaiolas e Estoque de Pallets e Chapas](021-cadastro-gaiolas.md)
- [Opção 025 — Saída de Veículos](025-saida-veiculos.md)
- [Opcao 027 — Relacao de Proprietarios de Veiculos](027-relacao-proprietarios-veiculos.md)
- [Opcao 028 — Relacao de Motoristas](028-relacao-motoristas.md)
- [Opção 030 — Chegada de Veículo](030-chegada-de-veiculo.md)
- [Opção 031 — CTRCs com Determinada Ocorrência](031-controle-de-chegada.md)
- [Opção 033 — Ocorrências de Transferência](033-ocorrencias-de-transferencia.md)
- [Opção 071 — Notas Fiscais Importadas via EDI (Contratação de Veículos)](071-contratacao-de-veiculos.md)
- [Opção 072 — Contratação de Veículo de Transferência](072-contratacao-de-veiculo-de-transferencia.md)
- [Opção 073 (077) — Reemissão de CTRBs](073-controle-de-contratacao.md)
- [Opção 081 — CTRCs Disponíveis para Entrega (Romaneio)](081-romaneio.md)
- [Opção 084 — Informar Pesos e Volumes de NFs (opção 148 — Resultados de Cubagem/Pesagem)](084-controle.md)
- [Opção 087 — Apreensão Fiscal de Mercadorias (TAD)](087-controle.md)
- [Opção 091 — Controle de CTRCs Segregados](091-consulta.md)
- [Opção 097 — Cadastro de Tipos de Veículos](097-controle.md)
- [Opção 099 — Cobrança de Estadia na Entrega](099-consulta.md)
- [Opcao 108 — Instrucoes para Ocorrencias de Entrega](108-ocorrencias-entrega.md)
- [Opção 120 — Chegada de Veículo sem Manifesto](120-chegada-veiculo-sem-manifesto.md)
- [Opção 133 — Informar Ocorrências em CTRCs](133-ocorrencias-ctrcs.md)
- [Opção 136 — Cobrança de Armazenagem](136-cobranca-armazenagem.md)
