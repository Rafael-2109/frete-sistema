"""
Servico de aprendizado — cria regras a partir de categorizacoes manuais.

Quando usuario categoriza manualmente uma transacao:
1. Normaliza historico
2. Busca regra existente (fuzzy >= 90)
3. Se nao existe: cria regra nova (origem='aprendido', confianca=80)
4. Se existe: incrementa vezes_usado e ajusta confianca
5. Se mesmo padrao -> 3+ categorias distintas: muda tipo_regra='RELATIVO'

Propagacao:
- propagar_para_pendentes(): re-roda pipeline em PENDENTES
- despropagar_regra(): reseta auto-categorizadas por uma regra
"""
import logging
from typing import Optional
from rapidfuzz import fuzz
from unidecode import unidecode
import re

from app import db
from app.pessoal.models import (
    PessoalTransacao, PessoalCategoria, PessoalRegraCategorizacao,
)
from app.pessoal.services.categorizacao_service import categorizar_transacao
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def _mesmo_escopo_regra(regra: 'PessoalRegraCategorizacao',
                         cpf_cnpj_norm, valor_min, valor_max) -> bool:
    """Retorna True se a regra tem o mesmo escopo (cpf_cnpj + range de valor).

    Regras com mesmo padrao textual mas escopos diferentes sao consideradas
    distintas (ex: ">=100" vs "<100"), permitindo coexistencia.
    None == None; senao compara valor numerico.
    """
    def _num(v):
        return float(v) if v is not None else None

    regra_cpf = regra.cpf_cnpj_padrao or None
    novo_cpf = cpf_cnpj_norm or None
    if regra_cpf != novo_cpf:
        return False
    if _num(regra.valor_min) != _num(valor_min):
        return False
    if _num(regra.valor_max) != _num(valor_max):
        return False
    return True


