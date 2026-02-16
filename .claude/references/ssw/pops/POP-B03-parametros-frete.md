# POP-B03 — Configurar Parametros de Frete

> **Categoria**: B — Comercial e Precificacao
> **Prioridade**: P1 (Alta — pode ser causa da simulacao incorreta)
> **Status anterior**: A IMPLANTAR
> **Criado em**: 2026-02-16
> **Executor atual**: Rafael
> **Executor futuro**: Rafael

---

## Objetivo

Configurar os parametros que controlam o calculo de frete no SSW: limites de cotacao, cubagem, desconto maximo, resultado minimo e servicos adicionais. Envolve as opcoes [903](../cadastros/903-parametros-gerais.md)/Frete (parametros gerais), 469 (limites por rota), [423](../comercial/423-parametros-comerciais-cliente.md) (parametros por cliente) e [062](../comercial/062-parametros-frete.md) (parametros de frete).

Este POP e critico porque Rafael **nao conhece a opcao 062**, e essa pode ser a causa dos problemas recorrentes de simulacao incorreta. O POP documenta o que se sabe e marca com [CONFIRMAR] o que precisa ser verificado na pratica.

---

## Trigger

- Setup inicial da CarVia no SSW (configuracao base)
- Simulacao ([004](../operacional/004-emissao-ctrcs.md)) ou cotacao ([002](../operacional/002-consulta-coletas.md)) retornando valores errados (ver POP-B02 para diagnostico)
- Implantacao de nova rota (POP-A10) — revisar parametros
- Necessidade de ajustar limites de desconto para negociacao comercial
- Necessidade de configurar cubagem ou servicos adicionais para cliente especifico

---

## Frequencia

- Setup inicial: **unica vez** (revisao semestral recomendada)
- Ajustes por rota/cliente: por demanda

---

## Pre-requisitos

| Requisito | Opcao SSW | O que verificar |
|-----------|-----------|-----------------|
| Acesso de usuario master/MTZ | [925](../cadastros/925-cadastro-usuarios.md) | Usuario com permissao para alterar 903 |
| Unidades cadastradas | [401](../cadastros/401-cadastro-unidades.md) | Unidades de origem e destino existem |
| Rotas cadastradas | [403](../cadastros/403-rotas.md) | Rotas CAR → destino existem |
| Tabelas de frete ativas | 420 / 417 | Pelo menos uma tabela ativa para testar |
| Tabela NTC (referencia) | [923](../comercial/923-cadastro-tabelas-ntc-generica.md) | Cadastrada para calculo de desconto NTC |
| Clientes cadastrados | [483](../cadastros/483-cadastro-clientes.md) | Para configurar 423 por cliente |

---

## Passo-a-Passo

### ETAPA 1 — Verificar Parametros Gerais (Opcao 903/Frete)

A [opcao 903](../cadastros/903-parametros-gerais.md) e o **coracao do sistema SSW**. A aba Frete controla parametros que afetam TODAS as cotacoes e emissoes.

1. Acessar [opcao **903**](../cadastros/903-parametros-gerais.md) (requer usuario MTZ)
2. Navegar para a secao **Frete**
3. Verificar e configurar:

| Parametro | Valor recomendado CarVia | O que faz |
|-----------|--------------------------|-----------|
| **Cubagem padrao** | **300** Kg/m3 (sugestao SSW) | Usado quando cliente nao tem cubagem especifica na 423. Peso cubado = volume x cubagem |
| **Aprovacao centralizada de tabelas** | **N** (nao) | Se S: tabelas ficam em simulacao ate aprovacao (518). Para CarVia, nao necessario por enquanto |
| **Prazo de vencimento de tabelas** | Definir data adequada | Tabelas vencem nesta data — sistema alerta e desativa |
| **Curva ABC de Clientes** | Configurar criterios | Classificacao por volume faturamento e inadimplencia |

> **ATENCAO**: Mudancas na 903 afetam TODA a transportadora (todos os CNPJs/unidades). Alterar em horario de baixa operacao.

4. Navegar para a secao **Prazos**:

| Parametro | Valor recomendado CarVia | O que faz |
|-----------|--------------------------|-----------|
| **Prazo validade cotacoes** | 30 dias (ajustar conforme necessidade) | Cotacoes contratadas ([002](../operacional/002-consulta-coletas.md)) vencem apos este prazo |
| **ICMS/ISS repassado** | Verificar configuracao | Se impostos sao repassados ou inclusos (CarVia: inclusos) |
| **PIS/COFINS repassado** | Verificar configuracao | Se impostos sao repassados ou inclusos (CarVia: inclusos) |

