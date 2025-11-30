ANÁLISE PROFUNDA - BASEADA NAS RECOMENDAÇÕES OFICIAIS DA ANTHROPIC
FONTES CONSULTADAS:
Writing Effective Tools for AI Agents
Equipping Agents for the Real World with Agent Skills
Skill Authoring Best Practices
Anthropic Skills GitHub Repository
Effective Context Engineering for AI Agents
🔍 PONTO 1: Consolidação vs Granularidade dos Scripts
EVIDÊNCIA DA ANTHROPIC:
"Tools can consolidate functionality, handling potentially multiple discrete operations under the hood. For example, tools can enrich tool responses with related metadata or handle frequently chained, multi-step tasks in a single tool call."
"Avoid bloated tool sets that cover too much functionality or lead to ambiguous decision points about which tool to use. If a human engineer can't definitively say which tool should be used in a given situation, an AI agent can't be expected to do better."
ANÁLISE DO ESTADO ATUAL:
Categoria	Scripts	Queries	Observação
P0 (3 scripts)	consultar_pedidos, analisar_disponibilidade, consultar_estoque	10 queries	✅ CONSOLIDAÇÃO ADEQUADA
P1 (4 scripts)	diagnosticar_atrasos, analisar_gargalos, listar_enviaveis, sugerir_adiar	5 queries	⚠️ GRANULAR DEMAIS
P2 (5 scripts)	calcular_prazo, ranking_travando, verificar_bonificacao, simular_reprogramacao, buscar_consolidar	5 queries	⚠️ MUITO GRANULAR
RECOMENDAÇÃO BASEADA NA ANTHROPIC:
Os P0 estão CORRETOS - são scripts consolidados que respondem múltiplas queries com variações de parâmetros:
consultar_estoque.py responde: Query 13, 17, 18, 20 (4 queries!)
analisar_disponibilidade.py responde: Query 1, 2, 9 (3 queries!)
Os P1 e P2 deveriam seguir o mesmo padrão. Analisando as queries:
Queries Relacionadas	Consolidação Recomendada
Q3 (sugerir adiar) + Q12 (ranking travando)	analisar_impacto_pedidos.py - ambos analisam como pedidos afetam outros
Q4, Q5 (gargalos) + Q11 (causa atraso)	diagnosticar_problemas.py - ambos diagnosticam causas de impedimentos
Q6 (enviaveis) + Q19 (consolidar)	planejar_envio.py - ambos planejam próximos envios
Q7 (prazo) + Q14 (bonificação) + Q15 (reprogramação)	Manter separados - propósitos distintos
PROPOSTA DE REESTRUTURAÇÃO:
DE 12 scripts → 7 scripts:
P0 (3 scripts - MANTER):
├── consultar_pedidos.py      # Q8, Q10, Q16
├── analisar_disponibilidade.py # Q1, Q2, Q9
└── consultar_estoque.py      # Q13, Q17, Q18, Q20

P1 (2 scripts - CONSOLIDAR):
├── diagnosticar_problemas.py  # Q4, Q5, Q11 (gargalos + causas atraso)
└── planejar_envio.py          # Q3, Q6 (adiar + enviaveis)