def aprender_de_categorizacao(transacao_id: int, categoria_id: int,
                               membro_id: int = None,
                               tipo_regra: str = 'PADRAO',
                               padrao_historico: str = None,
                               cpf_cnpj_padrao: str = None,
                               valor_min=None,
                               valor_max=None) -> Optional[PessoalRegraCategorizacao]:
    """Aprende uma nova regra a partir de categorizacao manual.

    Args:
        tipo_regra: 'PADRAO' (aplica categoria automaticamente) ou
                    'RELATIVO' (sugere, nao aplica). Se RELATIVO, regra
                    criada com categoria_id=None e categoria nas restritas.
        padrao_historico: padrao editado pelo usuario (ex: sem datas).
                         Se None, auto-gera do historico da transacao.
        cpf_cnpj_padrao (F1): CPF/CNPJ como chave alternativa de match.
                              Se None e a transacao tem cpf_cnpj_parte, usa esse.
        valor_min / valor_max (F4): range opcional de valor para a regra.

    Returns: regra criada ou atualizada, ou None se nao aplicavel.
    """
    transacao = db.session.get(PessoalTransacao, transacao_id)
    if not transacao:
        return None

    categoria = db.session.get(PessoalCategoria, categoria_id)
    if not categoria:
        return None

    # F1: normalizar CPF/CNPJ enviado, fallback para o extraido da transacao
    cpf_cnpj_norm = None
    if cpf_cnpj_padrao:
        cpf_cnpj_norm = ''.join(ch for ch in cpf_cnpj_padrao if ch.isdigit()) or None

    # 1. Normalizar historico — usa padrao editado se fornecido
    #    Senao, usa historico_completo (historico + descricao normalizado)
    #    para capturar contexto completo (ex: "TRANSF PIX | JOAO SILVA")
    if padrao_historico and padrao_historico.strip():
        historico_norm = _normalizar(padrao_historico)
    else:
        historico_norm = _normalizar(
            transacao.historico_completo or transacao.historico or ''
        )
    # Regra precisa de pelo menos um criterio: padrao textual OU CPF/CNPJ
    if (not historico_norm or len(historico_norm) < 3) and not cpf_cnpj_norm:
        return None
    if not historico_norm:
        historico_norm = cpf_cnpj_norm  # fallback — CPF/CNPJ tambem e texto

    # 2. Buscar regra existente (fuzzy >= 90) — MESMO ESCOPO
    # Regras com mesmo padrao mas cpf_cnpj ou range de valor diferentes
    # sao tratadas como regras DISTINTAS (ex: ">=100=X" + "<100=Y" coexistem).
    regras = PessoalRegraCategorizacao.query.filter_by(ativo=True).all()
    melhor_regra = None
    melhor_score = 0

    for regra in regras:
        padrao_norm = _normalizar(regra.padrao_historico)
        if not padrao_norm:
            continue
        score = fuzz.token_set_ratio(padrao_norm, historico_norm)
        if score < 90:
            continue
        if not _mesmo_escopo_regra(regra, cpf_cnpj_norm, valor_min, valor_max):
            continue
        if score > melhor_score:
            melhor_score = score
            melhor_regra = regra

    if melhor_regra:
        # 4. Regra existente: incrementar uso
        melhor_regra.vezes_usado = (melhor_regra.vezes_usado or 0) + 1

        # 4b. Se usuario editou o padrao, atualizar a regra
        #     (padrao_historico explicitamente fornecido e diferente do existente)
        if padrao_historico and padrao_historico.strip():
            padrao_existente = _normalizar(melhor_regra.padrao_historico or '')
            if historico_norm != padrao_existente:
                melhor_regra.padrao_historico = historico_norm

        # F1/F4: cpf_cnpj/valor ja batem (filtrados em _mesmo_escopo_regra).
        # Nao sobrescrever — regras de escopo diferente seguem caminho "nova".

        # 5. Verificar se mesmo padrao aponta para multiplas categorias
        if melhor_regra.categoria_id and melhor_regra.categoria_id != categoria_id:
            # Potencial RELATIVO — contar categorias distintas
            categorias_usadas = _contar_categorias_distintas(melhor_regra, categoria_id)
            if len(categorias_usadas) >= 3:
                melhor_regra.tipo_regra = 'RELATIVO'
                melhor_regra.set_categorias_restritas(list(categorias_usadas))
                melhor_regra.categoria_id = None

        # Ajustar confianca para cima (max 99)
        if melhor_regra.confianca and float(melhor_regra.confianca) < 99:
            melhor_regra.confianca = min(99, float(melhor_regra.confianca) + 1)

        melhor_regra.atualizado_em = agora_utc_naive()
        db.session.flush()
        return melhor_regra

    # 3. Nao existe: criar nova regra
    if tipo_regra == 'RELATIVO':
        nova_regra = PessoalRegraCategorizacao(
            padrao_historico=historico_norm,
            tipo_regra='RELATIVO',
            categoria_id=None,
            membro_id=membro_id,
            cpf_cnpj_padrao=cpf_cnpj_norm,
            valor_min=valor_min,
            valor_max=valor_max,
            vezes_usado=1,
            confianca=80,
            origem='aprendido',
        )
        nova_regra.set_categorias_restritas([categoria_id])
    else:
        nova_regra = PessoalRegraCategorizacao(
            padrao_historico=historico_norm,
            tipo_regra='PADRAO',
            categoria_id=categoria_id,
            membro_id=membro_id,
            cpf_cnpj_padrao=cpf_cnpj_norm,
            valor_min=valor_min,
            valor_max=valor_max,
            vezes_usado=1,
            confianca=80,
            origem='aprendido',
        )
    db.session.add(nova_regra)
    db.session.flush()
    return nova_regra


def _contar_categorias_distintas(regra: PessoalRegraCategorizacao,
                                  nova_categoria_id: int) -> set:
    """Conta categorias distintas associadas a um padrao de regra."""
    cat_ids = set()

    # Categoria atual da regra
    if regra.categoria_id:
        cat_ids.add(regra.categoria_id)

    # Categorias restritas existentes
    restritas = regra.get_categorias_restritas()
    cat_ids.update(restritas)

    # Nova categoria
    cat_ids.add(nova_categoria_id)

    return cat_ids