5. Navegar para a secao **Outros**:

| Parametro | Valor recomendado CarVia | O que faz |
|-----------|--------------------------|-----------|
| **Aprovacao centralizada de despesas** | Avaliar | Se S: despesas (475) precisam aprovacao (560) antes de liquidar |
| **Seguro %** | Configurar custo do seguro | % sobre valor mercadoria — entra no calculo do resultado comercial ([101](../comercial/101-resultado-ctrc.md)) |
| **GRIS custo %** | Configurar custo GRIS | % sobre valor mercadoria — entra no calculo do resultado comercial ([101](../comercial/101-resultado-ctrc.md)) |

> **DICA**: Seguro e GRIS na 903/Outros sao os **custos** da transportadora (usados no resultado comercial da [opcao 101](../comercial/101-resultado-ctrc.md)). Ja o GRIS na tabela de frete e o que a transportadora **cobra** do cliente. Nao confundir.

---

### ETAPA 2 — Configurar Limites de Cotacao (Opcao 469)

A opcao 469 define limites que controlam a negociacao comercial em cotacoes ([002](../operacional/002-consulta-coletas.md)) e resultados de CTRCs.

6. Acessar opcao **469**
7. Configurar limites para cada rota:

| Limite | O que define | Exemplo |
|--------|-------------|---------|
| **Valor Minimo Frete (R$)** | Frete Peso, Frete Valor e Minimo garantidos | R$ 150,00 (frete nunca abaixo deste valor) |
| **Desconto max NTC (%)** | Maximo de desconto sobre tabela NTC ([923](../comercial/923-cadastro-tabelas-ntc-generica.md)) | 50% (nao pode dar mais de 50% de desconto sobre NTC) |
| **Resultado Comercial Minimo (%)** | % minimo de lucro exigido | 10% (frete deve gerar pelo menos 10% de resultado) |
| **Desconto max proposta inicial (%)** | % maximo de desconto sobre proposta inicial | 15% (nao pode descontar mais de 15% na cotacao) |

> **IMPORTANTE**: Limites por grupos (opcao 369) substituem os limites da 469 quando cadastrados para o grupo do cliente. Verificar se a CarVia usa grupos de clientes.

8. Repetir para cada combinacao de rota relevante

> **Se a 469 nao estiver configurada**: A cotacao ([002](../operacional/002-consulta-coletas.md)) pode nao exibir limites, permitindo descontos excessivos ou cotacoes abaixo do custo. Configurar e essencial.

---

### ETAPA 3 — Configurar Parametros por Cliente (Opcao 423)

A [opcao 423](../comercial/423-parametros-comerciais-cliente.md) define parametros comerciais especificos por cliente, sobrescrevendo os padroes da transportadora ([903](../cadastros/903-parametros-gerais.md)).

9. Acessar [opcao **423**](../comercial/423-parametros-comerciais-cliente.md)
10. Informar **CNPJ do cliente**
11. Configurar:

#### 3.1 Cubagem Especifica

| Campo | Valor | Quando configurar |
|-------|-------|-------------------|
| **Cubagem padrao (Kg/m3)** | Valor real do tipo de carga | Quando cubagem padrao (903 = 300) nao reflete a carga do cliente |

**Exemplos CarVia**:
- MotoChefe: motos em caixas (~140x40x60cm, ~60kg) — cubagem real diferente de 300
- NotCo: paletes de leite vegetal (1.000-2.000 kg) — possivelmente cubagem mais alta

> Se cubagem do cliente = 0 na 423, o SSW nao calcula cubagem para este cliente (usa apenas peso real).

#### 3.2 Servicos Adicionais

| Campo | O que configurar | Formato |
|-------|-----------------|---------|
| **Paletizacao** | R$ fixo ou % sobre frete | Se cliente exige paletizacao |
| **Agendamento** | R$ fixo ou % sobre frete | Se cliente exige agendamento de entrega |
| **Separacao** | R$ fixo ou % sobre frete | Se aplica separacao de volumes |
| **Capatazia** | R$ fixo ou % sobre frete | Se aplica movimentacao de carga |
| **Veiculo Dedicado** | R$ fixo ou % sobre frete | Se cliente exige veiculo exclusivo |
| **Devolucao Canhoto NF** | R$ fixo | Se cobra devolucao do canhoto |

