#!/usr/bin/env python3
"""
Script: gerar_embarque.py
Acao: GERA UM EMBARQUE PRONTO (Cotacao + Embarque + EmbarqueItem) a partir de
      Separacoes ja escolhidas, propagando cotacao_id na Separacao (-> COTADO).

NAO lanca frete. O embarque nasce PRONTO mas SEM data_embarque: o frete nasce
depois, no fluxo normal de portaria/faturamento (este script NUNCA chama
processar_lancamento_automatico_fretes / lancar_frete_automatico).

Replica a sequencia oficial de criacao de Embarque (app/cotacao/routes.py:1162
`fechar_frete`, ramo Nacom) DENTRO de app_context, sem HTTP. Reusa as funcoes
oficiais (TabelaFreteManager, obter_proximo_numero_embarque,
LocalizacaoService, Separacao.atualizar_cotacao) — NAO reimplementa nada delas.

DOIS MODOS:

  (A) ESPELHO de um embarque existente:
      --embarque-origem <id>
      Copia os campos tabela_* (snapshot congelado) do Embarque origem (DIRETA)
      ou de cada EmbarqueItem origem (FRACIONADA). NAO re-busca TabelaFrete.
      Os lotes a embarcar vem dos EmbarqueItem ativos Nacom do embarque origem,
      salvo se --lotes for passado para restringir.

  (B) SEPARACOES SOLTAS ja escolhidas:
      --lotes '["LOTE_...","LOTE_..."]' --transportadora-id <id> --tabela <nome>
      Monta dados_tabela a partir da TabelaFrete indicada (uf_origem=SP,
      uf_destino derivado dos pedidos, tipo_carga = --tipo, modalidade = --modalidade).

GUARD-RAILS:
- --dry-run e o DEFAULT. Sem --confirmar SO simula e imprime o plano.
- --user-id OBRIGATORIO, validado contra a tabela usuarios.
- v1 SO ramo Nacom: RECUSA lotes com prefixo CARVIA-/ASSAI-.
- DIRETA exige todos os pedidos do MESMO UF normalizado.
- Idempotencia: avisa se os lotes ja tem embarque ativo.
- Totais recalculados do banco (NAO confia em entrada do usuario).
- NUNCA INSERT raw — so ORM via funcoes oficiais.

EXIT CODES:
  0  efetivado (--confirmar com sucesso)
  4  dry-run OK (simulacao bem-sucedida; default sem --confirmar)
  1  falha (erro de execucao / validacao de negocio)
  2  uso (parametros invalidos)

Uso:
    # ESPELHO (dry-run default)
    python gerar_embarque.py --user-id 74 --embarque-origem 5807
    # ESPELHO efetivo
    python gerar_embarque.py --user-id 74 --embarque-origem 5807 --confirmar

    # SOLTAS (dry-run default)
    python gerar_embarque.py --user-id 74 \
        --lotes '["LOTE_20251004_1","LOTE_20251004_2"]' \
        --transportadora-id 12 --tabela "TABELA AM" --tipo DIRETA --modalidade "FRETE PESO"
    # SOLTAS efetivo
    python gerar_embarque.py --user-id 74 --lotes '[...]' --transportadora-id 12 \
        --tabela "TABELA AM" --tipo FRACIONADA --confirmar
"""
import sys
import os
import json
import argparse
from datetime import date, datetime
from decimal import Decimal

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# ---------------------------------------------------------------------------
# Exit codes (convencao do orquestrador)
# ---------------------------------------------------------------------------
EXIT_OK = 0       # efetivado
EXIT_FALHA = 1    # falha
EXIT_USO = 2      # uso (parametros invalidos)
EXIT_DRYRUN = 4   # dry-run OK


# ---------------------------------------------------------------------------
# Acessores LAZY (mantem o modulo importavel sem app_context, p/ teste)
# ---------------------------------------------------------------------------
def _get_db():
    from app import db  # type: ignore # noqa: E402
    return db


def _get_usuario_model():
    from app.auth.models import Usuario  # type: ignore # noqa: E402
    return Usuario


def criar_app_context():
    from app import create_app  # type: ignore # noqa: E402
    app = create_app()
    return app.app_context()


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ===========================================================================
# PARTES PURAS / VALIDACOES (testaveis sem banco)
# ===========================================================================
_PREFIXOS_RECUSADOS = ('CARVIA-', 'ASSAI-SEP-', 'ASSAI-')


