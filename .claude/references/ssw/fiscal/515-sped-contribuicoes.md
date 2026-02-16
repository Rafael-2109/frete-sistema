# Opcao 515 — SPED Contribuicoes (PIS/COFINS)

> **Modulo**: Fiscal / IR e PIS/COFINS (menu: Fiscal > IR e PIS/COFINS > 515)
> **Status CarVia**: EXTERNO (contabilidade externa executa)
> **Atualizado em**: 2026-02-16
> **SSW interno**: ssw1018 | Verificado via Playwright em 16/02/2026

## Funcao

Gera o arquivo SPED Contribuicoes (EFD-Contribuicoes) para envio a Receita Federal, contendo a apuracao de PIS e COFINS da transportadora. O sistema consolida receitas (CTRCs emitidos) e despesas com creditos PIS/COFINS (lancamentos de entrada na opcao 475), calcula os tributos conforme regime tributario (cumulativo ou nao-cumulativo) e gera o arquivo digital no layout exigido pela Receita Federal. O fechamento do periodo fiscal (opcao 567) ocorre automaticamente durante a geracao, por raiz de CNPJ.

## Diferenca entre Opcao 512 e Opcao 515

| Aspecto | Opcao 512 (SPED Fiscal) | Opcao 515 (SPED Contribuicoes) |
|---------|------------------------|-------------------------------|
| **Tributo** | ICMS + IPI | PIS + COFINS |
| **Ambito** | Estadual (SEFAZ) | Federal (Receita Federal) |
| **Fechamento por** | Inscricao Estadual (IE) | Raiz de CNPJ |
| **Layout** | EFD-ICMS/IPI | EFD-Contribuicoes |
| **Obrigatorio para** | Todos contribuintes ICMS/IPI | Lucro Real ou Presumido |
| **Creditos** | ICMS de entradas | PIS/COFINS de entradas (regime nao-cumulativo) |
| **Transmissao** | SEFAZ estadual | Receitanet (Receita Federal) |

## Quando Usar

- Obrigacao mensal para empresas no Lucro Real ou Lucro Presumido
- Geracao do arquivo EFD-Contribuicoes para transmissao a Receita Federal
- Fechamento do periodo fiscal por raiz de CNPJ
- Apos finalizacao de todos os lancamentos de receita (CTRCs) e despesa (475) do periodo

## Pre-requisitos

- Todos os CTRCs do periodo autorizados pelo SEFAZ (opcao 007)
- Todas as despesas do periodo lancadas (opcao 475) com creditos PIS/COFINS corretos
- Regime tributario PIS/COFINS definido na opcao 401 (unidade)
- Eventos de despesa (opcao 503) configurados com marcacao de creditamento PIS/COFINS
- Certificado digital valido (opcao 903/Certificados)
- Periodo fiscal aberto (opcao 567) — primeira geracao ou periodo reaberto para correcoes
- Validador SPED Contribuicoes instalado (programa da Receita Federal)

## Campos / Interface

> **Verificado via Playwright em 16/02/2026 contra o SSW real.**
>
> A tela ssw1018 tem 28 inputs visiveis — muito mais completa que o inferido.

### Campos Principais