> **CarVia hoje**: Provavelmente nenhum servico adicional configurado na 423. Configurar conforme necessidade de cada cliente.

#### 3.3 Desconto Maximo Proposta Inicial

| Campo | O que define | Hierarquia |
|-------|-------------|------------|
| **Max desconto proposta inicial** | % maximo de desconto na cotacao ([002](../operacional/002-consulta-coletas.md)) | [423](../comercial/423-parametros-comerciais-cliente.md) (cliente) > 469 (rota) > 903 (geral) |

12. Gravar configuracao

---

### ETAPA 4 — Investigar Opcao 062 [CONFIRMAR]

> **NOTA CRITICA**: A [opcao 062](../comercial/062-parametros-frete.md) e mencionada na documentacao SSW como "parametros de frete" e e referenciada como pre-requisito na [opcao 101](../comercial/101-resultado-ctrc.md) (Resultado CTRC): "Parametros de frete ([Opcao 062](../comercial/062-parametros-frete.md)): desconto maximo, resultado comercial minimo". Porem, NAO existe documentacao dedicada da [opcao 062](../comercial/062-parametros-frete.md) nos arquivos SSW coletados.

13. [CONFIRMAR] Acessar [opcao **062**](../comercial/062-parametros-frete.md) no SSW
14. [CONFIRMAR] Verificar quais campos estao disponiveis:

| Campo esperado | Baseado em | Relacao |
|----------------|------------|---------|
| Desconto maximo | Referencia na [opcao 101](../comercial/101-resultado-ctrc.md) | Pode ser o mesmo parametro da 469 ou complementar |
| Resultado comercial minimo | Referencia na [opcao 101](../comercial/101-resultado-ctrc.md) | Pode ser o mesmo parametro da 469 ou complementar |
| Custos adicionais | Referencia no CATALOGO_POPS | Mencionado no catalogo como funcao da 062 |

15. [CONFIRMAR] Comparar campos da 062 com a 469:
    - Se sao redundantes: entender qual tem prioridade
    - Se sao complementares: configurar ambos
    - Se a 062 tem campos unicos: documentar e configurar

16. [CONFIRMAR] Anotar todos os campos e valores atuais da 062 para referencia futura

> **HIPOTESE**: A [opcao 062](../comercial/062-parametros-frete.md) pode conter parametros que a 469 nao cobre — como custos adicionais que afetam o resultado comercial. Se a 062 estiver vazia ou com valores errados, isso pode explicar por que a simulacao da 004 "nao calcula certo". Investigar com prioridade.

---

### ETAPA 5 — Testar Configuracoes

Apos configurar os parametros, testar o calculo em dois cenarios:

17. **Teste via cotacao ([002](../operacional/002-consulta-coletas.md))**:
    - Acessar [opcao 002](../operacional/002-consulta-coletas.md)
    - Informar CNPJ de um cliente existente
    - Preencher dados de teste (origem CAR, destino conhecido, peso 500kg, valor R$ 10.000)
    - Simular → verificar:
      - Proposta Inicial esta coerente?
      - Limites aparecem na tela?
      - Desconto funciona dentro dos limites?

18. **Teste via simulacao ([004](../operacional/004-emissao-ctrcs.md))**:
    - Acessar [opcao 004](../operacional/004-emissao-ctrcs.md)
    - Preencher dados normais (remetente, destinatario, NF, peso, valor, placa ARMAZEM)
    - Simular → verificar:
      - Parcelas estao corretas? (comparar com POP-B02)
      - Peso de calculo e o esperado? (real vs cubado)
      - Taxas condicionais aparecem corretamente?

19. **Comparar 002 vs 004**:
    - Mesmos dados → valores devem ser coerentes
    - Se 002 retorna valor diferente de 004: diferenca esperada se cotacao tem desconto aplicado
    - Se divergencia inexplicavel: revisar parametros

20. **Verificar resultado comercial ([101](../comercial/101-resultado-ctrc.md))**:
    - Se CTRC ja emitido: acessar [opcao 101](../comercial/101-resultado-ctrc.md) → link Resultado
    - Receita - Despesas = Resultado %
    - Resultado % deve estar acima do minimo configurado (469/062)

---

## Contexto CarVia

