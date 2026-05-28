"""
MATRIZ_INTERCOMPANY — operacoes fiscais entre empresas do grupo NACOM.

Dado, nao codigo. Adicionar nova operacao = adicionar entrada no dict.

Origem dos valores:
- SAIDA: docs/inventario-2026-05/00-decisoes/D002-matriz-intercompany-final.md (audit F0)
- ENTRADA: validacao XML-RPC read-only no Odoo PROD em 2026-05-21 (faturas posted reais,
  par saida<->entrada via chave SEFAZ).
- Regra de negocio 5902/5903/5124/5949 confirmada por Rafael 2026-05-21 (ver bloco
  dev-industrializacao).
Premissas: P001-P011 em docs/inventario-2026-05/01-premissas/

Estrutura:
- `fiscal_position_id`: dict (company_origem, company_destino) -> fiscal_position da SAIDA.
  Service seta isso no account.move; Odoo decide o CFOP. NAO setar CFOP no account.move.
- `cfop_esperado`: CFOP da SAIDA.
  * NO FLUXO NORMAL (account.move criado via PO+fiscal_position): **informacional/log**.
    Real e decidido pelo Odoo via fiscal_position + l10n_br_tipo_pedido. NAO hardcodar.
  * NO CAMINHO B PALIATIVO da ETAPA F (Skill 8) — picking criado MANUALMENTE pela Skill 5
    atomo `criar_picking_entrada_destino_manual` SEM PO+partner+fiscal_position — vira
    **FALLBACK NECESSARIO** para setar `l10n_br_cfop_id` explicito no stock.move (G037).
    Caso degenerado: motor fiscal nao tem como derivar CFOP sem fiscal_position.
  * Refator v19+ remove o paliativo (caminho A correto: DFe→PO→picking nativo). Apos
    refator, `cfop_esperado` volta a ser apenas informacional/log.
  * Doc: docs/inventario-2026-05/02-gotchas/G037-*.md
- `entrada`: dict (company_origem, company_destino) -> dados da NF de ENTRADA (in_invoice
  escriturada no DESTINO a partir do DFe). Campos: fiscal_position_id, cfop,
  l10n_br_tipo_pedido_entrada. Informacional/auditoria.

REGRA DE CFOP por TIPO DE PRODUTO na industrializacao por encomenda FB<->LF (Rafael 2026-05-21):
  - 5901 (entrada 1901): FB->LF remessa de INSUMO (tipo 1,2,3) p/ industrializar.
  - 5124 (entrada 1124): LF->FB saida do PRODUTO ACABADO (tipo 4) industrializado + cobranca.
  - 5902 (entrada 1902): LF->FB retorno dos INSUMOS (tipo 1,2,3) recebidos e UTILIZADOS.
                         NUNCA produto acabado. Par interno de 5124 na mesma NF.
  - 5903 (entrada 1903): LF->FB retorno de INSUMO (tipo 1,2,3) recebido e NAO aplicado.
  - 5949 (entrada 1949): retrabalho / retorno / AJUSTE DE ESTOQUE de produto (tipo 4).
                         E o caso do agente/inventario.
  5124+5902 ocorrem na operacao 'venda-industrializacao' (fp 111, fluxo RecebimentoLF).

OPERACOES (6 chaves):
- AJUSTE DE INVENTARIO (usadas por resolver_operacao_por_tipo_produto):
  industrializacao, perda, dev-industrializacao, transf-filial.
- REFERENCIA (fluxo RecebimentoLF; documentadas, NAO retornadas pelo resolver de ajuste):
  venda-industrializacao (5124+5902, fp 111), vasilhame (5921, fp 64).

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §6.3
Doc consolidada das entradas/CFOPs: docs/inventario-2026-05/00-decisoes/D014-cfop-entradas-e-operacoes-referencia.md
"""
from typing import Dict, Any, Tuple


CODIGO_PARA_COMPANY_ID: Dict[str, int] = {'FB': 1, 'CD': 4, 'LF': 5}

COMPANY_PARTNER_ID: Dict[int, int] = {
    1: 1,    # FB → res.partner.id=1
    4: 34,   # CD → res.partner.id=34
    5: 35,   # LF → res.partner.id=35
}


