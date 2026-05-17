# Manual ECD Leiaute 9 — Indice Mestre

**Fonte**: Anexo ao Ato Declaratorio Executivo Cofis no 01/2026 — Atualizacao janeiro de 2026
**PDF original**: `~/Manual_de_Orientação_da_ECD_Leiaute_9_janeiro_2026.pdf` (235 paginas)
**Valido**: Anos-calendario 2020 em diante (codigo I010.COD_VER_LC = `9.00`)

> Este indice e organizado para **consulta rapida durante debugging do SPED ECD**.
> Cada registro tem: hierarquia, ocorrencia, campos chave, obrigatoriedade por tipo de livro, regras criticas, pagina no PDF original.

---

## Mapa de Arquivos

| Arquivo | Conteudo | Pags PDF |
|---------|----------|----------|
| [01_informacoes_gerais.md](01_informacoes_gerais.md) | Cap 1.1-1.44: legislacao, prazos, hash, RAS, moeda funcional, SCP, substituicao, recuperacao ECD anterior | 5-51 |
| [02_dados_tecnicos.md](02_dados_tecnicos.md) | Cap 2: formato campos (C/N), data, periodo, codigos, tabelas internas/externas | 52-56 |
| [bloco_0_abertura.md](bloco_0_abertura.md) | Bloco 0 — Abertura, Identificacao e Referencias (8 registros) | 64-87 |
| [bloco_C_recuperada.md](bloco_C_recuperada.md) | Bloco C — Informacoes Recuperadas da ECD Anterior (10 registros) | 88-100 |
| [bloco_I_lancamentos.md](bloco_I_lancamentos.md) | Bloco I — Lancamentos Contabeis (26 registros) **PRINCIPAL** | 101-168 |
| [bloco_J_demonstracoes.md](bloco_J_demonstracoes.md) | Bloco J — Demonstracoes Contabeis (13 registros) | 169-207 |
| [bloco_K_conglomerados.md](bloco_K_conglomerados.md) | Bloco K — Conglomerados Economicos (11 registros) | 208-228 |
| [bloco_9_encerramento.md](bloco_9_encerramento.md) | Bloco 9 — Controle e Encerramento (4 registros) | 229-232 |
| [04_regras_validacao.md](04_regras_validacao.md) | Cap 4: Regras de Validacao Nivel 1 e Nivel 2 | 233-235 |

---

## Mapa de Blocos

| Bloco | Descricao | Registros | Obrigatorio | Notas |
|-------|-----------|-----------|-------------|-------|
| **0** | Abertura, Identificacao e Referencias | 0000, 0001, 0007, 0020, 0035, 0150, 0180, 0990 | Sim | Sempre primeiro bloco |
| **C** | Informacoes Recuperadas da ECD Anterior | C001, C040, C050, C051, C052, C150, C155, C600, C650, C990 | Nao | Preenchido pelo PGE apos recuperacao |
| **I** | Lancamentos Contabeis | I001, I010, I012, I015, I020, I030, I050, I051, I052, I053, I075, I100, I150, I155, I157, I200, I250, I300, I310, I350, I355, I500, I510, I550, I555, I990 | Sim | **Maior bloco — plano de contas, lancamentos, saldos** |
| **J** | Demonstracoes Contabeis | J001, J005, J100, J150, J210, J215, J800, J801, J900, J930, J932, J935, J990 | Sim | DRE, BP, DLPA, DMPL, signatarios |
| **K** | Conglomerados Economicos | K001, K030, K100, K110, K115, K200, K210, K300, K310, K315, K990 | Condicional (IND_ESC_CONS=S) | Demonstracoes consolidadas |
| **9** | Controle e Encerramento | 9001, 9900, 9990, 9999 | Sim | Ultimo bloco |

---

## Tabela Mestre de Registros (Resumo)