P2 (2 scripts - CONSOLIDAR):
├── analisar_impacto.py        # Q12, Q19 (ranking travando + consolidar)
└── simular_cenarios.py        # Q7, Q14, Q15 (prazo + bonif + reprog)
🔍 PONTO 2: Formato das Skills vs Recomendações Anthropic
ANÁLISE DO SKILL.md ATUAL:
# ATUAL
name: agente-logistico
description: Agente para consultas e analises do sistema de fretes...
PROBLEMAS IDENTIFICADOS (vs Best Practices):
Aspecto	Recomendação Anthropic	Atual	Status
Nome	"Use gerund form (verb + -ing)"	agente-logistico	❌ Deveria ser analyzing-logistics ou querying-freight-orders
Descrição	"Inclua o que faz E quando usar"	✅ Presente	✅ OK
Descrição	"Escreva em terceira pessoa"	"Agente para consultas..."	⚠️ OK mas poderia ser mais claro
Tamanho SKILL.md	"< 500 linhas"	~70 linhas	✅ OK
Progressive Disclosure	"Split into separate files"	Referencia QUERIES.md	✅ OK
Índice em arquivos > 100 linhas	"Include table of contents"	QUERIES.md tem 436 linhas	❌ Falta índice
SKILL.md CORRIGIDO:
---
name: querying-freight-logistics
description: Queries and analyzes freight order system data. Retrieves pending orders, stock availability, delivery forecasts, and shipping bottlenecks. Use when user asks about order status, stock projections, delivery dates, or wants to identify shipping issues.
---
ESTRUTURA DE DIRETÓRIOS (vs Recomendação):
# RECOMENDAÇÃO ANTHROPIC:
skill-name/
├── SKILL.md           # Core prompt (< 500 lines)
├── references/        # Documentation loaded into context
│   └── queries.md
└── scripts/           # Executable Python/Bash scripts
    └── *.py

# ATUAL:
agente-logistico/
├── SKILL.md           ✅
├── QUERIES.md         ⚠️ Deveria estar em references/
├── scripts/           ✅
└── eval/              ⚠️ Não é padrão Anthropic
🔍 PONTO 3: Extração de Funcionalidade Comum (Grupos Empresariais)
EVIDÊNCIA DA DUPLICAÇÃO:
# 6 scripts com GRUPOS_EMPRESARIAIS duplicado:
analisar_disponibilidade.py
analisar_gargalos.py
buscar_consolidar.py
calcular_prazo.py
consultar_pedidos.py
sugerir_adiar.py
RECOMENDAÇÃO DA ANTHROPIC:
"Tools should be self-contained, robust to error, and extremely clear with respect to their intended use."
"Scripts must solve problems, not transfer them to Claude."
SOLUÇÃO RECOMENDADA:
Criar um módulo compartilhado utils/resolver_entidades.py:
# utils/resolver_entidades.py
"""
Módulo para resolução de entidades do domínio logístico.
Centraliza lookup de grupos empresariais, produtos e termos do negócio.
"""

GRUPOS_EMPRESARIAIS = {
    'atacadao': ['93.209.76', '75.315.33', '00.063.96'],
    'assai': ['06.057.22'],
    'tenda': ['01.157.55']
}

def resolver_grupo_empresarial(termo: str) -> list[str]:
    """Retorna prefixos CNPJ para um grupo empresarial"""
    return GRUPOS_EMPRESARIAIS.get(termo.lower(), [])

def resolver_pedido_por_termo(termo: str):
    """
    Busca pedido por:
    - Número exato: VCD123
    - Grupo + termo: "atacadao 183"
    - Cliente + termo: "carrefour barueri"
    """
    # Implementação centralizada
    pass
Impacto: Reduz duplicação de ~150 linhas de código duplicado.
🔍 PONTO 4: Resolução de Termos Ambíguos de Produtos
PROBLEMA IDENTIFICADO:
Usuários podem usar termos como:
"pessego" → único produto com esse termo
"pf da mezzani" → Azeitona Preta Fatiada + Mezzani
"bd ind az" → Balde Industrial + Azeitona
RECOMENDAÇÃO DA ANTHROPIC:
"Metadata are critical: File hierarchies, naming conventions, and timestamps all provide important signals that guide both humans and agents in efficient information retrieval."
"Instead of wrapping individual API endpoints, create composite tools that handle multi-step workflows."
SOLUÇÃO RECOMENDADA:
Criar um resolver de produtos inteligente que seja chamado por todos os scripts:
# utils/resolver_produtos.py
"""
Resolver inteligente de SKUs por termos do domínio.
Lida com abreviações e combinações de categoria/embalagem/marca.
"""