MATRIZ_INTERCOMPANY: Dict[str, Dict[str, Any]] = {
    'industrializacao': {
        'l10n_br_tipo_pedido': 'industrializacao',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3],
        'fiscal_position_id': {
            (1, 5): 25,  # FB → LF: 'REMESSA PARA INDUSTRIALIZAÇÃO'
        },
        'cfop_esperado': {(1, 5): '5901'},
        'entrada': {
            # FB → LF: entrada escriturada na LF (ENTIN). Confirmado RPI/2026/00200 -> ENTIN/2026/05/0032.
            (1, 5): {'fiscal_position_id': 131, 'cfop': '1901',
                     'l10n_br_tipo_pedido_entrada': 'serv-industrializacao'},
        },
        'nf_referencia': 94457,
        'account_move_id_referencia': 607443,
    },
    'perda': {
        # ====================================================================
        # 5903 (produto 1,2,3) = retorno de INSUMO recebido p/ industrializacao e NAO
        # aplicado. NAO e "par obrigatorio" de 5902. Verificado no Odoo 2026-05-21: das
        # 152 NFs de saida LF->FB, 96 sao SO 5902 (serie VND), 56 sao SO 5903 (serie RETNA),
        # ZERO combinam os dois. O par de 5902 DENTRO da mesma NF e o 5124 (produto acabado),
        # nao o 5903 — ver bloco dev-industrializacao. 5902 e 5903 sao retornos de insumo
        # independentes (utilizado vs nao-aplicado), emitidos cada um quando aplicavel.
        # ====================================================================
        'l10n_br_tipo_pedido': 'perda',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3],
        'fiscal_position_id': {
            (5, 1): 91,  # LF → FB: 'SAÍDA - PERDAS' (fiscalmente: retorno NAO aplicado)
        },
        'cfop_esperado': {(5, 1): '5903'},
        'entrada': {
            # LF → FB: entrada na FB. fp 97 'ENTRADA: RETORNO NÃO APLICADO'.
            # Confirmado RETNA/2026/00025 -> RETNA/2026/04/0008.
            (5, 1): {'fiscal_position_id': 97, 'cfop': '1903',
                     'l10n_br_tipo_pedido_entrada': 'retorno'},
        },
        'nf_referencia': 13075,
        'account_move_id_referencia': 588209,
    },
    'dev-industrializacao': {
        # ====================================================================
        # PRODUTO TIPO 4 (ACABADO) entre LF e [FB, CD]. CFOP de SAIDA = 5949 em TODAS as
        # direcoes (retrabalho / retorno / AJUSTE DE ESTOQUE — uso do agente). Entrada 1949.
        #
        #   CD → LF .. fp 74 (REMESSA P/ RETRABALHO) -> 5949   confirmado RRET/2026/00008
        #   LF → CD .. fp 89 (RETRABALHO)            -> 5949   confirmado SARET/2026/00002
        #   LF → FB .. fp 89 (RETRABALHO)            -> 5949   retorno/ajuste
        #   FB → LF .. fp 74 (simetria P011)         -> 5949   SEM precedente
        #
        # 5902 NAO SE APLICA A PRODUTO ACABADO (regra Rafael 2026-05-21).
        #   5902 ('retorno de mercadoria utilizada na industr. por encomenda') e EXCLUSIVO
        #   dos INSUMOS/embalagens (tipo 1,2,3) que a FB remeteu (5901) e a LF aplicou.
        #   Ocorre na operacao 'venda-industrializacao' (fp 111, fluxo RecebimentoLF), em NF
        #   MISTA:  produto acabado tipo 4 -> 5124 (entrada 1124)
        #           insumos tipo 1,2,3     -> 5902 (entrada 1902)
        #           entrada FB: fp 88 'ENTRADA - SERVICO INDUSTRIALIZACAO' (serv-industrializacao).
        #   Essa operacao e do faturamento de industrializacao (RecebimentoLF), NAO do ajuste
        #   de inventario -> nao modelada como operacao aqui.
        #
        #   ERRO CONHECIDO: NFs de produto acabado (tipo 4) emitidas com 5902 — ex. SARET/
        #   2026/00006-9 (LF->FB) — sao classificacao fiscal incorreta (deveriam ser 5949).
        #   NAO usar como precedente.
        #
        # OBS.: Odoo decide o CFOP pela fiscal_position + natureza -> NAO hardcodar CFOP.
        # ====================================================================
        'l10n_br_tipo_pedido': 'dev-industrializacao',
        'move_type': 'out_invoice',
        'tipo_produto': [4],
        'fiscal_position_id': {
            (4, 5): 74,   # CD → LF: 'SAÍDA - REMESSA PARA RETRABALHO'
            (5, 4): 89,   # LF → CD: 'SAÍDA - RETRABALHO'
            (5, 1): 89,   # LF → FB: 'SAÍDA - RETRABALHO'
            (1, 5): 74,   # FB → LF: simetria com (4,5) — SEM precedente (P011)
        },
        'cfop_esperado': {
            (4, 5): '5949',  # CD → LF: confirmado RRET/2026/00008
            (5, 4): '5949',  # LF → CD: confirmado SARET/2026/00002
            (5, 1): '5949',  # LF → FB: retorno / ajuste de estoque (produto acabado)
            (1, 5): '5949',  # FB → LF: ASSUMIDO (sem precedente, simetria com CD→LF)
        },
        'entrada': {
            # CD → LF: entrada na LF (ENTRE). fp 86 'ENTRADA - RETRABALHO'. ENTRE/2026/05/0002.
            (4, 5): {'fiscal_position_id': 86, 'cfop': '1949',
                     'l10n_br_tipo_pedido_entrada': 'retorno'},
            # LF → CD: entrada na CD (ENTRE). fp 87 'ENTRADA - RETRABALHO'. ENTRE/2026/05/0001.
            (5, 4): {'fiscal_position_id': 87, 'cfop': '1949',
                     'l10n_br_tipo_pedido_entrada': 'outro'},
            # LF → FB (retorno/ajuste): entrada 1949 na FB. fp SEM precedente VALIDO
            # (historico LF->FB de produto tipo 4 e todo 5902, que e erro) -> canary.
            (5, 1): {'fiscal_position_id': None, 'cfop': '1949',
                     'l10n_br_tipo_pedido_entrada': 'outro'},
            # FB → LF: SEM precedente; entrada ASSUMIDA por simetria com (4,5). Canary fiscal pendente.
            (1, 5): {'fiscal_position_id': 86, 'cfop': '1949',
                     'l10n_br_tipo_pedido_entrada': 'retorno'},
        },
        'nf_referencia': 147772,
        'account_move_id_referencia': 590839,
        # Sem precedente VALIDO de 5949 produto tipo 4 em LF->FB nem FB->LF.
        # (5,1) tem NFs historicas, mas com 5902 (erro de classificacao) -> nao conta.
        'direcoes_sem_precedente_historico': [(1, 5), (5, 1)],
    },
    'transf-filial': {
        'l10n_br_tipo_pedido': 'transf-filial',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3, 4],
        'fiscal_position_id': {
            (1, 4): 20,  # FB → CD: 'SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS'
            (4, 1): 49,  # CD → FB: 'SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS'
        },
        'cfop_esperado': {
            (1, 4): '5152',  # FB → CD: 'Transferência de mercadoria adquirida/recebida de terceiros'
            (4, 1): '5151',  # CD → FB: 'Transferência de produção do estabelecimento'
        },
        'entrada': {
            # FB → CD: entrada no CD. fp 50 'ENTRADA - TRANSFERÊNCIA ENTRE FILIAIS'.
            # CFOP 1152 'Transferência p/ comercialização'. SDTRA/2026/00881 -> ENTTR/2026/05/0146.
            (1, 4): {'fiscal_position_id': 50, 'cfop': '1152',
                     'l10n_br_tipo_pedido_entrada': 'transf-filial'},
            # CD → FB: entrada na FB. fp 22 'ENTRADA - TRANSFERÊNCIA ENTRE FILIAIS'.
            # CFOP 1151 'Transferência p/ industrialização ou produção rural'. SDTRA/2026/00344 -> ENTTR/2026/05/0052.
            (4, 1): {'fiscal_position_id': 22, 'cfop': '1151',
                     'l10n_br_tipo_pedido_entrada': 'transf-filial'},
        },
        'nf_referencia': 94410,
        'account_move_id_referencia': 604472,
    },
    # ========================================================================
    # OPERACOES DE REFERENCIA (fluxo RecebimentoLF / faturamento de industrializacao).
    # NAO sao usadas pelo ajuste de inventario (resolver_operacao_por_tipo_produto NAO
    # as retorna). Modeladas para documentar a regra fiscal completa (confirmado 2026-05-21).
    # ========================================================================
    'venda-industrializacao': {
        # Industrializacao por encomenda COM cobranca. NF MISTA (2 CFOPs por tipo de produto):
        #   produto acabado (tipo 4)   -> 5124 'Industrializacao efetuada p/ outra empresa' (entrada 1124)
        #   insumos utilizados (1,2,3) -> 5902 'Retorno de mercadoria utilizada na industr.'  (entrada 1902)
        # Confirmado: VND/2026/00308 (605869) -> ENTSI/2026/05/0034 (606765).
        'l10n_br_tipo_pedido': 'venda-industrializacao',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3, 4],   # NF mista
        'uso': 'RecebimentoLF (faturamento industrializacao por encomenda) — NAO ajuste de inventario',
        'fiscal_position_id': {
            (5, 1): 111,  # LF → FB: 'SAÍDA - SERVIÇO DE INDUSTRIALIZAÇÃO'
        },
        'cfop_esperado': {
            # NF mista: CFOP por classe de produto
            (5, 1): {'produto_acabado': '5124', 'insumo_utilizado': '5902'},
        },
        'entrada': {
            (5, 1): {'fiscal_position_id': 88,  # 'ENTRADA - SERVIÇO INDUSTRIALIZAÇÃO'
                     'l10n_br_tipo_pedido_entrada': 'serv-industrializacao',
                     'cfop': {'produto_acabado': '1124', 'insumo_utilizado': '1902'}},
        },
        'nf_referencia': 605869,                # VND/2026/00308 (saida)
        'account_move_id_referencia': 606765,   # ENTSI/2026/05/0034 (entrada)
    },
    'vasilhame': {
        # Remessa de vasilhame / sacaria / pallet (embalagem retornavel, tipo 2). Operacao
        # PROPRIA — nao confundir com retorno de insumo (5902/5903) nem retrabalho (5949).
        # Confirmado: VAS/2026/00160 (692147), fp 64, CFOP 5921, produto tipo 2, LF → FB.
        'l10n_br_tipo_pedido': 'dev-vasilhame',
        'move_type': 'out_invoice',
        'tipo_produto': [2],            # embalagem (sacaria / vasilhame / pallet)
        'uso': 'Remessa de vasilhame retornavel — NAO ajuste de inventario',
        'fiscal_position_id': {
            (5, 1): 64,  # LF → FB: 'REMESSA DE VASILHAME'
        },
        'cfop_esperado': {(5, 1): '5921'},
        'entrada': {
            # NAO CONFIRMADA: remessa de vasilhame nao gerou in_invoice por chave (a FB pode
            # nao escriturar entrada, ou estava pendente). 1920 'Entrada de vasilhame ou sacaria'
            # e o CFOP candidato (visto como LINHA em NF de retrabalho, ex. move 603226) — validar.
            (5, 1): {'fiscal_position_id': None, 'cfop': '1920',
                     'l10n_br_tipo_pedido_entrada': 'ent-vasilhame'},
        },
        'nf_referencia': 692147,  # VAS/2026/00160 (saida)
    },
}


