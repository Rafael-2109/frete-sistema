<!-- doc:meta
tipo: explanation
camada: L3
sot_de: curadoria verificada do README_MAPEAMENTO_SEMANTICO (jun/2025) para enriquecer o text_to_SQL — proposta aguardando aprovacao do Rafael
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Curadoria semantica do README_MAPEAMENTO -> enriquecimento text_to_SQL (proposta)

> **Papel:** proposta CURADA e VERIFICADA de enriquecimento do text_to_SQL a partir do `README_MAPEAMENTO_SEMANTICO_COMPLETO.md` (jun/2025). Cada item foi checado contra os schemas/overlays/models ATUAIS (existe? ja coberto? ainda verdade?). NADA aplicado ainda — overlays sao zona NAO-TOCAR (text_to_SQL ativo).

## Contexto

Rafael pediu para curar o README (6+ meses) e ver o que enriquece o text_to_SQL, sem adicionar as cegas. Verificacao por 11 modelos (workflow read-only). Resultado: 152 ja-cobertos (nao re-adicionar), 78 lacunas reais (ADICIONAR), 10 drift descartados, 4 incertos, 48 business_rules de negocio propostas. Aplicacao via OVERLAYS (`schemas/overlays/*.json` — camada de curadoria; contrato: overlay carrega `business_rules`/`query_hints`/`lineage`, NAO field descriptions, que moram na fonte/modelo).

**APLICADO (2026-06-15):** criado overlay novo `overlays/despesas_extras.json` (5 business_rules verificados; SERVIDA; carga validada via SchemaProvider).

**NAO aplicavel (descoberto na verificacao contra catalog.json):** `usuarios` e `relatorio_faturamento_importado` estao em `tabelas_bloqueadas` — o text_to_SQL nao as serve, logo overlay nelas seria inerte. A curadoria desses 2 fica como REFERENCIA neste report (parte do conhecimento de `relatorio_faturamento_importado`, grao header, pode aplicar-se a `faturamento_produto` (grao item, SERVIDA, JA tem overlay) — avaliar adicao coordenada).

**Follow-up coordenado (zona ativa, nao feito agora):** (a) 78 field descriptions -> model `info={'desc':...}` na fonte; (b) adicoes de `business_rules` aos overlays JA existentes (separacao, embarque_itens, embarques, entregas_monitoradas, transportadoras, contatos_agendamento, cidades, faturamento_produto).

## Indice