# Mapeamento de abreviações
ABREVIACOES = {
    'tipo_materia_prima': {
        'az': 'azeitona',
        'pf': 'preta fatiada',
        'vf': 'verde fatiada',
        'vi': 'verde inteira',
    },
    'tipo_embalagem': {
        'bd': 'balde',
        'ind': 'industrial',
        'lt': 'lata',
        'vd': 'vidro',
        'sch': 'sachet',
        'pouch': 'pouch',
    },
    'categoria': {
        'mezzani': 'MEZZANI',
        'famiglia': 'LA FAMIGLIA',
    }
}

def resolver_produto(termo: str) -> list[dict]:
    """
    Resolve termo ambíguo para lista de SKUs candidatos.
    
    Exemplos:
        "pessego" -> [{"cod": "PES001", "nome": "Pessego em Calda..."}]
        "pf mezzani" -> [{"cod": "AZ001", "nome": "Azeitona Preta Fatiada..."}]
    
    Retorna lista ordenada por relevância (match score).
    """
    from app.producao.models import CadastroPalletizacao
    
    # 1. Tokenizar termo
    tokens = termo.lower().split()
    
    # 2. Expandir abreviações
    tokens_expandidos = expandir_abreviacoes(tokens)
    
    # 3. Buscar matches
    candidatos = buscar_candidatos(tokens_expandidos)
    
    # 4. Ranquear por relevância
    return ranquear_por_match_score(candidatos, tokens_expandidos)

def expandir_abreviacoes(tokens: list) -> list:
    """Expande abreviações conhecidas do domínio"""
    expandidos = []
    for token in tokens:
        for categoria, mapa in ABREVIACOES.items():
            if token in mapa:
                expandidos.append({
                    'termo': mapa[token],
                    'campo': categoria,
                    'original': token
                })
                break
        else:
            expandidos.append({'termo': token, 'campo': None, 'original': token})
    return expandidos
ONDE DOCUMENTAR:
No SKILL.md (seção de termos do domínio):
## Resolução de Produtos

Usuários podem referenciar produtos por:
- **Nome completo**: "Azeitona Preta Manzanilla Fatiada BD 12KG Mezzani"
- **Termo único se único**: "pessego" (único SKU)
- **Combinação de atributos**: "pf mezzani", "az bd ind"

Abreviações comuns:
- AZ = Azeitona
- PF = Preta Fatiada
- VI = Verde Inteira
- BD = Balde
- IND = Industrial

Os scripts automaticamente resolvem termos ambíguos consultando CadastroPalletizacao.
📊 RESUMO DAS AÇÕES RECOMENDADAS
#	Ação	Justificativa Anthropic	Prioridade
1	Consolidar P1/P2: 9 scripts → 4 scripts	"Avoid bloated tool sets"	🔴 Alta
2	Renomear skill: querying-freight-logistics	"Use gerund form"	🟡 Média
3	Mover QUERIES.md para references/	Estrutura padrão	🟡 Média
4	Criar utils/resolver_entidades.py	"Self-contained, robust"	🔴 Alta
5	Criar utils/resolver_produtos.py	"Enrich responses with metadata"	🔴 Alta
6	Adicionar índice ao QUERIES.md	">100 lines needs TOC"	🟢 Baixa