def get_operacao(tipo_operacao: str) -> Dict[str, Any]:
    """Retorna entrada da matriz.

    Raises:
        KeyError: se tipo_operacao nao existe.
    """
    if tipo_operacao not in MATRIZ_INTERCOMPANY:
        raise KeyError(
            f"tipo_operacao={tipo_operacao!r} nao em MATRIZ_INTERCOMPANY. "
            f"Validos: {sorted(MATRIZ_INTERCOMPANY)}"
        )
    return MATRIZ_INTERCOMPANY[tipo_operacao]


def resolver_operacao_por_tipo_produto(*, tipo: int, company_id: int, sinal: int) -> str:
    """
    Dada uma diferenca de inventario, decide qual operacao usar.

    Args:
        tipo: 1/2/3/4 (primeiro digito do cod_produto)
        company_id: 1 (FB), 4 (CD), 5 (LF)
        sinal: +1 se ajuste positivo (estoque deve aumentar),
               -1 se negativo (estoque deve diminuir)

    Returns:
        chave de MATRIZ_INTERCOMPANY. Apenas operacoes de AJUSTE de inventario:
        industrializacao, perda, dev-industrializacao, transf-filial. Os tipos de
        referencia 'venda-industrializacao' e 'vasilhame' NAO sao retornados aqui
        (pertencem ao fluxo RecebimentoLF, nao ao ajuste de inventario).

    Raises:
        ValueError: se combinacao desconhecida.
    """
    if company_id == 5:  # LF
        if tipo == 4:
            return 'dev-industrializacao'
        if tipo in (1, 2, 3):
            return 'industrializacao' if sinal > 0 else 'perda'
        raise ValueError(f'tipo={tipo} nao suportado para LF (company_id=5)')

    if company_id in (1, 4):
        return 'transf-filial'

    raise ValueError(f'company_id={company_id} nao reconhecido (esperado: 1, 4 ou 5)')