def propagar_para_pendentes() -> dict:
    """Re-roda pipeline de categorizacao em todas as transacoes PENDENTES.

    Busca transacoes com status='PENDENTE' e excluir_relatorio=False,
    aplica categorizar_transacao() e atualiza apenas as que mudaram
    para CATEGORIZADO.

    Returns: {'propagados': N, 'total_pendentes': M}
    """
    pendentes = PessoalTransacao.query.filter_by(
        status='PENDENTE',
        excluir_relatorio=False,
    ).all()

    total_pendentes = len(pendentes)
    propagados = 0

    for transacao in pendentes:
        resultado = categorizar_transacao(transacao)

        if resultado.status == 'CATEGORIZADO' and resultado.categoria_id:
            transacao.categoria_id = resultado.categoria_id
            transacao.regra_id = resultado.regra_id
            transacao.categorizacao_auto = True
            transacao.categorizacao_confianca = resultado.categorizacao_confianca
            transacao.excluir_relatorio = resultado.excluir_relatorio
            transacao.eh_pagamento_cartao = resultado.eh_pagamento_cartao
            transacao.eh_transferencia_propria = resultado.eh_transferencia_propria
            transacao.status = 'CATEGORIZADO'
            transacao.categorizado_em = agora_utc_naive()
            transacao.categorizado_por = 'sistema (propagacao)'
            propagados += 1

    logger.info(
        'Propagacao concluida: %d/%d pendentes categorizadas',
        propagados, total_pendentes,
    )
    return {'propagados': propagados, 'total_pendentes': total_pendentes}


def propagar_regra_para_pendentes(regra: PessoalRegraCategorizacao,
                                   padrao_override: str = None) -> dict:
    """Propaga UMA regra PADRAO para transacoes PENDENTES.

    Match usa tres criterios (qualquer um serve):
    - F1: cpf_cnpj_padrao == transacao.cpf_cnpj_parte
    - Substring: padrao_norm in historico normalizado
    - F4: range valor_min/valor_max e aplicado como filtro em ambos

    Muito mais rapido que propagar_para_pendentes() porque:
    - 2 queries (pendentes + exclusoes) vs 3*N do pipeline completo
    - Match em memoria pura, sem queries por transacao

    Args:
        regra: regra PADRAO ativa a propagar.
        padrao_override: padrao editado pelo usuario (usa no lugar de regra.padrao_historico).

    Returns: {'propagados': N, 'total_pendentes': M}
    """
    from app.pessoal.services.categorizacao_service import _valor_no_range

    if not regra or regra.tipo_regra != 'PADRAO' or not regra.ativo:
        return {'propagados': 0, 'total_pendentes': 0}

    padrao_norm = _normalizar(padrao_override or regra.padrao_historico or '')
    cpf_cnpj_regra = regra.cpf_cnpj_padrao

    # Regra precisa ter pelo menos um criterio de match
    if not padrao_norm and not cpf_cnpj_regra:
        return {'propagados': 0, 'total_pendentes': 0}

    pendentes = PessoalTransacao.query.filter_by(
        status='PENDENTE',
        excluir_relatorio=False,
    ).all()

    # NOTA: exclusoes empresariais agora sao regras PADRAO -> categoria Desconsiderar.
    # Transacoes com padrao de exclusao ja estao com status CATEGORIZADO, nao em pendentes.

    total_pendentes = len(pendentes)
    propagados = 0

    for transacao in pendentes:
        historico = _normalizar(
            transacao.historico_completo or transacao.historico or ''
        )

        # F4: filtro de valor
        if not _valor_no_range(transacao.valor, regra.valor_min, regra.valor_max):
            continue

        # Match por CPF/CNPJ (F1) ou substring
        match = False
        if cpf_cnpj_regra and transacao.cpf_cnpj_parte == cpf_cnpj_regra:
            match = True
        elif padrao_norm and padrao_norm in historico:
            match = True

        if match:
            from app.pessoal.services.categorizacao_service import eh_categoria_desconsiderar
            transacao.categoria_id = regra.categoria_id
            transacao.regra_id = regra.id
            transacao.categorizacao_auto = True
            transacao.categorizacao_confianca = 100.0
            transacao.status = 'CATEGORIZADO'
            transacao.categorizado_em = agora_utc_naive()
            transacao.categorizado_por = 'sistema (propagacao)'
            transacao.excluir_relatorio = eh_categoria_desconsiderar(regra.categoria_id)
            regra.vezes_usado = (regra.vezes_usado or 0) + 1
            propagados += 1

    logger.info(
        'Propagacao regra_id=%d ("%s"): %d/%d pendentes categorizadas',
        regra.id, regra.padrao_historico, propagados, total_pendentes,
    )
    return {'propagados': propagados, 'total_pendentes': total_pendentes}