| Campo | Name/ID | Obrigatorio | Descricao |
|-------|---------|-------------|-----------|
| **CNPJ** | cnpj_emp | Sim | CNPJ da empresa (default: 62312605000175, maxlen=14). Link para lookup de unidades |
| **Periodo de referencia (inicio)** | per_ref_ini | Sim | Formato ddmmaa (maxlen=6) |
| **Periodo de referencia (fim)** | per_ref_fin | Sim | Formato ddmmaa (maxlen=6) |
| **Periodo extemporaneo (inicio)** | per_ext_ini | Opc | Formato ddmmaa (maxlen=6). Para declaracoes fora do prazo |
| **Periodo extemporaneo (fim)** | per_ext_fin | Opc | Formato ddmmaa (maxlen=6) |
| **Tipo de escrituracao** | tp_escrituracao | Sim | "0" = Original, "1" = Retificadora (maxlen=1, default: 0) |
| **Referencia** | referencia | Sim | "X" = XML, "P" = Contas a Pagar (maxlen=1, default: P) |
| **Objetivo** | objetivo | Sim | "S" = Simulacao, "E" = Envio (maxlen=1, default: S) |
| **Usa contab Credito a recuperar** | lancto_contab | Sim | "S" = Sim, "N" = Nao (maxlen=1, default: N) |
| **Relatorio Conferencia Excel** | excel | Sim | "S" = Sim, "N" = Nao (maxlen=1, default: N) |
| **Numero recibo anterior** | nro_recib_ant | Opc | So para Tipo 1 — Retificadora (maxlen=41) |
| **Base calc sobre rendimento aplicacao** | base_calc_rend_aplica | Opc | Valor monetario (maxlen=18) |
| **Base calc sobre outras receitas** | base_calc_outras_receitas | Opc | Valor monetario (maxlen=18) |
| **Valor credito PIS periodo anterior** | vlr_cred_pis_per_ant | Opc | Valor monetario (maxlen=15) |
| **Valor credito COFINS periodo anterior** | vlr_cred_cofins_per_ant | Opc | Valor monetario (maxlen=15) |
| **Base calculo DEBITO PIS/COFINS** | deduz_icms_debito | Sim | "0" = Nao deduzir ICMS, "1" = Deduzir ICMS, "2" = Deduzir ICMS recolhido SPED FISCAL (maxlen=1, default: 1) |

### Dados do Contabilista

| Campo | Name/ID | Descricao |
|-------|---------|-----------|
| Nome | contab_nome | Nome completo (maxlen=40) |
| CPF | contab_cpf | CPF do contabilista (maxlen=11) |
| CRC | contab_crc | Registro no CRC (maxlen=11) |
| CNPJ | contab_cnpj | CNPJ do escritorio (maxlen=14) |
| CEP | contab_cep | CEP (maxlen=8) |
| Endereco/Numero/Complemento | contab_end / contab_numero / contab_comple | Endereco completo |
| Bairro | contab_bairro | Bairro (maxlen=40) |
| Fone | contab_ddd_fone / contab_fone | DDD (maxlen=2) + Fone (maxlen=8) |
| E-mail | contab_email | E-mail do contabilista (maxlen=40) |

### Acoes Adicionais

| Botao | Acao |
|-------|------|
| **Cadastro de Contas contabeis** | `ajaxEnvia('TELA_CONTAS', 1)` — abre tela auxiliar |
| **ICMS recolhido SPED FISCAL** | `ajaxEnvia('TELA_DEDUCAO', 1)` — abre tela de deducoes |

### Campos Inferidos vs Reais

| Inferido | Status Real |
|----------|-------------|
| Filtros por unidade/empresa/regime | **PARCIAL** — CNPJ filtra empresa; tipo escrituracao e referencia sao controles, nao filtros |
| Log/historico de geracoes anteriores | **NAO VISIVEL** na tela — pode existir internamente |
| Integracao direta com Receitanet | **NAO** — gera arquivo para transmissao manual (campo "Objetivo" S/E) |

## Fluxo de Uso

### Geracao do Arquivo

1. Verificar que todos os lancamentos do periodo estao finalizados:
   - CTRCs autorizados (opcao 007)
   - Despesas lancadas com creditos PIS/COFINS (opcao 475)
2. Acessar opcao 515
3. Informar periodo de apuracao (mes/ano)
4. [CONFIRMAR: selecionar CNPJ ou automatico por raiz]
5. Gerar arquivo SPED Contribuicoes
6. Sistema processa automaticamente:
   - Consolida receitas: CTRCs autorizados (valores de frete)
   - Consolida despesas: lancamentos com creditos PIS/COFINS
   - Calcula apuracao conforme regime:
     - **Cumulativo**: PIS 0,65% + COFINS 3% sobre receita bruta
     - **Nao-Cumulativo**: PIS 1,65% + COFINS 7,6% sobre receita, menos creditos
   - Gera arquivo `.txt` no formato EFD-Contribuicoes
   - **FECHA automaticamente** o periodo fiscal (opcao 567) por raiz de CNPJ