def resolver_fiscal_position(tipo_operacao: str, company_origem: int,
                              company_destino: int) -> int:
    """Resolve `fiscal_position_id` da SAIDA para uma direcao especifica.

    Args:
        tipo_operacao: chave de MATRIZ_INTERCOMPANY.
        company_origem: company_id origem.
        company_destino: company_id destino.

    Returns:
        fiscal_position_id Odoo (da SAIDA / out_invoice).

    Raises:
        KeyError: se tipo_operacao nao existe.
        ValueError: se direcao (origem, destino) nao mapeada para o tipo.
    """
    op = get_operacao(tipo_operacao)
    key: Tuple[int, int] = (company_origem, company_destino)
    fp = op['fiscal_position_id'].get(key)
    if fp is None:
        raise ValueError(
            f"fiscal_position nao mapeada para tipo={tipo_operacao!r} "
            f"direcao=({company_origem}, {company_destino}). "
            f"Direcoes validas: {sorted(op['fiscal_position_id'].keys())}"
        )
    return fp


def resolver_entrada(tipo_operacao: str, company_origem: int,
                     company_destino: int) -> Dict[str, Any]:
    """Resolve os dados da NF de ENTRADA (in_invoice no destino) para uma direcao.

    A chave e a MESMA tupla da SAIDA (company_origem, company_destino): a entrada e
    escriturada no `company_destino` a partir do DFe emitido pela `company_origem`.

    Args:
        tipo_operacao: chave de MATRIZ_INTERCOMPANY.
        company_origem: company_id origem da SAIDA.
        company_destino: company_id destino da SAIDA (onde a entrada e escriturada).

    Returns:
        dict {fiscal_position_id, cfop, l10n_br_tipo_pedido_entrada}.
        `fiscal_position_id` pode ser None quando o caso ainda nao tem precedente no Odoo.
        `cfop` e str na maioria das operacoes; para NF MISTA (ex.: 'venda-industrializacao')
        e um dict {classe_produto: cfop} (ex.: {'produto_acabado': '1124', 'insumo_utilizado': '1902'}).
        Callers devem checar o tipo (str vs dict) antes de tratar como string.

    Raises:
        KeyError: se tipo_operacao nao existe.
        ValueError: se o tipo nao tem `entrada` auditada ou a direcao nao esta mapeada.
    """
    op = get_operacao(tipo_operacao)
    entrada = op.get('entrada')
    if not entrada:
        raise ValueError(
            f"tipo_operacao={tipo_operacao!r} nao possui dados de 'entrada' auditados."
        )
    key: Tuple[int, int] = (company_origem, company_destino)
    dados = entrada.get(key)
    if dados is None:
        raise ValueError(
            f"entrada nao mapeada para tipo={tipo_operacao!r} "
            f"direcao=({company_origem}, {company_destino}). "
            f"Direcoes validas: {sorted(entrada.keys())}"
        )
    return dados