def validar_lotes_nacom(lotes):
    """v1 so ramo Nacom: recusa lotes com prefixo CARVIA-/ASSAI-.

    Returns:
        (ok: bool, recusados: list[str])
    """
    recusados = [
        lote for lote in lotes
        if any(str(lote).startswith(p) for p in _PREFIXOS_RECUSADOS)
    ]
    return (len(recusados) == 0, recusados)


def resolver_usuario(user_id):
    """Valida --user-id contra a tabela usuarios (Cotacao.usuario_id NOT NULL).

    Returns o objeto Usuario ou None se nao existe.
    """
    db = _get_db()
    Usuario = _get_usuario_model()  # noqa: F841 (forca import; valida modelo)
    return db.session.get(Usuario, user_id)


def validar_uf_unico_direta(pedidos):
    """DIRETA exige todos os pedidos do MESMO UF normalizado.

    Usa LocalizacaoService.normalizar_uf_com_regras (nao basta cod_uf cru).

    Returns:
        (ok: bool, ufs: set[str])
    """
    from app.utils.localizacao import LocalizacaoService  # type: ignore # noqa: E402
    ufs = set()
    for p in pedidos:
        uf = LocalizacaoService.normalizar_uf_com_regras(
            getattr(p, 'cod_uf', None),
            getattr(p, 'nome_cidade', None),
            getattr(p, 'rota', None),
        )
        if uf:
            ufs.add(uf)
    return (len(ufs) <= 1, ufs)


def dados_tabela_de_espelho_direta(embarque):
    """Snapshot de tabela a partir do Embarque origem (modo ESPELHO, DIRETA).

    Le os campos tabela_* JA congelados no Embarque (NAO re-busca TabelaFrete).
    icms_destino vem de localidades (campo proprio do embarque).
    """
    from app.utils.tabela_frete_manager import TabelaFreteManager  # type: ignore # noqa: E402
    dados = TabelaFreteManager.preparar_dados_tabela(embarque)
    dados['icms_destino'] = getattr(embarque, 'icms_destino', 0) or 0
    return dados


def dados_tabela_de_espelho_item(item):
    """Snapshot de tabela a partir de UM EmbarqueItem origem (ESPELHO, FRACIONADA)."""
    from app.utils.tabela_frete_manager import TabelaFreteManager  # type: ignore # noqa: E402
    dados = TabelaFreteManager.preparar_dados_tabela(item)
    dados['icms_destino'] = getattr(item, 'icms_destino', 0) or 0
    return dados


def dados_tabela_de_tabela_frete(tabela, icms_destino=0):
    """Snapshot de tabela a partir de uma TabelaFrete (modo SOLTAS).

    TabelaFrete tem campos SEM prefixo; TabelaFreteManager normaliza.
    """
    from app.utils.tabela_frete_manager import TabelaFreteManager  # type: ignore # noqa: E402
    dados = TabelaFreteManager.preparar_dados_tabela(tabela)
    dados['icms_destino'] = icms_destino or 0
    return dados


# ===========================================================================
# CONSULTAS AO BANCO (precisam de app_context)
# ===========================================================================
def carregar_pedidos(lotes):
    """Carrega os Pedido (VIEW) dos lotes em 1 query batch. Retorna lista."""
    from app.pedidos.models import Pedido  # type: ignore # noqa: E402
    if not lotes:
        return []
    return Pedido.query.filter(Pedido.separacao_lote_id.in_(lotes)).all()


def lotes_de_embarque_origem(embarque_origem_id):
    """Modo ESPELHO: lotes Nacom ativos do embarque origem.

    Recusa itens CarVia (carvia_cotacao_id / prefixo CARVIA-). Retorna
    (embarque_origem, lotes_nacom) — embarque_origem None se nao encontrado.
    """
    from app.embarques.models import Embarque, EmbarqueItem  # type: ignore # noqa: E402
    db = _get_db()
    embarque = db.session.get(Embarque, embarque_origem_id)
    if not embarque:
        return None, []

    itens = EmbarqueItem.query.filter(
        EmbarqueItem.embarque_id == embarque.id,
        EmbarqueItem.status == 'ativo',
    ).all()

    lotes = []
    for it in itens:
        lote = it.separacao_lote_id
        if not lote:
            continue
        if str(lote).startswith(_PREFIXOS_RECUSADOS):
            continue  # CarVia/Assai fora do v1 Nacom
        if it.carvia_cotacao_id is not None:
            continue
        if lote not in lotes:
            lotes.append(lote)
    return embarque, lotes


