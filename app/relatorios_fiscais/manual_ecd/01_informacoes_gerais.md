# Capitulo 1 — Informacoes Gerais (Resumo)

> Paginas PDF 5-51 · 44 subsecoes (1.1 a 1.44) · Volta ao [INDEX](INDEX.md)

**Conteudo**: legislacao, prazos, hash, RAS, moeda funcional, SCP, substituicao, recuperacao ECD anterior. Esta e uma sumarizacao para consulta — quando precisar do texto integral, ler o PDF.

---

## 1.1-1.2 Introducao e Legislacao

**SPED** (Decreto 6.022/2007): sistema unificado de recepcao, validacao, armazenamento e autenticacao de livros/documentos contabeis e fiscais.

**ECD** (Escrituracao Contabil Digital) substitui em formato digital:
- I. Livro Diario e auxiliares
- II. Livro Razao e auxiliares
- III. Livro Balancetes Diarios, Balancos e fichas de lancamento

**Normas chave**:
- IN RFB 2.003/2021 — regulamenta ECD (substituiu IN 1.774/2017)
- CTG 2001 (R3) CFC — formalidades escrituracao digital
- ITG 2000 (R1) CFC — escrituracao contabil
- IN RFB 1.700/2017 — moeda funcional, RAS, RET

**Tabela de Leiautes**:
| Leiaute | Periodo | Manual |
|---------|---------|--------|
| 1-4 | Ate 2015 | AD Cofis 34/2016 |
| 5 | 2016 | AD Cofis 29/2017 |
| 6 | 2017 | AD Cofis 53/2018 |
| 7 | 2018 | AD Cofis 83/2018 |
| 8 | 2019 | AD Cofis 64/2019 |
| **9** | **2020 em diante** | AD Cofis 79/2020 + 104/2021 + 114/2022 + 57/2023 + **01/2026** |

**I010.COD_VER_LC = "9.00"** para ano-calendario 2020+.

---

## 1.3 Obrigatoriedade

| Regime | Obrigado? |
|--------|-----------|
| **Lucro Real** | **Todas** |
| **Lucro Presumido** | So se NAO optou por livro caixa OU se distribuiu lucros sem IRRF em valor > base calculo |
| **Imunes/Isentas** | Se receitas+doacoes+etc >= R$ 4.800.000,00 |
| **SCP** | Mesmas regras (entrega em arquivo proprio, separado da socia ostensiva) |
| **Simples Aporte** | Sim, se recebeu aporte conforme art. 61-A a 61-D Lei Compl 123/2006 |
| **PJ Recursos Exterior** | Sim |
| **ESC** (Empresas Simples Credito) | Sim |
| **Simples Nacional** | Nao |
| **Orgaos publicos, autarquias, fundacoes** | Nao |
| **Inativas** | Nao (transmite DCTF como inativa) |
| **Itaipu Binacional** | Nao |
| **Demais** | Facultativa (sem multa) |

**Inatividade**: anual. Se realmente sem lancamentos, cadastrar pelo menos 1 conta/mes em I150/I155 com tudo zerado.

---

## 1.5 Prazos

| Situacao | Prazo |
|----------|-------|
| Normal | Ultimo dia util de **junho** do ano seguinte |
| Situacao especial (extincao, cisao, fusao, incorporacao) Jan-Mai | Ultimo dia util de **junho** do mesmo ano |
| Situacao especial Jun-Dez | Ultimo dia util do **mes seguinte** ao evento |

---

## 1.6 Formas de Escrituracao

| Sigla | Tipo |
|-------|------|
| **G** | Diario Geral (completo, SEM escrituracao auxiliar) |
| **R** | Diario com Escrituracao Resumida (com auxiliar) |
| **A** | Diario Auxiliar |
| **Z** | Razao Auxiliar (parametrizavel) |
| **B** | Balancetes Diarios e Balancos (instituicoes financeiras) |

---

## 1.7 Regras de Convivencia