# ============================================================================
# ACAO_PARA_DIRECAO — mapa central acao_decidida -> (tipo_op, co, cd)
#
# CR-F8 v15c (CRITICAL Reviewer B conf 95): consolidado aqui para eliminar
# duplicacao entre `inventario_pipeline_service.py:48-57` e
# `app/odoo/estoque/orchestrators/inventario_pipeline.py:84-97` (renomeado
# de faturamento_pipeline em v27+ S3). Ambos importam daqui — fonte unica
# de verdade.
#
# Cada `acao_decidida` mapeia para 1 tupla unica (tipo_op, company_origem,
# company_destino). Skill 8 orchestrator agrupa por `acao_decidida` (NAO por
# `(co, tipo_op)` — CR-C2 v15b) para preservar partner_id correto em
# DEV_LF_FB (cd=1) vs DEV_LF_CD (cd=4) que compartilham tipo_op.
# ============================================================================

ACAO_PARA_DIRECAO: Dict[str, Tuple[str, int, int]] = {
    'TRANSFERIR_CD_FB':       ('transf-filial',        4, 1),
    'TRANSFERIR_FB_CD':       ('transf-filial',        1, 4),
    'INDUSTRIALIZACAO_FB_LF': ('industrializacao',     1, 5),
    'PERDA_LF_FB':            ('perda',                5, 1),
    'DEV_FB_LF':              ('dev-industrializacao', 1, 5),
    'DEV_LF_FB':              ('dev-industrializacao', 5, 1),
    'DEV_CD_LF':              ('dev-industrializacao', 4, 5),
    'DEV_LF_CD':              ('dev-industrializacao', 5, 4),
}