def lotes_ja_em_embarque_ativo(lotes):
    """Idempotencia: retorna dict {lote: numero_embarque} dos lotes que JA
    pertencem a um EmbarqueItem ativo de um Embarque ativo."""
    from app.embarques.models import Embarque, EmbarqueItem  # type: ignore # noqa: E402
    if not lotes:
        return {}
    rows = (
        EmbarqueItem.query
        .join(Embarque, Embarque.id == EmbarqueItem.embarque_id)
        .filter(
            EmbarqueItem.separacao_lote_id.in_(lotes),
            EmbarqueItem.status == 'ativo',
            Embarque.status == 'ativo',
        )
        .all()
    )
    existentes = {}
    for it in rows:
        emb = _get_db().session.get(Embarque, it.embarque_id)
        existentes[it.separacao_lote_id] = emb.numero if emb else None
    return existentes


def buscar_tabela_frete(transportadora_id, nome_tabela, uf_destino, tipo, modalidade):
    """Modo SOLTAS: busca a TabelaFrete oficial (uf_origem=SP). Pode retornar None."""
    from sqlalchemy import func  # type: ignore # noqa: E402
    from app.tabelas.models import TabelaFrete  # type: ignore # noqa: E402
    q = TabelaFrete.query.filter(
        TabelaFrete.transportadora_id == transportadora_id,
        func.upper(func.trim(TabelaFrete.nome_tabela)) == func.upper(func.trim(nome_tabela)),
        TabelaFrete.uf_origem == 'SP',
        TabelaFrete.uf_destino == uf_destino,
        TabelaFrete.tipo_carga == tipo,
    )
    if modalidade:
        q = q.filter(func.upper(func.trim(TabelaFrete.modalidade)) == func.upper(func.trim(modalidade)))
    return q.first()


def buscar_icms_destino(pedidos):
    """ICMS de destino: do primeiro pedido com cidade resolvida (IBGE -> nome)."""
    from app.localidades.models import Cidade  # type: ignore # noqa: E402
    for pedido in pedidos:
        cidade_destino = None
        if getattr(pedido, 'codigo_ibge', None):
            cidade_destino = Cidade.query.filter_by(codigo_ibge=pedido.codigo_ibge).first()
        if not cidade_destino:
            cidade_destino = Cidade.query.filter_by(
                nome=getattr(pedido, 'cidade_normalizada', None),
                uf=getattr(pedido, 'cod_uf', None),
            ).first()
        if cidade_destino:
            return cidade_destino.icms or 0
    return 0


def calcular_totais(pedidos):
    """Recalcula totais do BANCO (NAO confia no usuario)."""
    valor = sum(p.valor_saldo_total or 0 for p in pedidos)
    peso = sum(p.peso_total or 0 for p in pedidos)
    pallets = sum(p.pallet_total or 0 for p in pedidos)
    if pallets < 0:
        pallets = 0
    return round(valor, 2), round(peso, 2), round(pallets, 2)