def propagar_parcelas(transacao: PessoalTransacao) -> int:
    """F2: Aplica categoria da transacao em todas as outras parcelas ja importadas.

    Usa `identificador_parcela` para achar compras parceladas (mesma compra,
    parcelas 1/12, 2/12... no mesmo cartao/conta).

    Returns: quantidade de parcelas atualizadas (nao inclui a transacao original).
    """
    if (not transacao.identificador_parcela or not transacao.categoria_id
            or not transacao.conta_id):
        return 0

    irmas = PessoalTransacao.query.filter(
        PessoalTransacao.identificador_parcela == transacao.identificador_parcela,
        PessoalTransacao.conta_id == transacao.conta_id,
        PessoalTransacao.id != transacao.id,
        PessoalTransacao.excluir_relatorio.is_(False),
    ).all()

    from app.pessoal.services.categorizacao_service import eh_categoria_desconsiderar
    desconsiderar = eh_categoria_desconsiderar(transacao.categoria_id)

    count = 0
    for irma in irmas:
        # Nao sobrescrever categorizacao manual divergente
        if (irma.categoria_id and not irma.categorizacao_auto
                and irma.categoria_id != transacao.categoria_id):
            continue
        irma.categoria_id = transacao.categoria_id
        irma.regra_id = transacao.regra_id
        irma.categorizacao_auto = True
        irma.categorizacao_confianca = 100.0
        irma.status = 'CATEGORIZADO'
        irma.categorizado_em = agora_utc_naive()
        irma.categorizado_por = 'sistema (parcela)'
        irma.excluir_relatorio = desconsiderar
        if transacao.membro_id and not irma.membro_id:
            irma.membro_id = transacao.membro_id
            irma.membro_auto = True
        count += 1

    if count > 0:
        logger.info(
            'Propagacao parcela id_parcela="%s": %d parcelas atualizadas',
            transacao.identificador_parcela, count,
        )
    return count


def contar_matches_por_regra(regras: list[PessoalRegraCategorizacao]) -> dict[int, int]:
    """Conta quantas transacoes PENDENTES cada regra PADRAO matcharia.

    Carrega pendentes uma vez, normaliza, e faz substring match por regra.
    O(R * P) em memoria — rapido para centenas de regras/transacoes.

    Returns: {regra_id: count_pendentes_que_matcham}
    """
    pendentes = PessoalTransacao.query.filter_by(
        status='PENDENTE',
        excluir_relatorio=False,
    ).all()

    # Pre-normalizar historicos uma vez
    pendentes_norm = []
    for t in pendentes:
        pendentes_norm.append(
            _normalizar(t.historico_completo or t.historico or '')
        )

    contagem = {}
    for regra in regras:
        if regra.tipo_regra == 'PADRAO' and regra.ativo:
            padrao_norm = _normalizar(regra.padrao_historico or '')
            if padrao_norm:
                contagem[regra.id] = sum(
                    1 for h in pendentes_norm if padrao_norm in h
                )
            else:
                contagem[regra.id] = 0
        else:
            contagem[regra.id] = 0

    return contagem


def despropagar_regra(regra_id: int) -> int:
    """Reseta transacoes auto-categorizadas por uma regra especifica.

    Transacoes com regra_id=X e categorizacao_auto=True voltam para PENDENTE.

    Returns: quantidade de transacoes afetadas.
    """
    afetadas = PessoalTransacao.query.filter_by(
        regra_id=regra_id,
        categorizacao_auto=True,
    ).all()

    count = len(afetadas)
    for transacao in afetadas:
        transacao.categoria_id = None
        transacao.regra_id = None
        transacao.categorizacao_auto = False
        transacao.categorizacao_confianca = None
        transacao.status = 'PENDENTE'
        transacao.categorizado_em = None
        transacao.categorizado_por = None
        # Sair de categoria Desconsiderar => volta ao relatorio
        transacao.excluir_relatorio = False

    if count > 0:
        logger.info(
            'Despropagacao regra_id=%d: %d transacoes resetadas para PENDENTE',
            regra_id, count,
        )
    return count


def desvincular_manuais_da_regra(regra_id: int) -> int:
    """Zera regra_id em transacoes MANUAIS (auto=False) que apontam para esta regra.

    Usado ao editar uma regra cuja categoria mudou: a decisao manual do usuario
    e PRESERVADA (categoria_id nao e alterada), mas remove-se a referencia a regra
    antiga para evitar inconsistencia (regra aponta para cat X, transacao para cat Y).

    NAO altera categoria_id, status, nem categorizacao_auto.

    Returns: quantidade de transacoes desvinculadas.
    """
    afetadas = PessoalTransacao.query.filter(
        PessoalTransacao.regra_id == regra_id,
        PessoalTransacao.categorizacao_auto.is_(False),
    ).update({'regra_id': None}, synchronize_session=False)
    if afetadas:
        logger.info(
            'Desvinculacao de manuais (regra_id=%d): %d transacoes com regra_id=NULL',
            regra_id, afetadas,
        )
    return int(afetadas or 0)