| Reg | Bloco | Hier | Ocor | Descricao Curta | Arquivo |
|-----|-------|------|------|-----------------|---------|
| **0000** | 0 | 0 | 1:1 | Abertura arquivo + identif PJ | [bloco_0](bloco_0_abertura.md#registro-0000) |
| **0001** | 0 | 1 | 1:1 | Abertura Bloco 0 | [bloco_0](bloco_0_abertura.md#registro-0001) |
| **0007** | 0 | 2 | 0:N | Outras inscricoes cadastrais | [bloco_0](bloco_0_abertura.md#registro-0007) |
| **0020** | 0 | 2 | 0:N | Escrituracao descentralizada | [bloco_0](bloco_0_abertura.md#registro-0020) |
| **0035** | 0 | 2 | 0:N | Identificacao das SCP | [bloco_0](bloco_0_abertura.md#registro-0035) |
| **0150** | 0 | 2 | 0:N | Tabela cadastro participante | [bloco_0](bloco_0_abertura.md#registro-0150) |
| **0180** | 0 | 3 | 1:N | Relacionamento com participante | [bloco_0](bloco_0_abertura.md#registro-0180) |
| **0990** | 0 | 1 | 1:1 | Encerramento Bloco 0 | [bloco_0](bloco_0_abertura.md#registro-0990) |
| **C001** | C | 1 | 1:1 | Abertura Bloco C | [bloco_C](bloco_C_recuperada.md#registro-c001) |
| **C040** | C | 2 | 1:1 | Identif ECD recuperada | [bloco_C](bloco_C_recuperada.md#registro-c040) |
| **C050** | C | 3 | 1:N | Plano de contas recuperado | [bloco_C](bloco_C_recuperada.md#registro-c050) |
| **C051** | C | 4 | 0:N | Plano contas referencial rec | [bloco_C](bloco_C_recuperada.md#registro-c051) |
| **C052** | C | 4 | 1:N | Codigos aglutinacao rec | [bloco_C](bloco_C_recuperada.md#registro-c052) |
| **C150** | C | 3 | 1:1 | Saldos periodicos rec — periodo | [bloco_C](bloco_C_recuperada.md#registro-c150) |
| **C155** | C | 4 | 1:N | Detalhe saldos periodicos rec | [bloco_C](bloco_C_recuperada.md#registro-c155) |
| **C600** | C | 3 | 1:N | Demonstracoes contabeis rec | [bloco_C](bloco_C_recuperada.md#registro-c600) |
| **C650** | C | 4 | 1:N | DRE recuperada | [bloco_C](bloco_C_recuperada.md#registro-c650) |
| **C990** | C | 1 | 1:1 | Encerramento Bloco C | [bloco_C](bloco_C_recuperada.md#registro-c990) |
| **I001** | I | 1 | 1:1 | Abertura Bloco I | [bloco_I](bloco_I_lancamentos.md#registro-i001) |
| **I010** | I | 2 | 1:1 | Identif escrituracao contabil | [bloco_I](bloco_I_lancamentos.md#registro-i010) |
| **I012** | I | 3 | 0:N | Livros auxiliares ao Diario | [bloco_I](bloco_I_lancamentos.md#registro-i012) |
| **I015** | I | 4 | 1:N | Contas da escrituracao resumida | [bloco_I](bloco_I_lancamentos.md#registro-i015) |
| **I020** | I | 3 | 0:N | Campos adicionais (moeda func) | [bloco_I](bloco_I_lancamentos.md#registro-i020) |
| **I030** | I | 3 | 1:1 | Termo de abertura do livro | [bloco_I](bloco_I_lancamentos.md#registro-i030) |
| **I050** | I | 3 | 1:N | **Plano de Contas** | [bloco_I](bloco_I_lancamentos.md#registro-i050) |
| **I051** | I | 4 | 1:N | **Plano de Contas Referencial** | [bloco_I](bloco_I_lancamentos.md#registro-i051) |
| **I052** | I | 4 | 1:N | Codigos de aglutinacao | [bloco_I](bloco_I_lancamentos.md#registro-i052) |
| **I053** | I | 4 | 1:N | Subcontas correlatas | [bloco_I](bloco_I_lancamentos.md#registro-i053) |
| **I075** | I | 3 | 0:N | Tabela historico padronizado | [bloco_I](bloco_I_lancamentos.md#registro-i075) |
| **I100** | I | 3 | 0:N | Centro de custos | [bloco_I](bloco_I_lancamentos.md#registro-i100) |
| **I150** | I | 3 | 1:12 | **Saldos periodicos — periodo** | [bloco_I](bloco_I_lancamentos.md#registro-i150) |
| **I155** | I | 4 | 1:N | **Detalhe saldos periodicos** | [bloco_I](bloco_I_lancamentos.md#registro-i155) |
| **I157** | I | 5 | 1:N | Transferencia saldos plano anterior | [bloco_I](bloco_I_lancamentos.md#registro-i157) |
| **I200** | I | 3 | 1:N | **Lancamento contabil** | [bloco_I](bloco_I_lancamentos.md#registro-i200) |
| **I250** | I | 4 | 1:N | **Partidas do lancamento** | [bloco_I](bloco_I_lancamentos.md#registro-i250) |
| **I300** | I | 3 | 0:N | Balancetes diarios — data | [bloco_I](bloco_I_lancamentos.md#registro-i300) |
| **I310** | I | 4 | 1:N | Detalhes balancete diario | [bloco_I](bloco_I_lancamentos.md#registro-i310) |
| **I350** | I | 3 | 1:12 | Saldos contas resultado antes encerr | [bloco_I](bloco_I_lancamentos.md#registro-i350) |
| **I355** | I | 4 | 1:N | Detalhe saldos contas result | [bloco_I](bloco_I_lancamentos.md#registro-i355) |
| **I500** | I | 3 | 0:N | Parametros razao auxiliar parametriz | [bloco_I](bloco_I_lancamentos.md#registro-i500) |
| **I510** | I | 3 | 0:N | Definicao campos razao auxiliar | [bloco_I](bloco_I_lancamentos.md#registro-i510) |
| **I550** | I | 3 | 0:N | Detalhes razao auxiliar parametriz | [bloco_I](bloco_I_lancamentos.md#registro-i550) |
| **I555** | I | 4 | 0:N | Totais razao auxiliar parametriz | [bloco_I](bloco_I_lancamentos.md#registro-i555) |
| **I990** | I | 1 | 1:1 | Encerramento Bloco I | [bloco_I](bloco_I_lancamentos.md#registro-i990) |
| **J001** | J | 1 | 1:1 | Abertura Bloco J | [bloco_J](bloco_J_demonstracoes.md#registro-j001) |
| **J005** | J | 2 | 1:12 | Demonstracoes contabeis (cabec) | [bloco_J](bloco_J_demonstracoes.md#registro-j005) |
| **J100** | J | 3 | 1:N | **Balanco Patrimonial** | [bloco_J](bloco_J_demonstracoes.md#registro-j100) |
| **J150** | J | 3 | 1:N | **DRE** | [bloco_J](bloco_J_demonstracoes.md#registro-j150) |
| **J210** | J | 3 | 1:N | DLPA/DMPL | [bloco_J](bloco_J_demonstracoes.md#registro-j210) |
| **J215** | J | 4 | 1:N | Fato contabil que altera PL | [bloco_J](bloco_J_demonstracoes.md#registro-j215) |
| **J800** | J | 3 | 1:N | Outras informacoes | [bloco_J](bloco_J_demonstracoes.md#registro-j800) |
| **J801** | J | 3 | 0:1 | Termo verificacao substituicao | [bloco_J](bloco_J_demonstracoes.md#registro-j801) |
| **J900** | J | 2 | 1:1 | Termo de encerramento | [bloco_J](bloco_J_demonstracoes.md#registro-j900) |
| **J930** | J | 3 | 1:N | Signatarios da escrituracao | [bloco_J](bloco_J_demonstracoes.md#registro-j930) |
| **J932** | J | 3 | 1:N | Signatarios termo verificacao | [bloco_J](bloco_J_demonstracoes.md#registro-j932) |
| **J935** | J | 3 | 1:N | Auditores independentes | [bloco_J](bloco_J_demonstracoes.md#registro-j935) |
| **J990** | J | 1 | 1:1 | Encerramento Bloco J | [bloco_J](bloco_J_demonstracoes.md#registro-j990) |
| **K001** | K | 1 | 1:1 | Abertura Bloco K | [bloco_K](bloco_K_conglomerados.md#registro-k001) |
| **K030** | K | 2 | 0:1 | Periodo escrituracao consolidada | [bloco_K](bloco_K_conglomerados.md#registro-k030) |
| **K100** | K | 3 | 0:N | Empresas consolidadas | [bloco_K](bloco_K_conglomerados.md#registro-k100) |
| **K110** | K | 4 | 0:N | Eventos societarios | [bloco_K](bloco_K_conglomerados.md#registro-k110) |
| **K115** | K | 5 | 0:N | Empresas participantes evento | [bloco_K](bloco_K_conglomerados.md#registro-k115) |
| **K200** | K | 2 | 1:N | Plano contas consolidado | [bloco_K](bloco_K_conglomerados.md#registro-k200) |
| **K210** | K | 3 | 1:N | Mapeamento plano consolidado | [bloco_K](bloco_K_conglomerados.md#registro-k210) |
| **K300** | K | 3 | 0:N | Saldos contas consolidadas | [bloco_K](bloco_K_conglomerados.md#registro-k300) |
| **K310** | K | 4 | 0:N | Detentoras parcelas elimin | [bloco_K](bloco_K_conglomerados.md#registro-k310) |
| **K315** | K | 5 | 0:N | Contrapartes parcelas elimin | [bloco_K](bloco_K_conglomerados.md#registro-k315) |
| **K990** | K | 1 | 1:1 | Encerramento Bloco K | [bloco_K](bloco_K_conglomerados.md#registro-k990) |
| **9001** | 9 | 1 | 1:1 | Abertura Bloco 9 | [bloco_9](bloco_9_encerramento.md#registro-9001) |
| **9900** | 9 | 2 | 1:N | Registros do arquivo (contadores) | [bloco_9](bloco_9_encerramento.md#registro-9900) |
| **9990** | 9 | 1 | 1:1 | Encerramento Bloco 9 | [bloco_9](bloco_9_encerramento.md#registro-9990) |
| **9999** | 9 | 0 | 1:1 | Encerramento arquivo digital | [bloco_9](bloco_9_encerramento.md#registro-9999) |

---

## Composicao dos Livros (G / R / A / B / Z)

| Sigla | Tipo de Escrituracao |
|-------|----------------------|
| **G** | Livro Diario (completo, sem escrituracao auxiliar) |
| **R** | Livro Diario com Escrituracao Resumida (com escrituracao auxiliar) |
| **A** | Livro Diario Auxiliar ao Diario com Escrituracao Resumida |
| **B** | Livro Balancetes Diarios e Balancos |
| **Z** | Razao Auxiliar |

**Legenda obrigatoriedade**: `O` = Obrigatorio · `F` = Facultativo · `F(n)` = Obrigatorio sob condicao (n) · `N` = Nao se aplica

Tabela completa de obrigatoriedade por registro x tipo de livro: ver final de [bloco_0_abertura.md](bloco_0_abertura.md#composicao-dos-livros).

---

## Condicionais de Obrigatoriedade (Notas Cap 3.5)

| Nota | Aplica-se a... | Condicao |
|------|----------------|----------|
| **(1)** | 0180 | Obrigatorio se existe 0150 |
| **(2)** | I355 | Obrigatorio se existe I350 |
| **(3)** | I155 | Obrigatorio se existe I150 |
| **(4)** | I051 | Obrigatoriedade definida pelo orgao do plano referencial |
| **(5)** | J100, J150 | Obrigatorios se J005 corresponde ao final do exercicio social |
| **(6)** | 0035 | Obrigatorio se 0000.TIP_ECD = 1 (sociedade ostensiva de SCP) |
| **(7)** | I020 | Obrigatorio se 0000.IDENT_MF = "S" (moeda funcional) |
| **(8)** | J801 | Obrigatorio se 0000.IND_FIN_ESC = 1 (Substituta) |
| **(9)** | K001, K990 | Obrigatorios se 0000.IND_ESC_CONS = "S" e (mes DT_FIN = 12 ou IND_SIT_ESP preenchido) |
| **(10)** | K110 | Obrigatorio se K100.EVENTO = "S" |
| **(11)** | K115 | Obrigatorio se K110.EVENTO em [1..6] (aquisicao/alienacao/fusao/cisao/incorp) |
| **(12)** | K310 | Obrigatorio se K300.VAL_EL > 0 |
| **(13)** | K210 | Obrigatorio se K200.IND_CTA = "A" (analitica) |
| **(14)** | J932 | Obrigatorio se 0000.IND_FIN_ESC = 1 (Substituta) |
| **(15)** | J935 | Obrigatorio se 0000.IND_GRANDE_PORTE = 1 (auditoria independente) |
| **(16)** | 0020 | Obrigatorio se 0000.IND_CENTRALIZADA = 1 (descentralizada) |
| **(17)** | I157 | Pelo menos 1 se 0000.IND_MUDANCA_PC = 1 (alteracao plano contas) |
| **(18)** | C040 | Importado so se ECD recuperada esta assinada |
| **(19)** | C050 | Obrigatorio se existe C040 e ECD assinada |
| **(20)** | C155 | Obrigatorio se existe C150 e ECD assinada |
| **(21)** | I051, C051 | Nao deve existir se 0000.COD_PLAN_REF vazio |
| **(22)** | C650 | Obrigatorio se existe C600 |
| **(23)** | C051 | Nao deve existir se C040.COD_PLAN_REF vazio. Obrigatorio se C040 + COD_PLAN_REF preenchido + assinada |

---

## Glossario Rapido

- **PGE**: Programa Gerador de Escrituracao (validador oficial Receita Federal)
- **ECD**: Escrituracao Contabil Digital
- **ECF**: Escrituracao Contabil Fiscal (outra obrigacao acessoria, complementar)
- **SCP**: Sociedade em Conta de Participacao
- **NIRE**: Numero de Identificacao do Registro de Empresas (Junta Comercial)
- **PL**: Patrimonio Liquido
- **DRE**: Demonstracao do Resultado do Exercicio
- **BP**: Balanco Patrimonial
- **DLPA**: Demonstracao de Lucros ou Prejuizos Acumulados
- **DMPL**: Demonstracao das Mutacoes do Patrimonio Liquido
- **RAS**: Razao Auxiliar das Subcontas (Lei 12.973/2014)
- **IND_DC**: Indicador Devedora/Credora ("D" / "C") — VL_CTA sempre positivo, sinal vem deste campo
- **COD_NAT** (I050): Natureza da conta (01-Ativo, 02-Passivo, 03-PL, 04-Receita, 05-Custos/Despesas, 07-Compensacao, 09-Outras)
- **IND_CTA**: Indicador tipo conta ("S" sintetica, "A" analitica)
- **NIVEL** (I050): nivel hierarquico do plano de contas (1, 2, 3, ...)
- **COD_PLAN_REF**: codigo do plano referencial da RFB (1-PJ Lucro Real, 2-Lucro Presumido, etc.)

---

## Convencoes Deste Manual Refatorado

- **Tabela de campos**: `| # | Campo | Tipo | Tam | Dec | Obrig | Valores |`
  - Tipo: `C` alfanumerico, `N` numerico
  - Tam: tamanho exato. `-` significa max 255 (C) ou ilimitado (N)
  - Dec: casas decimais. `-` significa nao se aplica
  - Obrig: `S` Sim, `N` Nao
- **Regras de validacao**: listadas com nome (`REGRA_X`) e descricao curta. Detalhe completo no PDF original.
- **Tabelas internas/externas**: codigos enumerados quando pequenos; para tabelas grandes (UF, IBGE), referenciar fonte.
- **Exemplo de preenchimento**: linha real do arquivo com prefixo `|` entre campos.