# ===========================================================================
# SIMULAR / EXECUTAR
# ===========================================================================
def preparar_plano(args):
    """Resolve modo, valida e monta o plano (dict) usado tanto para dry-run
    quanto para a execucao. Levanta ValueError em falha de negocio."""
    from app.utils.localizacao import LocalizacaoService  # type: ignore # noqa: E402

    modo = 'ESPELHO' if args.embarque_origem else 'SOLTAS'
    tipo = (args.tipo or 'FRACIONADA').upper()
    if tipo not in ('DIRETA', 'FRACIONADA'):
        raise ValueError(f"--tipo invalido: {tipo} (use DIRETA ou FRACIONADA)")

    embarque_origem = None
    transportadora_id = args.transportadora_id

    # ---- Resolver lotes + transportadora por modo ----
    if modo == 'ESPELHO':
        embarque_origem, lotes = lotes_de_embarque_origem(args.embarque_origem)
        if not embarque_origem:
            raise ValueError(f"Embarque origem {args.embarque_origem} nao encontrado")
        if args.lotes:  # restringe se o usuario passou subset
            lotes = [l for l in lotes if l in args.lotes]
        transportadora_id = embarque_origem.transportadora_id
        tipo = (embarque_origem.tipo_carga or tipo).upper()
        if not lotes:
            raise ValueError("Embarque origem nao tem lotes Nacom ativos para espelhar")
    else:  # SOLTAS
        lotes = list(args.lotes or [])
        if not lotes:
            raise ValueError("Modo SOLTAS exige --lotes")
        if not transportadora_id:
            raise ValueError("Modo SOLTAS exige --transportadora-id")
        if not args.tabela:
            raise ValueError("Modo SOLTAS exige --tabela")

    # ---- Guard-rail: v1 so Nacom ----
    ok_nacom, recusados = validar_lotes_nacom(lotes)
    if not ok_nacom:
        raise ValueError(
            f"v1 so suporta ramo Nacom. Lotes recusados (CarVia/Assai): {recusados}"
        )

    # ---- Carregar pedidos do banco ----
    pedidos = carregar_pedidos(lotes)
    if not pedidos:
        raise ValueError(f"Nenhum Pedido encontrado para os lotes: {lotes}")
    lotes_encontrados = {p.separacao_lote_id for p in pedidos}
    faltantes = [l for l in lotes if l not in lotes_encontrados]
    if faltantes:
        raise ValueError(f"Lotes sem Pedido correspondente: {faltantes}")

    # ---- DIRETA exige UF normalizado unico ----
    if tipo == 'DIRETA':
        ok_uf, ufs = validar_uf_unico_direta(pedidos)
        if not ok_uf:
            raise ValueError(
                f"DIRETA exige UF unico normalizado, mas ha multiplos: {sorted(ufs)}. "
                "Use --tipo FRACIONADA ou separe os lotes por UF."
            )
        uf_destino = next(iter(ufs)) if ufs else None
    else:
        # FRACIONADA: uf por item; para buscar TabelaFrete usamos o UF do 1o pedido
        uf_destino = LocalizacaoService.normalizar_uf_com_regras(
            getattr(pedidos[0], 'cod_uf', None),
            getattr(pedidos[0], 'nome_cidade', None),
            getattr(pedidos[0], 'rota', None),
        )

    # ---- dados_tabela (snapshot) por modo ----
    icms_destino = buscar_icms_destino(pedidos)
    tabela_frete_encontrada = None
    if modo == 'ESPELHO':
        if tipo == 'DIRETA':
            dados_tabela = dados_tabela_de_espelho_direta(embarque_origem)
        else:
            # FRACIONADA: usa o snapshot de um item ativo Nacom do embarque origem
            item_ref = _item_ref_espelho(embarque_origem.id)
            if item_ref is None:
                raise ValueError(
                    "Embarque origem FRACIONADA sem EmbarqueItem Nacom para espelhar tabela"
                )
            dados_tabela = dados_tabela_de_espelho_item(item_ref)
        # icms_destino do proprio embarque/item ja vem; se 0, usa o resolvido por cidade
        if not dados_tabela.get('icms_destino'):
            dados_tabela['icms_destino'] = icms_destino
    else:  # SOLTAS
        tabela_frete_encontrada = buscar_tabela_frete(
            transportadora_id, args.tabela, uf_destino, tipo, args.modalidade
        )
        if not tabela_frete_encontrada:
            raise ValueError(
                f"TabelaFrete nao encontrada: transportadora={transportadora_id} "
                f"tabela='{args.tabela}' uf_destino={uf_destino} tipo={tipo} "
                f"modalidade={args.modalidade}. Frete jamais com tabela zerada."
            )
        dados_tabela = dados_tabela_de_tabela_frete(tabela_frete_encontrada, icms_destino)

    # ---- Totais recalculados do banco ----
    valor_total, peso_total, pallets_total = calcular_totais(pedidos)

    # ---- Idempotencia ----
    ja_em_embarque = lotes_ja_em_embarque_ativo(lotes)

    # ---- Itens previstos ----
    from app.utils.localizacao import LocalizacaoService as _LS  # noqa
    itens_previstos = []
    for p in pedidos:
        cidade_fmt, uf_correto = _LS.obter_cidade_destino_embarque(p)
        itens_previstos.append({
            'separacao_lote_id': p.separacao_lote_id,
            'cnpj_cliente': getattr(p, 'cnpj_cpf', None),
            'cliente': getattr(p, 'raz_social_red', None),
            'pedido': getattr(p, 'num_pedido', None),
            'peso': float(p.peso_total or 0),
            'valor': float(p.valor_saldo_total or 0),
            'pallets': float(p.pallet_total or 0),
            'uf_destino': uf_correto,
            'cidade_destino': cidade_fmt,
        })

    return {
        'modo': modo,
        'tipo_carga': tipo,
        'transportadora_id': transportadora_id,
        'uf_destino_referencia': uf_destino,
        'lotes': lotes,
        'pedidos': pedidos,                # objetos ORM (so p/ execucao)
        'dados_tabela': dados_tabela,
        'totais': {
            'valor_total': valor_total,
            'peso_total': peso_total,
            'pallet_total': pallets_total,
        },
        'icms_destino': icms_destino,
        'itens_previstos': itens_previstos,
        'ja_em_embarque_ativo': ja_em_embarque,
        'numero_embarque_previsto': _proximo_numero_previsto(),
        'embarque_origem': args.embarque_origem,
    }