- **G** nao pode coexistir com nenhuma outra forma principal nem com auxiliares
- Principais G/R/B nao coexistem no mesmo periodo
- **R + auxiliares**: auxiliares (A ou Z) transmitidos ANTES do principal R. HASH dos auxiliares em I012 do R
- **B + auxiliares**: igual ao R, mas so para instituicoes financeiras
- I015 do principal R/B → conta ANALITICA do I050. I015 do auxiliar A/Z → conta SINTETICA do I050 (para detalhar com analiticas)

---

## 1.8 Hash do Livro

- Calculado pelo PGE ao validar
- 40 caracteres hexadecimais (0-9, A-F) — **sem letra "O"** (sempre numero zero)
- Visualizar via menu "Escrituracao > Dados da Escrituracao"
- Despreze separadores e digito verificador ao transcrever

---

## 1.10-1.11 Tamanho e Periodo dos Livros

- 1 arquivo = 1 livro
- Regra geral: ECD anual em 1 arquivo
- Arquivo > 5GB: pode entregar mensal (12 arquivos)
- Periodos do principal e dos auxiliares devem **coincidir** (se fragmentar 1, fragmenta os outros)
- Todos os meses no mesmo ano
- Sem fracao de mes (excecao: situacao especial, abertura)

**Casos de fracao de mes**: cisao parcial, incorporacao (se incorporadora) → 2 escrituracoes:
- Esc 1: inicio ate evento, IND_SIT_ESP=cod, IND_SIT_INI_PER=0 (Normal)
- Esc 2: dia seguinte ao evento ate fim, IND_SIT_ESP vazio, IND_SIT_INI_PER=2 (Resultante)

**Excecao**: se evento em 31/12, 1 escrituracao soh.

**Extincao/cisao total/fusao** (incorporada): 1 escrituracao do inicio ate evento.

**Sem descontinuidade**: ECD jan-mai nao pode pular fevereiro.

**Apuracao trimestral IRPJ**: livro pode ser anual com 4 conjuntos trimestrais + anual.

**Mudanca de contador no meio do periodo**: pode fracionar, MAS sem IND_SIT_ESP (mudanca contador nao e situacao especial).

**Mudanca de plano de contas no meio**: usar I157 no arquivo do segundo periodo.

**Data encerramento exercicio fora do periodo ECD**: Bloco J nao obrigatorio.

**Numero do livro**: nao precisa ser sequencial. Controle por hashcode.

**Alteracao de CNPJ matriz**: 1 arquivo unico OU 2 arquivos (antes/depois).

---

## 1.12 Substituicao da ECD

**Quando substituir**: erros que NAO podem ser corrigidos por lancamento extemporaneo (ITG 2000 R1, itens 31-36).

**Tipos de erro que justificam substituicao** (CTG 2001 R3):
- Ajustes no formato eletronico sem alterar saldos publicados (erros plano contas)
- Problemas de interface (multiplicacao por troca virgula/ponto)
- Abertura de subcontas Lei 12.973/14 sem alterar saldo total

**O que NAO justifica substituicao** (corrigir por lancamento extemporaneo):
- Erros que demandam alteracao de saldos
- Erros materiais que demandam reemissao de demonstracoes
- Finalizacao de demonstracoes posterior ao arquivamento da ECD

**Roteiro pratico** (substituir ECD):
1. Remover assinatura (apagar tudo apos 9999)
2. 0000.IND_FIN_ESC = "1" (Substituta)
3. 0000.COD_HASH_SUB = hash da ECD original (40 chars hex)
4. Corrigir as informacoes
5. Adicionar J801 (Termo de Verificacao para Fins de Substituicao)
6. Validar no PGE
7. Assinar
8. Transmitir

**Prazo limite**: ate fim do prazo de entrega da ECD do ano-calendario subsequente.
- ECDs do AC 2022 ou anteriores: **NAO podem mais ser substituidas**
- ECDs do AC 2023: substituiveis ate 30/06/2025