7. Salvar arquivo gerado

### Validacao

1. Abrir Validador SPED Contribuicoes (programa da Receita Federal)
2. Carregar arquivo gerado
3. Validador verifica: estrutura, apuracao, CSTs, campos obrigatorios
4. Se erros: corrigir no SSW → reabrir periodo (opcao 567) → corrigir lancamentos → gerar novamente
5. Se OK: salvar arquivo validado

### Transmissao

1. Acessar Receitanet (programa da Receita Federal)
2. Fazer upload do arquivo validado
3. Aguardar processamento
4. Receber e arquivar protocolo de entrega

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 401 | Cadastro de unidades — define regime PIS/COFINS (cumulativo/nao-cumulativo) e IE |
| 475 | Contas a pagar — lancamentos de despesa com creditos PIS/COFINS |
| 503 | Eventos de despesa — configuracao de creditamento PIS/COFINS por tipo de despesa |
| 512 | SPED Fiscal ICMS/IPI — complementar; fecha por IE (enquanto 515 fecha por raiz CNPJ) |
| 567 | Fechamento fiscal — fechamento automatico ao gerar SPED Contribuicoes; pode reabrir para correcoes |
| 584 | NCMs — define despesas creditaveis por NCM |
| 903 | Parametros gerais — certificado digital, configuracoes de impostos |

## Observacoes e Gotchas

- **Fechamento automatico**: Ao gerar SPED Contribuicoes, o sistema fecha automaticamente o periodo fiscal (opcao 567) por raiz de CNPJ. Todas as unidades com mesma raiz ficam bloqueadas para alteracoes retroativas
- **Reabertura de periodo**: Se necessario corrigir lancamentos apos geracao, reabrir periodo na opcao 567 ANTES de corrigir. Gerar novamente como arquivo SUBSTITUTO
- **Regime tributario**: O calculo de PIS/COFINS depende do regime definido na opcao 401. Verificar se esta correto para a CarVia
- **Creditos de entrada**: No regime nao-cumulativo, creditos PIS/COFINS de despesas so sao considerados se o evento (opcao 503) estiver marcado para creditamento
- **Prazo legal**: [CONFIRMAR: prazo de envio a Receita Federal — geralmente ate o 10o dia util do 2o mes subsequente]
- **IBS e CBS**: XMLs de NF-e/CT-e mais recentes podem conter campos IBS e CBS — importados automaticamente pelo SSW
- **ICMS Monofasico (CST 61)**: Creditos de combustivel com CST 61 devem ser tratados separadamente (regime debito/credito na opcao 401)
- **[CONFIRMAR]**: Verificar se existe log/historico de geracoes anteriores do SPED Contribuicoes
- **[CONFIRMAR]**: Verificar se ha integracao direta com Receitanet ou se a transmissao e 100% manual

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-G04 | Relatorios para contabilidade — POP completo que inclui geracao do SPED Contribuicoes como ETAPA 3 |
| POP-F01 | Contas a pagar — lancamentos de despesa que alimentam creditos PIS/COFINS |
| POP-C01 | Emitir CTe fracionado — receitas que compoem a base de calculo |
| POP-C02 | Emitir CTe carga direta — receitas que compoem a base de calculo |

## Status CarVia

| Aspecto | Status |
|---------|--------|
| **Adocao** | EXTERNO — contabilidade externa ja executa este processo mensalmente |
| **Quem faz** | Contabilidade externa (experiente com 100+ transportadoras SSW) |
| **Responsabilidade CarVia** | Garantir lancamentos corretos e completos (CTRCs + despesas) antes do prazo da contabilidade |
| **Executor futuro** | Contabilidade externa (sem mudanca prevista) |
| **Dependencia interna** | Qualidade dos lancamentos de entrada (475) e saida (007) do periodo |