def _item_ref_espelho(embarque_id):
    """Retorna 1 EmbarqueItem ativo Nacom do embarque origem (p/ snapshot FRACIONADA)."""
    from app.embarques.models import EmbarqueItem  # type: ignore # noqa: E402
    return (
        EmbarqueItem.query.filter(
            EmbarqueItem.embarque_id == embarque_id,
            EmbarqueItem.status == 'ativo',
            EmbarqueItem.carvia_cotacao_id.is_(None),
        ).first()
    )


def _proximo_numero_previsto():
    from app.utils.embarque_numero import obter_proximo_numero_embarque  # type: ignore # noqa: E402
    return obter_proximo_numero_embarque()


def _plano_json(plano):
    """Versao serializavel do plano (sem objetos ORM)."""
    return {
        'modo': plano['modo'],
        'tipo_carga': plano['tipo_carga'],
        'transportadora_id': plano['transportadora_id'],
        'uf_destino_referencia': plano['uf_destino_referencia'],
        'lotes': plano['lotes'],
        'dados_tabela': plano['dados_tabela'],
        'totais': plano['totais'],
        'icms_destino': plano['icms_destino'],
        'numero_embarque_previsto': plano['numero_embarque_previsto'],
        'itens_previstos': plano['itens_previstos'],
        'ja_em_embarque_ativo': plano['ja_em_embarque_ativo'],
        'embarque_origem': plano['embarque_origem'],
        'aviso_frete': (
            'Frete NAO sera lancado por este script. O embarque nasce SEM '
            'data_embarque; o frete nascera no fluxo normal de portaria/faturamento.'
        ),
    }