SIMULAÇÃO DE NOMES EM PORTUGUÊS PARA SCRIPTS EXISTENTES
#	Script Atual	Queries	Gerund (verbo-ndo)	Frase Nominal	Orientado Ação
1	analisar_disponibilidade.py	1, 2, 9	analisando-disponibilidade-pedido	analise-disponibilidade-pedido	analisar-disponibilidade-pedido
2	analisar_gargalos.py	4, 5	analisando-gargalos-envio	analise-gargalos-envio	analisar-gargalos-envio
3	buscar_consolidar.py	19	buscando-pedidos-consolidar	busca-consolidacao-pedidos	buscar-pedidos-consolidar
4	calcular_prazo.py	7	calculando-prazo-entrega	calculo-prazo-entrega	calcular-prazo-entrega
5	consultar_estoque.py	13, 17, 18, 20	consultando-estoque-produtos	consulta-estoque-produtos	consultar-estoque-produtos
6	consultar_pedidos.py	8, 10, 16	consultando-pedidos-carteira	consulta-pedidos-carteira	consultar-pedidos-carteira
7	diagnosticar_atrasos.py	10, 11	diagnosticando-atrasos-embarque	diagnostico-atrasos-embarque	diagnosticar-atrasos-embarque
8	listar_enviaveis.py	6	listando-pedidos-enviaveis	lista-pedidos-enviaveis	listar-pedidos-enviaveis
9	ranking_travando.py	12	ranqueando-pedidos-travando	ranking-pedidos-travando	ranquear-pedidos-travando
10	simular_reprogramacao.py	15	simulando-reprogramacao-producao	simulacao-reprogramacao-producao	simular-reprogramacao-producao
11	sugerir_adiar.py	3	sugerindo-pedidos-adiar	sugestao-adiamento-pedidos	sugerir-pedidos-adiar
12	verificar_bonificacao.py	14	verificando-alinhamento-bonificacao	verificacao-bonificacao-venda	verificar-bonificacao-venda
🔍 ANÁLISE DE REDUNDÂNCIA VIA NOMES
Agrupamento por VERBO (padrão gerund):
Verbo	Scripts	Observação
analisando-*	analisar_disponibilidade, analisar_gargalos	⚠️ CANDIDATOS A CONSOLIDAR
consultando-*	consultar_estoque, consultar_pedidos	Domínios distintos (estoque vs pedidos) - OK separados
buscando-*	buscar_consolidar	Único - poderia ser flag em consultar_pedidos
calculando-*	calcular_prazo	Único - domínio específico (lead time)
diagnosticando-*	diagnosticar_atrasos	Único
listando-*	listar_enviaveis	⚠️ Poderia ser flag em consultar_pedidos
ranqueando-*	ranking_travando	Único - análise de impacto
simulando-*	simular_reprogramacao	Único - domínio produção
sugerindo-*	sugerir_adiar	⚠️ Similar ao ranking (impacto de pedidos)
verificando-*	verificar_bonificacao	⚠️ Poderia ser flag em consultar_pedidos
REDUNDÂNCIAS CLARAS (mesmo padrão semântico):
Grupo	Scripts	Nome Consolidado Sugerido
Análise de disponibilidade	analisar_disponibilidade + analisar_gargalos	analisando-disponibilidade (com flags --pedido / --grupo)
Análise de impacto	sugerir_adiar + ranking_travando	analisando-impacto-pedidos (com flags --liberar-para / --ranking)
Consulta de pedidos	consultar_pedidos + listar_enviaveis + buscar_consolidar + verificar_bonificacao	consultando-pedidos (com flags --enviaveis / --consolidar-com / --verificar-bonificacao)
📊 PROPOSTA VISUAL DE CONSOLIDAÇÃO
ANTES (12 scripts):                          DEPOIS (7 scripts):
─────────────────────                        ────────────────────
analisar_disponibilidade.py  ─┬─►  analisando-disponibilidade.py (Q1,2,4,5,9)
analisar_gargalos.py         ─┘

consultar_pedidos.py         ─┬─►  consultando-pedidos.py (Q6,8,14,16,19)
listar_enviaveis.py          ─┤
buscar_consolidar.py         ─┤
verificar_bonificacao.py     ─┘

sugerir_adiar.py             ─┬─►  analisando-impacto-pedidos.py (Q3,12)
ranking_travando.py          ─┘

consultar_estoque.py         ───►  consultando-estoque.py (Q13,17,18,20) [MANTER]
diagnosticar_atrasos.py      ───►  diagnosticando-atrasos.py (Q10,11) [MANTER]
calcular_prazo.py            ───►  calculando-prazo-entrega.py (Q7) [MANTER]
simular_reprogramacao.py     ───►  simulando-reprogramacao.py (Q15) [MANTER]