- [PEDIDO](#pedido)
- [EMBARQUEITEM](#embarqueitem)
- [Embarque](#embarque)
- [ENTREGAMONITORADA](#entregamonitorada)
- [RELATORIOFATURAMENTOIMPORTADO](#relatoriofaturamentoimportado)
- [DESPESAEXTRA](#despesaextra)
- [Transportadora](#transportadora)
- [USUARIO](#usuario)
- [CONTATOAGENDAMENTO](#contatoagendamento)
- [CIDADE](#cidade)

---

## PEDIDO

Tabela: `separacao (VIEW pedidos = tabela bloqueada; mv_pedidos para agregacoes/contadores)` · overlay existe: True

**business_rules propostas (overlay):**
- PEDIDOS E UMA VIEW (NAO uma tabela): A VIEW 'pedidos' agrega dados de 'separacao' (GROUP BY separacao_lote_id + num_pedido), somando os campos de separacao (separacao.valor_saldo, separacao.peso, quantidades) por lote. Para queries diretas use 'separacao' (dados frescos, por item/produto) ou 'mv_pedidos' (snapshot para contadores/agregacoes, tolerancia de staleness ~30min). A VIEW pedidos esta em tabelas_bloqueadas.
- SEPARACAO = UNIDADE LOGISTICA: Um mesmo num_pedido pode ter multiplas linhas em separacao (multiplos lotes, um por embarque parcial). separacao_lote_id e o agrupador — agrupa todos os itens/produtos de um mesmo lote de separacao.
- RASTREAR PEDIDO -> NF FATURADA: JOIN separacao.num_pedido = faturamento_produto.origem (campo 'origem' em faturamento_produto e o num_pedido do ERP). Indice idx_faturamento_pedido confirma uso frequente.
- STATUS CALCULADO vs STATUS ARMAZENADO: O campo 'status' em separacao e auto-gerenciado por event listener (valores: PREVISAO, ABERTO, COTADO, FATURADO). O status visual exibido ao usuario e status_calculado (propriedade Python) que combina status + nf_cd. COTADO inclui pedidos FOB (sem cotacao de frete real). EMBARCADO deixou de ser status e virou badge visual independente via data_embarque.
- NF_CD SOBREPOE STATUS: Quando nf_cd=True, o status exibido e sempre 'NF no CD' independente do status armazenado. Indica que a mercadoria voltou ao CD e precisa de nova contratacao de frete para reentrega.
- BUSCA POR CLIENTE: Prefira cnpj_cpf para cruzamento entre tabelas (mais estavel que raz_social_red). Clientes de redes (atacado/atacarejo) podem ter prefixo de CNPJ identico entre filiais, mas ha redes com CNPJs totalmente distintos — use ILIKE no nome apenas como fallback ou complemento.
- DATA_EMBARQUE CONTROLADA PELA PORTARIA: O campo data_embarque em separacao e setado exclusivamente pelo modulo de portaria quando o veiculo sai (portaria/routes.py), NAO pelo modulo de embarques. Limpo em cancelamento de embarque.

**field descriptions / hints a adicionar (10):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `num_pedido` | SIM | Numero do pedido no ERP (equivale a 'pdd' na linguagem do comercial). Para rastrear NF emitida: JOIN com faturamento_produto ON faturamento_produto.origem = separacao.num_pedido. |
| `data_pedido` | SIM | Data de criacao do pedido no ERP (pode ser nulo). Tambem chamada de 'data do pdd' pelo comercial. Diferente de expedicao (data de saida) e agendamento (data de entrega no cliente). |
| `cnpj_cpf` | PARCIAL | CNPJ ou CPF do cliente. Mais confiavel que raz_social_red para cruzamento entre tabelas. Atencao: clientes de rede (atacado/atacarejo) podem ter mesmo prefixo de CNPJ entre filiais, mas nao e unive... |
| `raz_social_red` | SIM | Nome (razao social) do cliente. Sinonimos: cliente, nome do cliente. Para busca por nome use ILIKE '%termo%'. Para cruzamento entre tabelas prefira cnpj_cpf (mais estavel). |
| `observ_ped_1` | SIM | Observacao livre inserida pelo comercial no ERP. Pode conter instrucoes criticas para PCP/producao/logistica (ex: 'entrega imediata', 'producao especifica necessaria'). Truncado a 700 chars ao salvar. |
| `agendamento` | SIM | Data de agendamento de entrega no cliente. Quando preenchido, a entrega e mandatoria nessa data — diversos clientes exigem agendamento previo. Distinto de expedicao (saida do CD). |
| `status` | PARCIAL | Status do pedido. Valores: PREVISAO, ABERTO, COTADO, FATURADO, NF no CD. COTADO = em embarque ativo (sem NF) — inclui pedidos FOB sem cotacao de frete real. EMBARCADO nao e mais um status (virou ba... |
| `nf_cd` | SIM | Flag: mercadoria retornou ao CD sem entrega concluida. Quando True, sobrepoe qualquer outro status e torna status_calculado = 'NF no CD', indicando necessidade de nova contratacao de frete para ree... |
| `rota` | SIM | Agrupamento macro de regioes para roteirizacao (cada rota abrange varios estados). Valores especiais: 'RED' (redespacho), 'FOB' (cliente retira). Derivado do cod_uf via CadastroRota. |
| `codigo_ibge` | SIM | Codigo IBGE do municipio (unico por municipio+estado). Usado para identificar transportadora e tabela de frete correta via JOIN com localidades/vinculos. Derivado de cidade_normalizada + uf_normali... |

## EMBARQUEITEM

Tabela: `embarque_itens` · overlay existe: True

**business_rules propostas (overlay):**
- Cada EmbarqueItem representa 1 pedido dentro do embarque (cardinalidade 1 pedido : 1 item). Os campos tabela_* preenchidos em EmbarqueItem indicam obrigatoriamente tipo_carga=FRACIONADA no embarque pai; para tipo_carga=DIRETA, os campos tabela_* ficam em Embarque e sao rateados por peso entre os itens.
- Snapshot de rastreabilidade de frete fracionado: os campos tabela_* em EmbarqueItem sao gravados no momento da cotacao para garantir que alteracoes posteriores na tabela de frete nao alterem fretes fechados. Carga FRACIONADA: 1 CNPJ = 1 entrega = 1 CT-e = 1 linha de frete, portanto cada EmbarqueItem pode ter sua propria tabela.
- Para lancamento de fretes: TODOS os itens com status='ativo' do embarque devem ter nota_fiscal preenchida. Queries de validacao devem filtrar sempre por status='ativo' (itens cancelados permanecem na tabela para rastreabilidade).
- Redespacho (rota=RED): uf_destino='SP' e cidade_destino='Guarulhos' independentemente do UF/cidade real do cliente. Para obter UF real do cliente em pedidos de redespacho, consultar separacao.cod_uf ou separacao.cidade.
- FOB: nao ha cotacao de frete calculada; uf_destino e cidade_destino ficam com dados do cliente mas sao ignorados no calculo. cidade_destino pode conter nome da transportadora coletora ou estar vazio — sem padrao definido para FOB.

**field descriptions / hints a adicionar (18):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `volumes` | PARCIAL | Nacom: NULL (separacao fisica nao implementada; impressao da folha de separacao usa este campo mas nao exige preenchimento). CarVia: preenchido automaticamente via embarque_carvia_service. Filtrar ... |
| `peso` | SIM | Propagado de Separacao.peso; re-sincronizado no faturamento pois pode haver divergencia entre produtos/qtds do pedido original e a NF efetivamente faturada (sync_totais_service, atualizar_pes... |
| `valor` | SIM | Propagado de Separacao.valor_saldo; re-sincronizado no faturamento pois pode haver divergencia de produtos, qtds e preco entre o pedido inserido e a NF faturada. |
| `status` | SIM | Valores: 'ativo' / 'cancelado'. Item cancelado mantem registro para rastreabilidade; ao cancelar: NF e apagada, pedido retorna ao status 'Aberto'. Para lancar fretes, TODOS os itens com status='ati... |
| `uf_destino` | SIM | UF de ENTREGA, nao UF cadastral do cliente. Regras: rota=RED (redespacho) -> sempre 'SP' (entrega em Guarulhos/SP); CIF -> UF real do cliente via LocalizacaoService; FOB -> UF do cliente mas ignora... |
| `cidade_destino` | SIM | Cidade de ENTREGA. Regras: rota=RED -> sempre 'Guarulhos' (ponto de redespacho em SP); CIF -> cidade real do cliente; FOB -> sem padrao, pode estar vazio ou com nome da transportadora coletora. Nao... |
| `tabela_nome_tabela` | SIM | Nome da tabela de frete usada na cotacao deste item (tipo_carga=FRACIONADA). Tabelas sao unicas por combinacao (transportadora, nome_tabela, uf_destino, modalidade). Snapshot gravado para rastreabi... |
| `tabela_valor_kg` | SIM | R$/kg cobrado pela transportadora. Sinonimos: 'frete peso', 'frete kg', 'valor do kg', 'frete excedente', 'kg excedente'. Multiplicado pelo peso (ou frete_minimo_peso se maior) no calculo base do f... |
| `tabela_frete_minimo_valor` | SIM | Valor minimo de frete em R$: se o frete calculado for menor que este valor, aplica-se este como piso (max(frete_calculado, frete_minimo_valor)). |
| `tabela_frete_minimo_peso` | SIM | Peso minimo em kg para base de calculo: se peso do pedido for menor que este valor, usa-se este como piso (max(peso_pedido, frete_minimo_peso)). Sinonimos: 'frete minimo por peso', 'peso minimo do ... |
| `tabela_pedagio_por_100kg` | SIM | R$ por fração de 100kg: cobra-se 1 unidade de pedagio para cada 100kg inteiros ou fracao (arredondamento para cima). Formula: ceil(peso / 100) * pedagio_por_100kg. Sinonimos: 'pedagio', 'valor do p... |
| `tabela_valor_tas` | SIM | R$ fixo por CTE (Taxa de Administracao SEFAZ). Em carga FRACIONADA: 1 CNPJ = 1 entrega = 1 CT-e = 1 TAS. Sinonimos: 'tas', 'taxa do sefaz', 'tarifa do sefaz'. |
| `tabela_percentual_adv` | SIM | % Ad Valorem (seguro da carga) cobrado sobre o valor da mercadoria. Sinonimos: 'adv', 'advalorem', 'seguro da carga', 'seguro', 'valor do seguro'. % * valor_mercadoria. |
| `tabela_percentual_rca` | SIM | % de RCA (Responsabilidade Civil do Transportador Aquaviario): seguro maritimo/fluvial da carga. Sinonimos: 'rca', 'seguro maritimo'. % * valor_mercadoria. |
| `tabela_valor_despacho` | SIM | R$ fixo por CT-e emitido para cobrir custos administrativos de documentacao de transporte. Sinonimos: 'despacho', 'tarifa de despacho'. |
| `tabela_valor_cte` | SIM | R$ fixo por CT-e emitido pela transportadora. Sinonimos: 'taxa de cte', 'tarifa de cte'. |
| `tabela_icms_incluso` | SIM | Boolean: True = ICMS ja embutido no frete informado pela transportadora; False = ICMS deve ser acrescido ao calcular (formula: frete / (1 - icms)). Sinonimo: 'icms incluso'. |
| `icms_destino` | SIM | % de ICMS da cidade/UF de destino (snapshot da cotacao). Uso duplo: (1) acrescido ao frete quando tabela_icms_incluso=False — formula frete/(1-icms); (2) deduzido do frete bruto para calcular valor... |

## Embarque

Tabela: `embarques` · overlay existe: True

**business_rules propostas (overlay):**
- numero vs id: O campo numero e o identificador humano do embarque (usado no dia a dia operacional e na portaria). O campo id e a PK interna que aparece na URL. Ao buscar 'embarque N', usar numero, nao id.
- Criacao de embarques: embarques nao-FOB sao criados a partir do fluxo de cotacao (cotacao/routes.py). Embarques FOB sao criados diretamente a partir dos pedidos (pedidos/routes/cotacao_routes.py:399). Distinguir pelo tipo_carga='FOB' e tipo_cotacao='FOB'.
- Lock pos-CTe: Embarques com pelo menos um Frete vinculado a um CTe (Frete.numero_cte preenchido) nao podem ser cancelados. Ao diagnosticar status='ativo' sem possibilidade de cancelamento, verificar fretes com numero_cte.
- Calculo de frete liquido: Se transportadora_optante=True (Simples Nacional): frete_liquido = frete_bruto. Se False: frete_liquido = frete_bruto * (1 - %ICMS), onde %ICMS e dado por tabela_icms (tratativa comercial) ou icms_destino (fixo por regiao), dependendo de qual estiver preenchido.

**field descriptions / hints a adicionar (6):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `numero` | SIM | Numero de referencia do embarque usado no dia a dia operacional e no vinculo com a portaria. ATENCAO: nao confundir com id (que aparece na URL) — o campo numero e o identificador humano do embarque. |
| `data_prevista_embarque` | SIM | Data prevista de embarque, preenchida manualmente apos criacao. Funciona como gatilho para liberar o botao 'Imprimir completo' (2 vias do embarque + 1 via por separacao com itens/qtds/codigos). Sin... |
| `data_embarque` | SIM | Data efetiva de saida do embarque para entrega. Preenchida automaticamente pela portaria quando o veiculo sai; tambem editavel manualmente. Limpa ao desvincular portaria. |
| `transportadora_id` | SIM | FK para transportadoras.id. Em embarques FOB, este campo e preenchido por padrao com o registro 'FOB - COLETA' (coleta pelo proprio cliente). Para nao-FOB, selecionada da cotacao na criacao. |
| `status` | SIM | Status do embarque: 'draft' (criado manualmente sem cotacao), 'ativo' (criado via cotacao ou ativado), 'cancelado'. REGRA: embarque com pelo menos um frete vinculado a CTe nao pode ser cancelado. |
| `transportadora_optante` | SIM | Snapshot do regime tributario da transportadora no momento da cotacao. True = optante Simples Nacional: sem credito de ICMS, frete_liquido = frete_bruto. False = nao optante: ha credito de ICMS, fr... |

## ENTREGAMONITORADA

Tabela: `entregas_monitoradas` · overlay existe: True

**business_rules propostas (overlay):**
- Discriminador de dominio: sempre filtrar WHERE origem = 'NACOM' em consultas do fluxo padrao Nacom; origem = 'CARVIA' isola registros do frete subcontratado CarVia. Evita colisao de numero_nf entre os dois sistemas.
- Clientes de rede (Atacadao, Assai, Fort, Tenda): lancam contas a pagar pela data de RECEBIMENTO, nao pela emissao da NF, e podem atrasar o lancamento intencionalmente para ganhar dias de vencimento. O campo resposta_financeiro captura a confirmacao da logistica (via motorista, transportadora ou portal do cliente) que o financeiro usa para rebater o cliente.
- Canhoto como prova de entrega: canhoto_arquivo IS NOT NULL equivale a 'Canhoto OK'; NULL equivale a 'S/ canhoto'. Para clientes de rede, canhoto ausente bloqueia a confirmacao de entrega junto ao financeiro do cliente.
- Analise de gargalos de reagendamento: agregar motivo_reagendamento WHERE reagendar = True revela padroes sistematicos de falha operacional (ex: ausencia de cliente, falha de transportadora, problema de acesso).

**field descriptions / hints a adicionar (4):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `origem` | SIM | Discriminador de dominio: 'NACOM' (fluxo frete principal) ou 'CARVIA' (frete subcontratado CarVia). Evita colisao de numero_nf entre os dois sistemas — sempre filtrar WHERE origem = 'NACOM' quando ... |
| `motivo_reagendamento` | SIM | Texto livre informado pelo operador ao reagendar. Usado para identificar gargalos e falhas sistematicas que geram necessidade de reagendamento — aggregar por motivo_reagendamento revela padroes ope... |
| `resposta_financeiro` | SIM | Resposta da equipe de logistica sobre a pendencia financeira. Contexto: clientes de rede (Atacadao, Assai, Fort, Tenda) lancam contas a pagar pela data de RECEBIMENTO e nao pela emissao da NF, pode... |
| `canhoto_arquivo` | SIM | Caminho do arquivo do canhoto assinado (local ou S3). Semantica binaria: NULL = 'S/ canhoto' (sem prova de entrega), qualquer valor = 'Canhoto OK'. Propriedade possui_canhoto = bool(canhoto_arquivo... |

## RELATORIOFATURAMENTOIMPORTADO

Tabela: `relatorio_faturamento_importado` · overlay existe: False

**business_rules propostas (overlay):**
- origem = num_pedido: O campo 'origem' em relatorio_faturamento_importado corresponde ao 'num_pedido' em Pedido/CarteiraPrincipal. Para cruzar NFs com pedidos, usar: relatorio_faturamento_importado.origem = carteira_principal.num_pedido.
- cnpj_cliente = cnpj_cpf: O campo 'cnpj_cliente' equivale ao 'cnpj_cpf' em CarteiraPrincipal/Pedido. Join direto possível para enriquecer NFs com dados do pedido.
- cnpj_transportadora e nome_transportadora NAO sao confiáveis: Esses campos refletem o que consta na NF emitida, não a transportadora real que realizou a entrega. Para transportadora real, usar Embarque (embarque_item.transportadora_id ou embarque.transportadora).
- ativo=False NAO significa NF cancelada/inválida: NFs inativas são registros válidos e completos. A inativação é operacional — serve para excluir a NF do fluxo de monitoramento de entregas (ex: NFs FOB cuja entrega termina na coleta pelo cliente). Queries analíticas devem incluir ativo=False se buscarem volume total de NFs.
- vendedor -> Usuario.vendedor_vinculado: O campo 'vendedor' em relatorio_faturamento_importado faz join com Usuario.vendedor_vinculado (app/auth/models.py) para filtros por perfil de vendedor. Valor vem diretamente do CSV de faturamento do Odoo.
- incoterm armazenado sem prefixo Odoo: Os valores gravados são 'CIF', 'FOB', 'RED' (nunca '[CIF] COST...' ou '[RED] REDESPACHO'). O sanitizador extrair_incoterm_codigo() normaliza antes da inserção. Regra de derivação da rota do Pedido: rota RED -> 'RED'; rota FOB -> 'FOB'; demais -> 'CIF'.
- valor_total propagado para monitoramento: Após importação de NF, sincronizar_entrega_por_nf() copia relatorio_faturamento_importado.valor_total para EntregaMonitorada.valor_nf. Este é o mecanismo de atualização de valor no monitoramento de entregas.
- peso_bruto calculado em cascata: O campo peso_bruto é recalculado por AtualizadorPesoService somando FaturamentoProduto (via CadastroPalletizacao) e propagando para EmbarqueItem, Embarque e Frete. Não vem diretamente do CSV importado — é computado.

**field descriptions / hints a adicionar (16):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `numero_nf` | SIM | Número da nota fiscal. Equivale ao campo 'nf' em Pedido/CarteiraPrincipal. Chave única da tabela — uma linha por NF importada. |
| `cnpj_cliente` | SIM | CNPJ do cliente destinatário da NF. Equivale ao campo 'cnpj_cpf' em Pedido/CarteiraPrincipal. |
| `nome_cliente` | SIM | Razão social reduzida do cliente. Equivale ao campo 'razao_social_red' em Pedido/CarteiraPrincipal. |
| `valor_total` | SIM | Valor total da nota fiscal (R$). Após importação, é propagado para EntregaMonitorada.valor_nf via sincronizar_entrega_por_nf. Fonte de verdade do valor da NF no monitoramento de entregas. |
| `peso_bruto` | PARCIAL | Peso bruto total da NF em kg. Atualizado em cascata por AtualizadorPesoService (soma de FaturamentoProduto calculada via CadastroPalletizacao), propagando para EmbarqueItem, Embarque e Frete. |
| `cnpj_transportadora` | SIM | CNPJ da transportadora conforme consta na NF importada. NÃO usar para identificar transportadora — o vínculo correto está no Embarque, que é mais confiável. |
| `nome_transportadora` | SIM | Nome da transportadora conforme consta na NF importada. NÃO usar para identificar transportadora — o vínculo correto está no Embarque, que é mais confiável. |
| `municipio` | SIM | Município de destino da NF. Equivale ao campo 'nome_cidade' em Pedido/CarteiraPrincipal. |
| `estado` | SIM | UF (sigla de 2 letras) de destino da NF. Equivale ao campo 'cod_uf' em Pedido/CarteiraPrincipal. |
| `codigo_ibge` | SIM | Código IBGE do município de destino. Equivale ao campo 'codigo_ibge' em Pedido/CarteiraPrincipal. |
| `origem` | SIM | Número do pedido de origem desta NF. Equivale ao campo 'num_pedido' em Pedido/CarteiraPrincipal. Chave de join entre RelatorioFaturamentoImportado e a carteira de pedidos. |
| `incoterm` | PARCIAL | Incoterm da venda. Valores armazenados: 'CIF' (padrão), 'FOB' (cliente retira), 'RED' (redespacho). Derivado da rota do Pedido: RED -> 'RED'; FOB -> 'FOB'; demais -> 'CIF'. Extraído e normalizado p... |
| `vendedor` | SIM | Nome do vendedor responsável pela venda. Join com Usuario.vendedor_vinculado para filtros por perfil 'vendedor'. Campo vem diretamente do CSV de faturamento importado do Odoo. |
| `ativo` | SIM | Flag de ativação da NF no monitoramento. default=True. NFs inativas (ativo=False) são registros VÁLIDOS — a inativação é operacional (ex: NFs FOB cuja entrega encerra na coleta). Queries de monitor... |
| `inativado_em` | SIM | Timestamp de quando a NF foi inativada (ativo=False). Nulo enquanto NF estiver ativa. |
| `inativado_por` | SIM | Usuário (email ou nome) que executou a inativação da NF. Nulo enquanto NF estiver ativa. |

## DESPESAEXTRA

Tabela: `despesas_extras` · overlay existe: False

**business_rules propostas (overlay):**
- Lancamento no Odoo exige tres condicoes simultaneas: tipo_documento='CTe' (case-insensitive), despesa_cte_id preenchido (CTe Complementar vinculado) e status='VINCULADO_CTE'. Quando lancado com sucesso, status vai para 'LANCADO_ODOO'.
- Despesas com tipo_documento diferente de 'CTe' (ex: NFS, RECIBO) encerram em status='LANCADO' sem passar pelo Odoo — o comprovante e armazenado via comprovante_path (S3).
- transportadora_id e opcional: se NULL a despesa e paga para a transportadora do frete pai; se preenchido, indica transportadora alternativa (ex: coleta de devolucao feita por terceiro). A property transportadora_efetiva implementa essa logica de fallback.
- Para despesas de devolucao: tipo_despesa='DEVOLUCAO' e nfd_id deve ser preenchido com o id da NF de devolucao (tabela nf_devolucao). numero_nfd e cache do numero para exibicao rapida.
- origem de uma DespesaExtra nao tem coluna propria — sempre herda do Frete pai (frete.origem). Valores possiveis: NACOM ou OP_ASSAI.

**field descriptions / hints a adicionar (7):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `tipo_despesa` | SIM | Categoria da despesa extra. Valores: REENTREGA, TDE, PERNOITE, DEVOLUCAO, DIARIA, COMPLEMENTO DE FRETE, COMPRA/AVARIA, TRANSFERENCIA, DESCARGA, ESTACIONAMENTO, CARRO DEDICADO, ARMAZENAGEM. Para cus... |
| `setor_responsavel` | SIM | Setor da empresa responsavel pela despesa. Valores: COMERCIAL, QUALIDADE, FISCAL, FINANCEIRO, LOGISTICA, COMPRAS. |
| `motivo_despesa` | SIM | Motivo que gerou a despesa extra. Valores: PEDIDO EM DESACORDO, PROBLEMA NO CLIENTE, SEM AGENDA, DIVERGENCIA DE CADASTRO, ARQUIVO XML, FORA DO PADRAO, FALTA MERCADORIA, ATRASO, INVERSAO, EXCESSO DE... |
| `tipo_documento` | SIM | Tipo do documento comprobatorio. Valores tipicos: CTe, NFS, RECIBO. Apenas despesas com tipo_documento='CTe' vinculadas a um CTe Complementar (despesa_cte_id preenchido) podem ser lancadas no Odoo. |
| `status` | INCERTO | Status do ciclo de vida da despesa extra. Valores: PENDENTE (criada, aguardando), VINCULADO_CTE (CTe Complementar vinculado, pronto para Odoo), LANCADO_ODOO (lancado no Odoo via fluxo de 16 etapas)... |
| `transportadora_id` | INCERTO | Transportadora alternativa que recebe pelo pagamento da despesa. Se NULL, herda a transportadora do frete pai. Usar quando a despesa envolve transportadora diferente do frete original (ex: devoluca... |
| `despesa_cte_id` | INCERTO | FK para o CTe Complementar especifico desta despesa extra (diferente do CTe do frete pai). Obrigatorio para lancamento no Odoo: despesa deve ter tipo_documento='CTe', despesa_cte_id preenchido e st... |

## Transportadora

Tabela: `transportadoras` · overlay existe: True

**business_rules propostas (overlay):**
- optante (Simples Nacional): se False, o sistema deduz ICMS da cidade de destino ao calcular valor liquido do frete; se True, deducao de ICMS e suprimida. Regra: valor_sem_icms = valor_bruto * (1 - icms_cidade) somente quando optante=False E freteiro=False/NULL.
- freteiro=True dispara deducao adicional de 9,25% no valor liquido: valor_liquido = valor_sem_icms * (1 - 0,0925). Freteiros podem ou nao ter ICMS deduzido (depende de optante), mas sempre tem o desconto de 9,25%.
- freteiro=NULL deve ser tratado como freteiro=False (transportadora empresa) em todos os filtros e calculos — sempre usar OR freteiro IS NULL ao filtrar transportadoras nao-freteiro.

**field descriptions / hints a adicionar (2):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `optante` | SIM | Optante do Simples Nacional. Se False (nao optante), o sistema deduz ICMS da cidade de destino ao calcular valor liquido do frete; se True (optante), a deducao de ICMS e suprimida. Snapshoteado em ... |
| `freteiro` | SIM | freteiro=True: autonomo/avulso — nao e empresa transportadora; dispara deducao adicional de 9,25% no valor liquido do frete (alem do ICMS). freteiro=NULL deve ser tratado como False (transportadora... |

## USUARIO

Tabela: `usuarios` · overlay existe: False

**business_rules propostas (overlay):**
- Permissão é dual-axis: 'perfil' controla O QUE o usuário pode fazer dentro de um sistema; campos 'sistema_*' (sistema_logistica, sistema_motochefe, sistema_carvia, sistema_lojas etc.) controlam SE o usuário acessa o sistema. Um usuário com perfil='logistica' mas sistema_logistica=FALSE não acessa o módulo de logística.
- status='ativo' é pré-requisito absoluto para qualquer acesso, independente de perfil ou flags sistema_*. Usuários pendente/rejeitado/bloqueado não acessam nada.
- vendedor_vinculado é o JOIN key entre usuarios e RelatorioFaturamentoImportado.vendedor: filtra toda a visibilidade de pedidos, cotações e monitoramento para usuários com perfil='vendedor'. Para queries de visibilidade: WHERE RelatorioFaturamentoImportado.vendedor = usuarios.vendedor_vinculado.
- perfil='administrador' tem acesso irrestrito: ignora sistema_* flags, ignora loja_hora_id, ignora status nos métodos de permissão de sistemas (exceto gates explícitos de status='ativo' em pode_acessar_lojas e pode_acessar_motos_assai).
- O campo 'telefone' serve dupla função: contato genérico E chave de match para WhatsApp Bot (find_by_whatsapp_jid). Para o bot, o match considera variantes E.164: '11991642998' e '5511991642998' são equivalentes.

**field descriptions / hints a adicionar (7):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `perfil` | PARCIAL | Perfil base do usuário (portaria, vendedor, gerente_comercial, financeiro, logistica, administrador). Controla permissões dentro de um sistema, mas NÃO concede acesso ao sistema: o acesso a cada mó... |
| `vendedor_vinculado` | SIM | Nome de referência do vendedor conforme consta na coluna 'vendedor' de RelatorioFaturamentoImportado. Para usuários com perfil='vendedor': filtra pedidos, cotações e monitoramento para exibir apena... |
| `whatsapp_autorizado` | INCERTO | Opt-in explícito para o WhatsApp Bot (canal OpenClaw). Default FALSE — ter telefone cadastrado não habilita o bot automaticamente. Usado por find_by_whatsapp_jid para autenticar mensagens recebidas... |
| `teams_user_id` | INCERTO | Azure AD object ID do Microsoft Teams. Preenchido por código de pareamento (usuário envia 'vincular ABC123' no bot Teams), auto-match por email corporativo ou admin. Usado por find_by_teams_aad_id ... |
| `loja_hora_id` | INCERTO | Segregação por loja HORA: NULL = acesso a todas as lojas; preenchido com ID = restrito a 1 loja. Não é FK declarada (app/auth é independente de app/hora). Ignorado para perfil='administrador' (admi... |
| `criterio_pedidos_hora` | INCERTO | Critério de filtragem de pedidos HORA em /hora/vendas. 'loja' (padrão): filtra por loja_hora_id. 'vendedor': filtra por vendedor ou criado_por_id do usuário, ignorando escopo de loja. Configurado e... |
| `preferences` | INCERTO | Preferências per-user em JSONB. Chave conhecida: agent_thinking_display ('summarized'/'omitted', default 'omitted') — controla exibição do raciocínio do Agent SDK. Usar get_preference/set_preferenc... |

## CONTATOAGENDAMENTO

Tabela: `contatos_agendamento` · overlay existe: True

**business_rules propostas (overlay):**
- COMERCIAL como forma de agendamento significa que a logistica interna solicita ao departamento comercial para realizar o agendamento junto ao cliente — NAO e a logistica que contata o cliente diretamente.
- Enum completo e atual de forma: PORTAL, TELEFONE, E-MAIL, COMERCIAL, SEM AGENDAMENTO, ODOO. Valor WhatsApp NAO consta no enum de choices do sistema (apenas em comentario legado no model); nao usar em queries de filtragem.
- Tabela serve dupla funcao: (1) pre-embarque — roteirizacao usa para alertar se cliente precisa de agendamento antes de carregar o caminhao; (2) pos-embarque — monitoramento usa para executar o agendamento/reagendamento da entrega.
- Um CNPJ com forma = 'SEM AGENDAMENTO' dispensa contato previo; CNPJs ausentes da tabela tambem podem ser tratados como sem exigencia — validar com forma IS NULL OR forma = 'SEM AGENDAMENTO'.

**field descriptions / hints a adicionar (2):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `forma` | PARCIAL | Valores validos de forma (enum de choices): 'PORTAL', 'TELEFONE', 'E-MAIL', 'COMERCIAL', 'SEM AGENDAMENTO', 'ODOO'. COMERCIAL significa que a logistica solicita ao comercial para realizar o agendam... |
| `__table_description__` | SIM | Cadastro de politica de agendamento por cliente (CNPJ): define SE o cliente exige agendamento previo e COMO fazê-lo (via portal, telefone, e-mail, comercial, Odoo ou sem necessidade). Consultada na... |

## CIDADE

Tabela: `cidades` · overlay existe: True

**business_rules propostas (overlay):**
- Hierarquia geografica das cidades: UF > mesorregiao > microrregiao > cidade. Filtros por mesorregiao e microrregiao estao disponiveis em endpoints de listagem (localidades/routes.py).
- cidades.icms representa o ICMS de destino com referencia de origem em SP (sede da empresa; tabelas de frete sao cadastradas com uf_origem='SP'). Se tabelas_frete.icms_proprio estiver preenchido, ele tem prioridade sobre cidades.icms no calculo.
- substitui_icms_por_iss: campo de salvaguarda sem uso operacional atual (nenhum registro real com True). Reservado para municipios que exijam ISS sobre o frete em vez de ICMS.

**field descriptions / hints a adicionar (6):**

| Campo | Verdade | Proposta curada |
|---|---|---|
| `nome` | SIM | Nome da cidade no padrao IBGE; garantia de acentuacao correta e ortografia conforme tabela oficial. Busca deve usar ILIKE (ver business_rules). |
| `uf` | SIM | Sigla do estado (UF) no padrao IBGE: 2 letras maiusculas (ex: 'SP', 'PR'). Sempre NOT NULL. |
| `icms` | PARCIAL | ICMS de destino calculado com referencia de origem em SP (sede da empresa; tabelas filtram uf_origem='SP'). Aliquota percentual armazenada como float (ex: 12.0 = 12%). Sobreposta por tabelas_frete.... |
| `substitui_icms_por_iss` | SIM | Campo de salvaguarda: se True, o frete e tributado via ISS (NFS) em vez de ICMS (CTe). Default False. Nenhum registro real usa True (campo sem impacto operacional atual; reservado para eventual obr... |
| `microrregiao` | PARCIAL | Microrregiao IBGE da cidade (subdivisao de mesorregiao). Hierarquia geografica: UF > mesorregiao > microrregiao > cidade. Campo nullable; usado em filtros de localidades (endpoints de listagem e ex... |
| `mesorregiao` | PARCIAL | Mesorregiao IBGE da cidade (nivel acima de microrregiao, abaixo de UF). Hierarquia geografica: UF > mesorregiao > microrregiao > cidade. Campo nullable; usado em filtros de localidades (endpoints d... |