def executar(plano, usuario):
    """Efetiva a criacao do embarque, replicando a sequencia oficial Nacom de
    fechar_frete DENTRO de app_context. Usa SO ORM + funcoes oficiais."""
    from app import db  # type: ignore # noqa: E402
    from app.cotacao.models import Cotacao  # type: ignore # noqa: E402
    from app.embarques.models import Embarque, EmbarqueItem  # type: ignore # noqa: E402
    from app.separacao.models import Separacao  # type: ignore # noqa: E402
    from app.rastreamento.models import RastreamentoEmbarque  # type: ignore # noqa: E402
    from app.transportadoras.models import Transportadora  # type: ignore # noqa: E402
    from app.utils.tabela_frete_manager import TabelaFreteManager  # type: ignore # noqa: E402
    from app.utils.embarque_numero import obter_proximo_numero_embarque  # type: ignore # noqa: E402
    from app.utils.localizacao import LocalizacaoService  # type: ignore # noqa: E402
    from app.utils.timezone import agora_utc_naive  # type: ignore # noqa: E402

    tipo = plano['tipo_carga']
    transportadora_id = plano['transportadora_id']
    dados_tabela = plano['dados_tabela']
    pedidos = plano['pedidos']
    totais = plano['totais']

    transportadora = db.session.get(Transportadora, transportadora_id)
    if not transportadora:
        raise ValueError(f"Transportadora {transportadora_id} nao encontrada")

    try:
        # 3. Cria Cotacao
        cotacao = Cotacao(
            usuario_id=usuario.id,
            transportadora_id=transportadora_id,
            data_fechamento=agora_utc_naive(),
            status='Fechada',
            tipo_carga=tipo,
            valor_total=totais['valor_total'],
            peso_total=totais['peso_total'],
        )
        db.session.add(cotacao)
        db.session.flush()  # gera cotacao.id

        # 4. Cria Embarque (NAO seta data_embarque -> frete nasce na portaria)
        novo_numero = obter_proximo_numero_embarque()
        embarque = Embarque(
            transportadora_id=transportadora_id,
            status='ativo',
            numero=novo_numero,
            tipo_cotacao='Automatica',
            tipo_carga=tipo,
            valor_total=totais['valor_total'],
            peso_total=totais['peso_total'],
            pallet_total=totais['pallet_total'],
            criado_em=agora_utc_naive(),
            criado_por=usuario.nome,
            cotacao_id=cotacao.id,
            transportadora_optante=transportadora.optante,
        )
        if tipo == 'DIRETA':
            TabelaFreteManager.atribuir_campos_objeto(embarque, dados_tabela)
            embarque.icms_destino = dados_tabela.get('icms_destino')
        db.session.add(embarque)
        db.session.flush()  # gera embarque.id

        # 5. DIRETA: cria RastreamentoEmbarque
        if tipo == 'DIRETA':
            rastreamento = RastreamentoEmbarque(
                embarque_id=embarque.id,
                criado_por=usuario.nome,
            )
            db.session.add(rastreamento)
            db.session.flush()

        # 6. Loop ramo Nacom -> EmbarqueItem
        for pedido in pedidos:
            cidade_fmt, uf_correto = LocalizacaoService.obter_cidade_destino_embarque(pedido)

            nota_fiscal = None
            if pedido.separacao_lote_id and pedido.num_pedido:
                sep_com_nf = (
                    Separacao.query
                    .filter_by(
                        separacao_lote_id=pedido.separacao_lote_id,
                        num_pedido=pedido.num_pedido,
                    )
                    .filter(Separacao.numero_nf.isnot(None))
                    .first()
                )
                if sep_com_nf:
                    nota_fiscal = sep_com_nf.numero_nf

            item = EmbarqueItem(
                embarque_id=embarque.id,
                separacao_lote_id=pedido.separacao_lote_id,
                cnpj_cliente=pedido.cnpj_cpf,
                cliente=pedido.raz_social_red,
                pedido=pedido.num_pedido,
                nota_fiscal=nota_fiscal,
                peso=pedido.peso_total or 0,
                valor=pedido.valor_saldo_total or 0,
                pallets=pedido.pallet_total or 0,
                uf_destino=uf_correto,
                cidade_destino=cidade_fmt,
                volumes=None,
            )
            # Tabela: FRACIONADA grava no item; DIRETA ja gravou no embarque
            if tipo == 'FRACIONADA':
                TabelaFreteManager.atribuir_campos_objeto(item, dados_tabela)
                item.icms_destino = dados_tabela.get('icms_destino', 0)
            db.session.add(item)

        # 7. commit -> entao propaga cotacao via funcao oficial (COTADO via listener)
        db.session.commit()

        for item in embarque.itens:
            if item.separacao_lote_id and item.status == 'ativo':
                Separacao.atualizar_cotacao(
                    separacao_lote_id=item.separacao_lote_id,
                    cotacao_id=cotacao.id,
                    nf_cd=False,
                )

        db.session.commit()

        return {
            'success': True,
            'cotacao_id': cotacao.id,
            'embarque_id': embarque.id,
            'numero_embarque': embarque.numero,
            'tipo_carga': tipo,
            'itens_criados': len(embarque.itens),
            'totais': totais,
            'aviso_frete': (
                'Embarque criado SEM data_embarque. Frete nascera no fluxo normal '
                'de portaria/faturamento (este script NAO lanca frete).'
            ),
        }
    except Exception:
        db.session.rollback()
        raise


# ===========================================================================
# CLI
# ===========================================================================
def _parse_lotes(valor):
    if not valor:
        return None
    try:
        parsed = json.loads(valor)
    except json.JSONDecodeError:
        raise ValueError("--lotes deve ser um JSON array, ex: '[\"LOTE_1\",\"LOTE_2\"]'")
    if not isinstance(parsed, list):
        raise ValueError("--lotes deve ser um JSON array")
    return [str(x) for x in parsed]