**Substituicoes possiveis** (resumo matrix):
| Original | Substituta |
|----------|------------|
| G | G ou R (transformando) ou B |
| R | R ou G (consolidando todos auxiliares) ou B |
| A/Z | A/Z (com J801) |
| Sem NIRE | Com NIRE (preencher I030.NIRE) |
| Com NIRE | Sem NIRE (deixar I030.NIRE vazio) |
| Um arquivo | Varios (mensais) |
| Varios | Um arquivo |

**Erro comum** "ECD substituida nao encontrada": COD_HASH_SUB errado. Verificar hash em http://www.sped.fazenda.gov.br/appConsultaSituacaoContabil/ConsultaSituacao/CNPJAno

---

## 1.13 Assinatura do Livro Digital

Detalhe completo nos registros [J930](bloco_J_demonstracoes.md#registro-j930) e [J932](bloco_J_demonstracoes.md#registro-j932).

**Resumo**: pelo menos 2 assinaturas:
1. Contador (codigo 900) com e-CPF
2. Responsavel (IND_RESP_LEGAL=S) com qualquer codigo exceto 900

---

## 1.14 Receitanet e ReceitanetBX

- **Receitanet**: transmite a ECD
- **ReceitanetBX**: baixa ECD ja transmitida + dados agregados

Porta: 3456 · IP: 200.198.239.21

**Download permitido para**:
- PJ: so a propria ECD
- Representante Legal: so a ECD do CNPJ que representa
- Procuracao Eletronica: so a ECD do CNPJ procurado

---

## 1.16 Lancamentos de Quarta Formula e Plano de Contas com 4 Niveis

- Lancamentos 4a formula (>=2 D e >=2 C) permitidos se referirem-se a um **unico fato contabil**
- Plano de contas **minimo 4 niveis**

---

## 1.17 Plano de Contas Referencial

- Mapeamento facultativo (campo 0000.COD_PLAN_REF)
- Mesmos planos da ECF (registros L100, L300, P100, P150, U100, U150)
- Arquivos das tabelas dinamicas: `C:\Arquivos de Programas RFB\Programas SPED\SpedContabil\recursos\tabelas`
- Codigos 1-10 do COD_PLAN_REF: ver [Registro 0000](bloco_0_abertura.md#registro-0000)

---

## 1.18 Multa por Atraso

Lei 8.218/1991 art. 12 (redacao Lei 13.670/2018):
- **0,5%** da receita bruta — falha em requisitos para apresentacao
- **5%** sobre valor da operacao (limitado a 1% receita bruta) — omissoes/erros
- **0,02% por dia de atraso** sobre receita bruta (limitado a 1%) — atraso

**Reducoes** (se uso SPED):
- 50% se cumprido apos prazo mas antes de oficio
- 75% se cumprido no prazo de intimacao

**Codigo de Receita**: 1438 (DARF via Sicalcweb).

---

## 1.22 Razao Auxiliar das Subcontas (RAS)

Detalhes completos no PDF p.25-35 + nos registros [I053](bloco_I_lancamentos.md#registro-i053), [I500-I555](bloco_I_lancamentos.md#registros-i500i510i550i555--razao-auxiliar-parametrizavel-livro-z).

**NAT_LIVR** (I030 campo 4):
- `RAZAO_AUXILIAR_DAS_SUBCONTAS` — sem moeda funcional
- `RAZAO_AUXILIAR_DAS_SUBCONTAS_MF` — com moeda funcional

**Quando obrigatorio**:
- Empresas obrigadas ao razao auxiliar a partir do AC 2014 → produzir livro Z RAS desde 2014
- Empresas obrigadas a partir do AC 2015 → desde 2015

**Estrutura I510 (27 campos definidos)**: NAT_SUB_CNT, COD_SUB_CNT, COD_CCUS, CNPJ_INVTD, COD_PATR_ITEM, QTD, IDENT_ITEM, DESCR_ITEM, DATA_RECT_INI, SLD_ITEM_INI, IND_SLD_ITEM_INI, REAL_ITEM, IND_REAL_ITEM, SLD_ITEM_FIN, IND_SLD_ITEM_FIN, SLD_SCNT_INI, IND_SLD_SCNT_INI, DEB_SCNT, CRED_SCNT, SLD_SCNT_FIN, IND_SLD_SCNT_FIN, DATA_LCTO, NR_LCTO, VLR_LCTO, IND_VLR_LCTO, IND_ADOC_INI.

**Tabela NAT_SUB_CNT**: ver registro [I053](bloco_I_lancamentos.md#registro-i053) (codigos 2/3/10/11/12/60/65/70-78/80-86/90-93).

**Regra principal**: SLD_SCNT_FIN = SLD_SCNT_INI + DEB_SCNT + CRED_SCNT (com indicadores D/C).

---

## 1.23 Moeda Funcional

**Quando aplica**: PJs obrigadas a transmitir SPED em moeda funcional diferente da nacional (art. 287 IN 1.700/2017).

**Como sinalizar**: `0000.IDENT_MF = "S"`

**Como preencher**:
- Campos ja existentes nos blocos I (I155, I157, I200, I250, I310, I355) → preencher com valores em MOEDA NACIONAL (sao os que entram na ECF)
- Adicionar campos `_MF` via I020 → valores em MOEDA FUNCIONAL CONVERTIDA PARA REAIS (regras societarias)
- Bloco J → usa valores _MF para validacao (demonstracoes consolidadas refletem moeda funcional)

**Detalhe completo dos campos adicionais MF**: ver [Registro I020](bloco_I_lancamentos.md#registro-i020) e [I155](bloco_I_lancamentos.md#registro-i155).

---

## 1.24 Sociedades em Conta de Participacao (SCP)

- SCPs com obrigatoriedade entregam ECD como **livro proprio** (separado da socia ostensiva)
- 0000.CNPJ e 0030.CNPJ = CNPJ da socia ostensiva
- 0000.COD_SCP = CNPJ da SCP

---

## 1.26 Autenticacao da ECD

- Decreto 8.683/2016: ECDs pos 25/02/2016 autenticadas no momento da transmissao
- Decreto 9.555/2018: ECDs pos 07/11/2018 (PJ nao sujeita ao Registro do Comercio) autenticadas no momento da transmissao
- **Recibo de transmissao = comprovante de autenticacao**

---

## 1.27 Transformacao e Transferencia de Sede

NAO sao mais situacoes especiais. Entregar 1 arquivo unico com info do ultimo dia do periodo. IND_SIT_ESP em branco.

---

## 1.32 Recuperacao da ECD Anterior

**Objetivo**: garantir consistencia aritmetica — saldo final periodo anterior = saldo inicial periodo atual.

**Condicoes para habilitar funcionalidade no PGE atual**:
1. ECD atual em leiaute 8 ou posterior
2. ECD atual e livro principal (IND_ESC=G/R/B)

**Condicoes para listar ECD anterior**:
1. Mesmo CNPJ
2. Mesmo CNPJ_SCP (se houver)
3. ECD anterior assinada
4. Mesmo IND_ESC
5. ECD anterior IMEDIATAMENTE anterior (data final = data inicial-1)

**Recuperacao via arquivo**: botao "Localizar" — arquivo deve estar assinado e nao alterado.

**Criticas na transmissao**: hash da ECD recuperada = hash da ECD anterior ativa na base SPED.

**Criticas algebricas**:
1. Saldo final conta/CC anterior = Saldo inicial conta/CC atual
2. Total Saldos Iniciais Credores = Total Saldos Iniciais Devedores
3. Total Saldos Finais Credores = Total Saldos Finais Devedores
4. Codigo igual de um ano para outro → mesma natureza (nao pode mudar)
5. Se codigo nao mudou, nao deve ter I157

---

## 1.33 Situacoes Especiais e Demonstracoes Contabeis

- PJs **incorporadas/fusionadas/cindidas** levantam balanco especifico ate 30 dias antes do evento
- **Incorporadora** tambem, EXCETO se incorporadora e incorporada sob mesmo controle societario desde AC anterior

---

## 1.34 Mudancas Leiaute 9 — Registro I051 (CRITICO)

A partir do leiaute 9 (AC 2020+):

1. **Chave do I051 mudou**: era [COD_CCUS]+[COD_CTA_REF], passou a ser [COD_CCUS] apenas
2. **REGRA_NATUREZA_CONTA_DIFERENTE virou ERRO** (era aviso) — so mapear contas referenciais para contas contabeis de mesma natureza
3. **1 conta contabil + 1 centro de custos → so 1 conta referencial** (era N:N)

**Exemplo PERMITIDO**:
```
|I050|...|A|1113|111|CaixaZ
|I051|123|101010102|
|I051|456|101010102|

|I050|...|A|1112|111|CaixaX
|I051|123|101010102|  ← OK: mesmo CC para conta diferente
```

**Exemplo PROIBIDO** (a partir do leiaute 9):
```
|I050|...|A|1118|111|Banco
|I051|123|101010201|
|I051|123|101010202|  ← ERRO: mesmo CC mapeia 2 referenciais
```

---

## 1.36 Contas de Natureza Diferente e Codigos Iguais

Resumindo: se codigo da conta e o mesmo de um ano para outro:
1. Saldo final anterior = saldo inicial atual
2. Mesma natureza (NUNCA pode mudar)
3. NAO ha I157 filho (conta nao mudou)

**V1.7 (Nacom)**: contas de compensacao (COD_NAT=05, code 5+) excluidas do BP — natureza propria.

---

## 1.37 Modelo Termo de Verificacao para Fins de Substituicao

PDF p.48. Conteudo obrigatorio:
- Identificacao da escrituracao a ser substituida (titular, CNPJ, NIRE, denominacao, tipo, numero, periodo, hash)
- Descricao pormenorizada dos erros
- Identificacao dos registros a serem substituidos
- Autorizacao para CFC acessar info

Modelo completo no PDF.

---

## 1.43-1.44 Conta Zerada / Nao Movimentada Antes de Mudanca PC

**Causa frequente de erros V22-V29**: contas zeradas no ultimo periodo da ECD anterior NAO sao mapeadas no I157 da ECD posterior — mas deveriam.

**Regra**: TODAS as contas com movimentacao no I155 da ECD anterior (ainda que nao em todos os meses) devem constar no I157 da ECD posterior, mesmo com saldo final zero.

**Motivo**: a ECF precisa recuperar os saldos do plano antigo corretamente.

---

## Resumo Operacional (Resumo Cap 1)

Para uma operacao tipica de ECD anual:

1. **Identificar regime**: Lucro Real/Presumido/Imune? Obrigado ou facultativo?
2. **Recuperar ECD anterior**: arquivo proprio ou da base local PGE
3. **Definir tipo de livro**: G (sem auxiliares), R+A/Z (com auxiliares), B (instituicoes financeiras)
4. **Definir periodo**: anual ou fracionado (>5GB ou situacao especial)
5. **Preencher 0000**: CNPJ, datas, UF, IND_FIN_ESC, IND_GRANDE_PORTE, IDENT_MF, IND_ESC_CONS, IND_MUDANC_PC, COD_PLAN_REF
6. **Preencher plano de contas I050**: minimo 4 niveis, natureza correta, hierarquia
7. **Mapeamentos I051/I052**: referencial (se COD_PLAN_REF) + aglutinacao (para J100/J150)
8. **Saldos I150/I155**: continuidade entre meses + recuperacao anterior
9. **Lancamentos I200/I250**: D+C balanceados, historicos preenchidos
10. **Demonstracoes Bloco J**: BP (J100), DRE (J150), DLPA/DMPL (J210/J215)
11. **Signatarios J930**: contador (900) + responsavel (IND_RESP_LEGAL=S)
12. **9999**: contagem total de linhas
13. **Validar no PVA**: corrigir erros nivel 1 → revalidar → corrigir nivel 2 → revalidar
14. **Assinar**: e-CPF contador + responsavel (e-CNPJ ou e-CPF)
15. **Transmitir via Receitanet**: porta 3456, IP 200.198.239.21