def propagar_regra_forcado(regra: PessoalRegraCategorizacao) -> dict:
    """Propagacao forcada — aplica a regra em TODAS as transacoes compativeis.

    Para a regra dada (tipo PADRAO, ativo=True):
    1. Re-atribui a categoria em transacoes que JA estao vinculadas a esta regra
       (regra_id = <esta>) — cobre auto E manuais que apontam para esta regra.
    2. Propaga para transacoes PENDENTES que matcham o padrao (mesma logica de
       `propagar_regra_para_pendentes`).

    PROTEGE regras top-level: NAO sobrescreve transacoes que pertencem a OUTRA
    regra (regra_id != esta) — elas permanecem intactas, mesmo que o padrao
    desta regra tambem matche (ex: regra com CPF/CNPJ mais especifica).
    NAO sobrescreve transacoes CATEGORIZADAS manualmente sem regra_id
    (decisao top-level do usuario) — sao preservadas.

    Returns:
        dict com {reatribuidas_vinculadas, propagados_pendentes, total_pendentes,
                  protegidas_outras_regras, protegidas_manuais_sem_regra}
    """
    from app.pessoal.services.categorizacao_service import eh_categoria_desconsiderar

    if regra.tipo_regra != 'PADRAO' or not regra.ativo:
        return {
            'reatribuidas_vinculadas': 0,
            'propagados_pendentes': 0,
            'total_pendentes': 0,
            'protegidas_outras_regras': 0,
            'protegidas_manuais_sem_regra': 0,
        }

    # 1. Re-atribuir categoria nas transacoes vinculadas a esta regra
    vinculadas = PessoalTransacao.query.filter_by(regra_id=regra.id).all()
    reatribuidas = 0
    excluir = eh_categoria_desconsiderar(regra.categoria_id)
    for t in vinculadas:
        mudou = False
        if t.categoria_id != regra.categoria_id:
            t.categoria_id = regra.categoria_id
            mudou = True
        if t.excluir_relatorio != excluir:
            t.excluir_relatorio = excluir
            mudou = True
        # Se esta com status PENDENTE mas tem regra_id, promove a CATEGORIZADO
        if regra.categoria_id and t.status == 'PENDENTE':
            t.status = 'CATEGORIZADO'
            if t.categorizado_em is None:
                t.categorizado_em = agora_utc_naive()
            if not t.categorizado_por:
                t.categorizado_por = 'sistema (propagacao forcada)'
            mudou = True
        if mudou:
            reatribuidas += 1
    db.session.flush()

    # 2. Protegidas: contar transacoes com OUTRA regra que matcham o padrao (so informativo)
    padrao_norm = _normalizar(regra.padrao_historico or '')
    protegidas_outras = 0
    protegidas_manuais = 0
    if padrao_norm:
        # Transacoes com regra_id != esta
        candidatas_outra_regra = PessoalTransacao.query.filter(
            PessoalTransacao.regra_id.isnot(None),
            PessoalTransacao.regra_id != regra.id,
        ).all()
        for t in candidatas_outra_regra:
            hist = _normalizar(t.historico_completo or t.historico or '')
            if padrao_norm in hist:
                protegidas_outras += 1

        # Transacoes categorizadas manualmente SEM regra (regra_id=NULL, auto=False, CATEGORIZADO)
        candidatas_manuais = PessoalTransacao.query.filter(
            PessoalTransacao.regra_id.is_(None),
            PessoalTransacao.categorizacao_auto.is_(False),
            PessoalTransacao.status == 'CATEGORIZADO',
            PessoalTransacao.categoria_id.isnot(None),
        ).all()
        for t in candidatas_manuais:
            hist = _normalizar(t.historico_completo or t.historico or '')
            if padrao_norm in hist:
                protegidas_manuais += 1

    # 3. Propagar para pendentes (reusa logica existente — SEM commit proprio)
    resultado_pendentes = propagar_regra_para_pendentes(regra)

    logger.info(
        'Propagacao forcada regra_id=%d: %d reatribuidas, %d pendentes propagadas, '
        '%d protegidas (outra regra), %d protegidas (manuais sem regra)',
        regra.id, reatribuidas, resultado_pendentes['propagados'],
        protegidas_outras, protegidas_manuais,
    )

    return {
        'reatribuidas_vinculadas': reatribuidas,
        'propagados_pendentes': resultado_pendentes['propagados'],
        'total_pendentes': resultado_pendentes['total_pendentes'],
        'protegidas_outras_regras': protegidas_outras,
        'protegidas_manuais_sem_regra': protegidas_manuais,
    }


