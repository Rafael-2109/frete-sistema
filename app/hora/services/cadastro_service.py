"""CRUD de cadastros: HoraLoja, HoraModelo, HoraTabelaPreco."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable, List, Optional

from app import db
from app.hora.models import HoraLoja, HoraModelo, HoraTabelaPreco


# ----------------------------- Loja -----------------------------

def criar_loja(
    cnpj: str,
    nome: Optional[str] = None,
    apelido: Optional[str] = None,
    endereco: Optional[str] = None,
    cidade: Optional[str] = None,
    uf: Optional[str] = None,
    dados_receita: Optional[dict] = None,
) -> HoraLoja:
    """Cria HoraLoja. Se `dados_receita` (output de receitaws_service.consultar_cnpj)
    for fornecido, autopreenche os campos fiscais e de endereço."""
    from app.utils.timezone import agora_utc_naive

    cnpj_norm = ''.join(c for c in cnpj if c.isdigit())
    if len(cnpj_norm) != 14:
        raise ValueError(f"CNPJ inválido (esperado 14 dígitos): {cnpj}")

    existente = HoraLoja.query.filter_by(cnpj=cnpj_norm).first()
    if existente:
        raise ValueError(f"Loja já cadastrada com CNPJ {cnpj_norm}")

    nome_final = (
        nome
        or (dados_receita.get('razao_social') if dados_receita else None)
        or apelido
        or f'CNPJ {cnpj_norm}'
    )

    loja = HoraLoja(
        cnpj=cnpj_norm,
        nome=nome_final,
        apelido=apelido,
        endereco=endereco,
        cidade=cidade,
        uf=uf.upper() if uf else None,
        ativa=True,
    )

    if dados_receita:
        loja.razao_social = dados_receita.get('razao_social')
        loja.nome_fantasia = dados_receita.get('nome_fantasia')
        loja.situacao_cadastral = dados_receita.get('situacao_cadastral')
        loja.data_abertura = dados_receita.get('data_abertura')
        loja.porte = dados_receita.get('porte')
        loja.natureza_juridica = dados_receita.get('natureza_juridica')
        loja.atividade_principal = dados_receita.get('atividade_principal')
        loja.logradouro = dados_receita.get('logradouro')
        loja.numero = dados_receita.get('numero')
        loja.complemento = dados_receita.get('complemento')
        loja.bairro = dados_receita.get('bairro')
        loja.cep = dados_receita.get('cep')
        # Sobrescreve cidade/uf se vieram da Receita e não foram passados manualmente
        loja.cidade = loja.cidade or dados_receita.get('cidade')
        loja.uf = loja.uf or dados_receita.get('uf')
        loja.telefone = dados_receita.get('telefone')
        loja.email = dados_receita.get('email')
        loja.receitaws_consultado_em = agora_utc_naive()

    db.session.add(loja)
    db.session.commit()
    return loja


def listar_lojas(
    apenas_ativas: bool = True,
    *,
    busca: Optional[str] = None,
    uf: Optional[str] = None,
) -> Iterable[HoraLoja]:
    """Lista lojas. Filtros opcionais:
    - busca: substring em nome, apelido, razao_social, nome_fantasia ou CNPJ
    - uf: UF exato (case-insensitive)
    """
    from sqlalchemy import or_

    query = HoraLoja.query.order_by(HoraLoja.nome)
    if apenas_ativas:
        query = query.filter_by(ativa=True)
    if busca:
        b = busca.strip()
        digits = ''.join(c for c in b if c.isdigit())
        cond = or_(
            HoraLoja.nome.ilike(f'%{b}%'),
            HoraLoja.apelido.ilike(f'%{b}%'),
            HoraLoja.razao_social.ilike(f'%{b}%'),
            HoraLoja.nome_fantasia.ilike(f'%{b}%'),
        )
        if digits:
            cond = or_(cond, HoraLoja.cnpj.ilike(f'%{digits}%'))
        query = query.filter(cond)
    if uf:
        query = query.filter(HoraLoja.uf == uf.strip().upper())
    return query.all()


def buscar_loja_por_cnpj(cnpj: str) -> Optional[HoraLoja]:
    cnpj_norm = ''.join(c for c in cnpj if c.isdigit())
    return HoraLoja.query.filter_by(cnpj=cnpj_norm).first()


# CNPJ que NAO deve aparecer na listagem de lojas para criar pedido de venda
# (regra de negocio fornecida pelo usuario em 2026-05-06).
CNPJ_EXCLUIDO_PEDIDO_VENDA = '62634044000120'


def listar_lojas_para_pedido_venda(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[HoraLoja]:
    """Lojas elegiveis para SELECT em criar pedido de venda.

    Regras:
    - Apenas ativas (`ativa=True`).
    - Respeita escopo do operador (`lojas_permitidas_ids`):
      None = sem restricao (admin/global); [] = nenhuma loja; [...] = filtra.
    - Exclui CNPJ `CNPJ_EXCLUIDO_PEDIDO_VENDA`.
    - Ordenadas por nome.
    """
    if lojas_permitidas_ids is not None and not lojas_permitidas_ids:
        return []
    query = HoraLoja.query.filter_by(ativa=True)
    if lojas_permitidas_ids is not None:
        query = query.filter(HoraLoja.id.in_(lojas_permitidas_ids))
    query = query.filter(HoraLoja.cnpj != CNPJ_EXCLUIDO_PEDIDO_VENDA)
    return query.order_by(HoraLoja.nome).all()


# ----------------------------- Modelo -----------------------------

def _normalizar_preco(valor) -> Optional[Decimal]:
    """Converte string/Decimal/None em Decimal positivo (ou None se vazio).

    Aceita formatos brasileiros ('1.234,56', '1234,56') e ingleses ('1234.56').
    Levanta ValueError se valor invalido (negativo ou nao numerico).
    """
    if valor is None or valor == '' or valor == 0:
        return None
    if isinstance(valor, Decimal):
        if valor < 0:
            raise ValueError(f'Preço nao pode ser negativo: {valor}')
        return valor if valor > 0 else None
    s = str(valor).strip()
    if not s:
        return None
    # Remove separador de milhar BR e troca virgula por ponto.
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        dec = Decimal(s)
    except Exception:
        raise ValueError(f'Preço invalido: {valor!r}')
    if dec < 0:
        raise ValueError(f'Preço nao pode ser negativo: {valor}')
    return dec if dec > 0 else None


def _normalizar_bool(valor, *, default: bool = True) -> bool:
    """Converte form-input em bool. Aceita: True/False (passa direto),
    "on"/"true"/"1"/"sim"/"yes" -> True, "off"/"false"/"0"/"nao"/"no"/""/None
    -> False. None aplica `default` (para retroatividade quando o caller
    nao informa o campo).
    """
    if valor is None:
        return default
    if isinstance(valor, bool):
        return valor
    s = str(valor).strip().lower()
    if not s:
        return False
    if s in ('on', 'true', '1', 'sim', 'yes', 's', 'y'):
        return True
    if s in ('off', 'false', '0', 'nao', 'não', 'no', 'n'):
        return False
    # Valor inesperado — default para evitar quebrar fluxos legados.
    return default


def criar_modelo(
    nome_modelo: str,
    potencia_motor: Optional[str] = None,
    descricao: Optional[str] = None,
    preco_a_vista=None,
    preco_a_prazo=None,
    autopropelido=True,
) -> HoraModelo:
    nome_norm = nome_modelo.strip()
    if not nome_norm:
        raise ValueError("nome_modelo obrigatório")

    existente = HoraModelo.query.filter_by(nome_modelo=nome_norm).first()
    if existente:
        raise ValueError(f"Modelo já cadastrado: {nome_norm}")

    modelo = HoraModelo(
        nome_modelo=nome_norm,
        potencia_motor=potencia_motor,
        descricao=descricao,
        preco_a_vista=_normalizar_preco(preco_a_vista),
        preco_a_prazo=_normalizar_preco(preco_a_prazo),
        autopropelido=_normalizar_bool(autopropelido, default=True),
        ativo=True,
    )
    db.session.add(modelo)
    db.session.commit()
    return modelo


def buscar_ou_criar_modelo(nome_modelo: str) -> HoraModelo:
    """DEPRECATED — preferir `modelo_resolver_service.resolver_ou_pendenciar`.

    Mantido como shim de compat: tenta resolver via aliases primeiro;
    se nao achar, cai no comportamento antigo (cria HoraModelo
    silenciosamente). NOVOS CALLSITES NAO devem usar essa funcao —
    usar resolver_ou_pendenciar para criar pendencia adequada.

    Existe apenas para callsites legados que ainda nao foram adaptados;
    sera removida apos migracao completa.
    """
    from app.hora.services.modelo_resolver_service import resolver_modelo

    nome_norm = (nome_modelo or '').strip()
    if not nome_norm:
        nome_norm = 'MODELO_DESCONHECIDO'

    # 1. Tenta resolver via aliases (caminho preferencial novo)
    modelo = resolver_modelo(nome_norm)
    if modelo:
        return modelo

    # 2. Fallback: comportamento antigo — cria HoraModelo silenciosamente.
    #    Mantido apenas para compat ate todos os callsites migrarem para
    #    resolver_ou_pendenciar. Loga para auditoria.
    import logging
    logging.getLogger(__name__).warning(
        'buscar_ou_criar_modelo criou modelo silenciosamente: %r. '
        'Migrar callsite para resolver_ou_pendenciar.',
        nome_norm,
    )
    modelo = HoraModelo(nome_modelo=nome_norm, ativo=True)
    db.session.add(modelo)
    db.session.flush()
    return modelo


def listar_modelos(
    apenas_ativos: bool = True,
    *,
    busca: Optional[str] = None,
    incluir_merged: bool = False,
) -> Iterable[HoraModelo]:
    """Lista modelos canonicos. Filtros opcionais:

    - busca: substring em nome_modelo, potencia_motor ou descricao
    - incluir_merged: se True, inclui modelos absorvidos (merged_em_id IS
      NOT NULL). Default False — listagens publicas mostram 1 modelo por
      produto fisico.
    """
    from sqlalchemy import or_

    query = HoraModelo.query.order_by(HoraModelo.nome_modelo)
    if apenas_ativos:
        query = query.filter_by(ativo=True)
    if not incluir_merged:
        query = query.filter(HoraModelo.merged_em_id.is_(None))
    if busca:
        b = busca.strip()
        query = query.filter(or_(
            HoraModelo.nome_modelo.ilike(f'%{b}%'),
            HoraModelo.potencia_motor.ilike(f'%{b}%'),
            HoraModelo.descricao.ilike(f'%{b}%'),
        ))
    return query.all()


def atualizar_modelo(
    modelo_id: int,
    nome_modelo: str,
    potencia_motor: Optional[str] = None,
    descricao: Optional[str] = None,
    preco_a_vista=None,
    preco_a_prazo=None,
    autopropelido=None,
) -> HoraModelo:
    """Atualiza atributos descritivos do modelo. Não altera `ativo` (use `toggle_ativo_modelo`).

    Preços (preco_a_vista, preco_a_prazo): aceitar None/'' grava NULL (limpa).
    Strings sao parseadas via _normalizar_preco (aceita formato BR ou ingles).

    autopropelido: aceita True/False, "on"/"true"/"1" -> True, "off"/"false"/"0"/""
    -> False, None preserva valor atual (retroatividade — caller nao mexeu).
    """
    modelo = HoraModelo.query.get(modelo_id)
    if modelo is None:
        raise ValueError(f"Modelo não encontrado: id={modelo_id}")

    nome_norm = (nome_modelo or '').strip()
    if not nome_norm:
        raise ValueError("nome_modelo obrigatório")

    if nome_norm != modelo.nome_modelo:
        duplicado = (
            HoraModelo.query
            .filter(HoraModelo.nome_modelo == nome_norm, HoraModelo.id != modelo_id)
            .first()
        )
        if duplicado is not None:
            raise ValueError(f"Já existe outro modelo com o nome: {nome_norm}")

    modelo.nome_modelo = nome_norm
    modelo.potencia_motor = (potencia_motor or '').strip() or None
    modelo.descricao = (descricao or '').strip() or None
    modelo.preco_a_vista = _normalizar_preco(preco_a_vista)
    modelo.preco_a_prazo = _normalizar_preco(preco_a_prazo)
    if autopropelido is not None:
        modelo.autopropelido = _normalizar_bool(autopropelido, default=modelo.autopropelido)
    db.session.commit()
    return modelo


def toggle_ativo_modelo(modelo_id: int) -> HoraModelo:
    """Alterna a flag `ativo` do modelo (inativação soft)."""
    modelo = HoraModelo.query.get(modelo_id)
    if modelo is None:
        raise ValueError(f"Modelo não encontrado: id={modelo_id}")
    modelo.ativo = not modelo.ativo
    db.session.commit()
    return modelo


# ----------------------------- Tabela de Preço -----------------------------

def criar_tabela_preco(
    modelo_id: int,
    preco_tabela: Decimal,
    vigencia_inicio: date,
    vigencia_fim: Optional[date] = None,
) -> HoraTabelaPreco:
    if preco_tabela <= 0:
        raise ValueError("preco_tabela deve ser > 0")

    tabela = HoraTabelaPreco(
        modelo_id=modelo_id,
        preco_tabela=Decimal(preco_tabela),
        vigencia_inicio=vigencia_inicio,
        vigencia_fim=vigencia_fim,
        ativo=True,
    )
    db.session.add(tabela)
    db.session.commit()
    return tabela


def buscar_preco_vigente(modelo_id: int, na_data: date) -> Optional[HoraTabelaPreco]:
    """Retorna a linha de preço vigente do modelo na data informada.

    Critério: ativo=True, vigencia_inicio <= na_data <= vigencia_fim (ou fim NULL).
    Se houver múltiplas, retorna a mais recente (maior vigencia_inicio).
    """
    from sqlalchemy import or_

    return (
        HoraTabelaPreco.query
        .filter(
            HoraTabelaPreco.modelo_id == modelo_id,
            HoraTabelaPreco.ativo.is_(True),
            HoraTabelaPreco.vigencia_inicio <= na_data,
            or_(
                HoraTabelaPreco.vigencia_fim.is_(None),
                HoraTabelaPreco.vigencia_fim >= na_data,
            ),
        )
        .order_by(HoraTabelaPreco.vigencia_inicio.desc())
        .first()
    )