# Subset de `acao_decidida` que dispara pipeline de picking (ETAPA B Skill 8).
# Equivale a `ACAO_PARA_DIRECAO.keys()` — proxy semantico (filtro pipeline,
# NAO matriz fiscal — por isso fica em `operacoes_fiscais.py` mas como
# constante derivada).
ACOES_PICKING: frozenset = frozenset(ACAO_PARA_DIRECAO.keys())


# ============================================================================
# ACAO_PARA_CFOP_ENTRADA — mapa CFOP saida (5xxx) -> CFOP entrada (1xxx).
#
# CR-D17 v14a (script 09 L1300-1305): centralizado aqui (era inline no
# script) para uso por ETAPA E (RecebimentoLf criar X->FB) na Skill 8 v17.
#
# Razao: Odoo da FB so tem `fiscal_position` cadastrada para CFOPs de
# entrada (1xxx). Gravar 5xxx no `RecebimentoLfLote.cfop` causa "CFOP nao
# cadastrado".
# ============================================================================

ACAO_PARA_CFOP_ENTRADA: Dict[str, str] = {
    'PERDA_LF_FB':            '1903',  # saida 5903
    'TRANSFERIR_CD_FB':       '1152',  # saida 5152
    'TRANSFERIR_FB_CD':       '1152',  # saida 5152 (FB->CD)
    'DEV_FB_LF':              '1949',  # saida 5949
    'DEV_LF_FB':              '1949',  # saida 5949
    'DEV_CD_LF':              '1949',  # saida 5949
    'DEV_LF_CD':              '1949',  # saida 5949
    'INDUSTRIALIZACAO_FB_LF': '1901',  # saida 5901
}


# ============================================================================
# ACOES_ENTRADA_FB — subset de acoes cuja ETAPA E (Skill 8 v17) cria
# RecebimentoLf no destino FB.
#
# CR v14a (script 09 L1261-1263): centralizado aqui (era inline no script).
# ============================================================================

ACOES_ENTRADA_FB: frozenset = frozenset({
    'PERDA_LF_FB',       # LF -> FB (RecebimentoLf na FB)
    'TRANSFERIR_CD_FB',  # CD -> FB
    'DEV_LF_FB',         # LF -> FB
    'DEV_CD_LF',         # CD -> LF (RecebimentoLf na LF — adicionar futuro v17)
})