| Aspecto | Hoje | Futuro |
|---------|------|--------|
| **903/Frete** | Provavelmente com valores padrao do setup inicial | Revisado e configurado conforme necessidade CarVia |
| **Cubagem padrao** | Possivelmente 300 Kg/m3 (padrao SSW) | 300 ou ajustado se carga tipica CarVia exige outro valor |
| **Opcao 469** | Possivelmente NAO configurada por rota | Configurada para todas as rotas ativas |
| **Opcao 423** | Possivelmente SEM cubagem por cliente | Cubagem configurada para MotoChefe, NotCo e demais clientes |
| **Opcao 062** | Rafael NAO CONHECE esta opcao | Investigada, documentada e configurada |
| **Limites de cotacao** | Sem limites → descontos sem controle | Limites definidos por rota (469) e por cliente ([423](../comercial/423-parametros-comerciais-cliente.md)) |
| **Servicos adicionais** | Nenhum configurado | Avaliar agendamento/paletizacao por cliente |
| **Resultado minimo** | Sem meta definida | Meta minima definida (sugestao: 10-15%) |

---

## Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Cotacao aceita desconto de 100% | 469 nao configurada para a rota | Acessar 469 e definir desconto maximo |
| Resultado comercial negativo em todos CTRCs | Custos (408) maiores que receita (420) e 062/469 sem minimo | Revisar tabelas 420 vs 408. Configurar resultado minimo |
| Cubagem inflando peso de calculo | Cubagem padrao 300 inadequada para carga leve/volumosa | [Opcao 423](../comercial/423-parametros-comerciais-cliente.md) → definir cubagem real por cliente |
| Cubagem nao calculada | Cubagem do cliente = 0 na 423 | Intencional (usa peso real) ou configurar valor correto |
| Taxas de servico nao cobradas | 423 nao configurada para o cliente | Acessar 423 → configurar servicos adicionais |
| Aprovacao centralizada bloqueando tabelas | 903/Frete → Aprovacao = S mas ninguem aprova (518) | Desligar aprovacao centralizada (903/Frete = N) ou aprovar na 518 |
| [Opcao 903](../cadastros/903-parametros-gerais.md) nao acessivel | Usuario nao e MTZ ou sem permissao | Trocar para unidade MTZ. Verificar grupo do usuario na 918 |
| Limites da 469 nao funcionam | Limites da 369 (grupo) substituindo | Verificar se cliente pertence a grupo (583) com limites proprios |
| [CONFIRMAR] 062 vazia ou com valores incorretos | Nunca configurada | Investigar campos e preencher |

---

## Verificacao Playwright

| Ponto de verificacao | Como verificar |
|---------------------|----------------|
| 903/Frete configurada | [Opcao 903](../cadastros/903-parametros-gerais.md) → aba Frete → cubagem padrao preenchida |
| 903/Prazos configurada | [Opcao 903](../cadastros/903-parametros-gerais.md) → aba Prazos → prazo cotacao e impostos definidos |
| 469 por rota | Opcao 469 → filtrar por rota → limites preenchidos |
| 423 por cliente | [Opcao 423](../comercial/423-parametros-comerciais-cliente.md) → CNPJ cliente → cubagem e servicos configurados |
| [CONFIRMAR] 062 | [Opcao 062](../comercial/062-parametros-frete.md) → verificar campos disponiveis e valores |
| Cotacao respeita limites | [Opcao 002](../operacional/002-consulta-coletas.md) → simular → limites exibidos na tela |
| Resultado minimo funciona | [Opcao 002](../operacional/002-consulta-coletas.md) → tentar desconto abaixo do Min RC % → bloqueio |
| Cubagem correta no CTRC | [Opcao 004](../operacional/004-emissao-ctrcs.md) → simular → peso calculo coerente com cubagem |

---

## POPs Relacionados

| POP | Relacao |
|-----|---------|
| POP-B02 | Formacao de preco — entender todos os componentes antes de configurar |
| POP-B01 | Cotar frete — usa os limites e parametros configurados aqui |
| POP-A07 | Cadastrar tabelas de preco — tabelas que serao controladas por estes parametros |
| POP-A06 | Cadastrar custos/comissoes — custos que alimentam resultado comercial |
| POP-A10 | Implantar nova rota — deve incluir revisao de parametros (469, 423) |
| POP-A01 | Cadastrar cliente — 423 complementa o cadastro do cliente |

---

## Historico de Revisoes

| Data | Alteracao | Autor |
|------|-----------|-------|
| 2026-02-16 | Criacao inicial — opcoes [903](../cadastros/903-parametros-gerais.md), 469, [423](../comercial/423-parametros-comerciais-cliente.md) e [062](../comercial/062-parametros-frete.md) [CONFIRMAR] com contexto CarVia | Claude (Agente Logistico) |