def build_parser():
    parser = argparse.ArgumentParser(
        description='Gera um embarque PRONTO (Cotacao + Embarque + EmbarqueItem) sem lancar frete.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--user-id', type=int, required=True,
                        help='ID do usuario (validado contra tabela usuarios; OBRIGATORIO)')
    # Modo A: espelho
    parser.add_argument('--embarque-origem', type=int,
                        help='Modo ESPELHO: id do Embarque a espelhar (tabela congelada)')
    # Modo B: soltas
    parser.add_argument('--lotes', type=str,
                        help='Modo SOLTAS: JSON array de separacao_lote_id')
    parser.add_argument('--transportadora-id', type=int,
                        help='Modo SOLTAS: id da transportadora')
    parser.add_argument('--tabela', type=str,
                        help='Modo SOLTAS: nome da TabelaFrete (uf_origem=SP)')
    parser.add_argument('--tipo', type=str, choices=['DIRETA', 'FRACIONADA'],
                        help='Tipo de carga (default FRACIONADA; no ESPELHO herda do origem)')
    parser.add_argument('--modalidade', type=str,
                        help='Modalidade da tabela (ex: "FRETE PESO"); modo SOLTAS')
    # Confirmacao
    parser.add_argument('--confirmar', action='store_true',
                        help='Efetiva a criacao. Sem isso, apenas simula (dry-run).')
    return parser


def main(argv=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return EXIT_USO

    # Parse lotes
    try:
        args.lotes = _parse_lotes(args.lotes)
    except ValueError as e:
        print(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False, indent=2))
        return EXIT_USO

    # Validacao de uso: precisa de UM modo
    if not args.embarque_origem and not args.lotes:
        print(json.dumps({
            'success': False,
            'error': 'Informe --embarque-origem (modo ESPELHO) OU --lotes (modo SOLTAS)',
        }, ensure_ascii=False, indent=2))
        return EXIT_USO

    with criar_app_context():
        # --user-id validado contra tabela usuarios
        usuario = resolver_usuario(args.user_id)
        if not usuario:
            print(json.dumps({
                'success': False,
                'error': f'--user-id {args.user_id} nao existe na tabela usuarios',
            }, ensure_ascii=False, indent=2))
            return EXIT_FALHA

        # Monta o plano (valida regras de negocio)
        try:
            plano = preparar_plano(args)
        except ValueError as e:
            print(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False, indent=2))
            return EXIT_FALHA

        plano_json = _plano_json(plano)

        if not args.confirmar:
            saida = {
                'success': True,
                'modo_execucao': 'DRY-RUN (simulacao)',
                'aviso': 'Use --confirmar para efetivar a criacao do embarque.',
                'usuario': {'id': usuario.id, 'nome': usuario.nome},
                'plano': plano_json,
            }
            if plano_json['ja_em_embarque_ativo']:
                saida['alerta_idempotencia'] = (
                    'Alguns lotes JA pertencem a embarque(s) ativo(s) — reexecutar '
                    'criaria Cotacao/Embarque duplicados: '
                    f"{plano_json['ja_em_embarque_ativo']}"
                )
            print(json.dumps(saida, default=decimal_default, ensure_ascii=False, indent=2))
            return EXIT_DRYRUN

        # --confirmar: bloqueia se idempotencia detecta embarque ativo
        if plano_json['ja_em_embarque_ativo']:
            print(json.dumps({
                'success': False,
                'error': (
                    'Lotes ja em embarque ativo — abortando para nao duplicar '
                    'Cotacao/Embarque: '
                    f"{plano_json['ja_em_embarque_ativo']}"
                ),
            }, ensure_ascii=False, indent=2))
            return EXIT_FALHA

        try:
            resultado = executar(plano, usuario)
        except Exception as e:
            print(json.dumps({
                'success': False,
                'error': f'Erro ao executar criacao do embarque: {e}',
            }, ensure_ascii=False, indent=2))
            return EXIT_FALHA

        resultado['modo_execucao'] = 'EFETIVADO'
        print(json.dumps(resultado, default=decimal_default, ensure_ascii=False, indent=2))
        return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