def simular_propagacao(padrao_historico: str = None,
                       cpf_cnpj_padrao: str = None,
                       valor_min=None,
                       valor_max=None) -> list[dict]:
    """Simula propagacao — retorna transacoes PENDENTES que seriam afetadas.

    Quando padrao_historico ou cpf_cnpj_padrao fornecido: replica a logica de
    `propagar_regra_para_pendentes` (match substring OU CPF/CNPJ, filtro por
    range de valor, exclusao Layer 0) para preview fiel da regra nova/editada.

    Quando nenhum fornecido: roda pipeline completo de categorizacao em
    PENDENTES (comportamento original).

    Returns: lista de dicts com {id, data, historico, valor, tipo}
    """
    from app.pessoal.services.categorizacao_service import _valor_no_range

    pendentes = PessoalTransacao.query.filter_by(
        status='PENDENTE',
        excluir_relatorio=False,
    ).all()

    afetadas = []

    # Preview de regra nova/editada: ha pelo menos um criterio de match
    tem_match_criterio = bool(padrao_historico) or bool(cpf_cnpj_padrao)

    if tem_match_criterio:
        padrao_norm = _normalizar(padrao_historico or '')
        cpf_cnpj_norm = (cpf_cnpj_padrao or '').strip() or None

        if not padrao_norm and not cpf_cnpj_norm:
            return []

        # NOTA: exclusoes empresariais agora sao regras PADRAO -> categoria Desconsiderar.
        # Transacoes com padrao de exclusao ja estao com status CATEGORIZADO, nao em pendentes.

        for transacao in pendentes:
            historico = _normalizar(
                transacao.historico_completo or transacao.historico or ''
            )

            # F4: filtro de valor (range aberto nao restringe)
            if not _valor_no_range(transacao.valor, valor_min, valor_max):
                continue

            # Match por CPF/CNPJ (F1) OU substring de padrao
            match = False
            if cpf_cnpj_norm and transacao.cpf_cnpj_parte == cpf_cnpj_norm:
                match = True
            elif padrao_norm and padrao_norm in historico:
                match = True

            if match:
                afetadas.append({
                    'id': transacao.id,
                    'data': transacao.data.strftime('%d/%m/%Y') if transacao.data else '-',
                    'historico': (transacao.historico or '')[:60],
                    'descricao': (transacao.descricao or '')[:50],
                    'valor': float(transacao.valor) if transacao.valor else 0,
                    'tipo': transacao.tipo,
                })
    else:
        # Pipeline completo (comportamento original)
        for transacao in pendentes:
            resultado = categorizar_transacao(transacao)

            if resultado.status == 'CATEGORIZADO' and resultado.categoria_id:
                afetadas.append({
                    'id': transacao.id,
                    'data': transacao.data.strftime('%d/%m/%Y') if transacao.data else '-',
                    'historico': (transacao.historico or '')[:60],
                    'descricao': (transacao.descricao or '')[:50],
                    'valor': float(transacao.valor) if transacao.valor else 0,
                    'tipo': transacao.tipo,
                })

            # Reverter side effects: decrementar vezes_usado
            if resultado.regra_id:
                regra = db.session.get(PessoalRegraCategorizacao, resultado.regra_id)
                if regra and regra.vezes_usado and regra.vezes_usado > 0:
                    regra.vezes_usado = regra.vezes_usado - 1

    return afetadas


def normalizar_padrao(texto: str) -> str:
    """Normaliza texto de padrao para match. Funcao publica.

    Aplica: unidecode → upper → strip → collapse spaces.
    Identica a _normalizar, exposta para uso em configuracao.py.
    """
    return _normalizar(texto)


def _normalizar(texto: str) -> str:
    """Normaliza texto para comparacao."""
    if not texto:
        return ''
    texto = unidecode(texto).upper().strip()
    texto = re.sub(r'\s+', ' ', texto)
    return texto
