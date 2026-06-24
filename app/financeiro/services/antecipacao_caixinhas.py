# -*- coding: utf-8 -*-
"""
Modelo de "caixinhas" para baixa de ANTECIPACAO (ex: Sendas/Assai).
=====================================================================

Logica PURA e deterministica, SEM dependencia de Odoo (testavel isoladamente).

A baixa de uma antecipacao decompoe o valor de FACE da NF em 3 caixinhas invariantes:

    face  = account.move.l10n_br_total_nfe        (NF sem abatimentos)
    desconto = face * taxa_desconto               (res.partner.x_studio_desconto)
    titulo   = face - desconto                    (== account.move.amount_total)
    liquido  = titulo - encargos                  (entra no banco, journal Sicoob)

    INVARIANTE: liquido + encargos + desconto == face

As caixinhas sao o ESTADO-ALVO: o tamanho de cada uma e' determinado pela face e pela
taxa do cliente, independente de como o desconto esteja representado no Odoo
(aplicado/embutido, linha-fantasma ano-2000, ou nao aplicado). So as OPERACOES de baixa
variam conforme o estado atual do titulo no Odoo (ver reconciliador no service).

Spec: docs/superpowers/specs/2026-06-24-baixa-antecipacao-caixinhas-design.md
"""
from dataclasses import dataclass

# Tolerancia (R$) de centavos (arredondamento) na invariante e nas comparacoes de saldo.
TOL_CAIXINHAS = 0.05


@dataclass(frozen=True)
class Caixinhas:
    """Estado-alvo deterministico de uma baixa de antecipacao (valores em R$)."""
    face: float       # l10n_br_total_nfe (NF sem abatimentos)
    desconto: float   # face * taxa_desconto (desconto concedido contratual)
    titulo: float     # face - desconto (== amount_total do titulo a receber)
    encargos: float   # Vlr.encargos da planilha (input manual; depende do prazo)
    liquido: float    # titulo - encargos (valor que entra no banco)


def calcular_caixinhas(face, taxa_desconto, encargos, tol: float = TOL_CAIXINHAS) -> Caixinhas:
    """
    Dimensiona as caixinhas a partir da fonte de verdade e valida a invariante.

    Args:
        face:          valor da NF sem abatimentos (account.move.l10n_br_total_nfe).
        taxa_desconto: FRACAO do desconto contratual (ex: 0.005 = 0,5%).
                       Vem de res.partner.x_studio_desconto / 100.
        encargos:      Vlr.encargos da planilha (>= 0). Input manual.
        tol:           tolerancia em R$ para a invariante (default TOL_CAIXINHAS).

    Returns:
        Caixinhas com face/desconto/titulo/encargos/liquido.

    Raises:
        ValueError: face <= 0, taxa fora de [0,1), encargos < 0, liquido negativo,
                    ou invariante (soma != face) violada alem da tolerancia.
    """
    face = round(float(face or 0), 2)
    taxa_desconto = float(taxa_desconto or 0)
    encargos = round(float(encargos or 0), 2)

    if face <= 0:
        raise ValueError(f"Face invalida ({face:.2f}) — nao da para dimensionar as caixinhas")
    if not (0 <= taxa_desconto < 1):
        raise ValueError(f"Taxa de desconto fora de [0,1): {taxa_desconto}")
    if encargos < 0:
        raise ValueError(f"Encargos negativo: {encargos:.2f}")

    desconto = round(face * taxa_desconto, 2)
    titulo = round(face - desconto, 2)
    liquido = round(titulo - encargos, 2)

    if liquido < -tol:
        raise ValueError(
            f"Encargos ({encargos:.2f}) maior que o titulo ({titulo:.2f}) — liquido negativo"
        )

    soma = round(liquido + encargos + desconto, 2)
    if abs(soma - face) > tol:
        raise ValueError(
            f"Invariante violada: liquido+encargos+desconto ({soma:.2f}) != face ({face:.2f})"
        )

    return Caixinhas(
        face=face, desconto=desconto, titulo=titulo, encargos=encargos, liquido=liquido
    )


# =============================================================================
# CLASSIFICACAO DETERMINISTICA DO ESTADO DO TITULO NO ODOO
# =============================================================================
# O desconto contratual e' UMA entidade; "ano-2000" e "embutido" sao 2 momentos
# dela. O reconciliador (no service) usa este estado para decidir as OPERACOES;
# as caixinhas-alvo sao as mesmas em qualquer estado.

ESTADO_EMBUTIDO = 'EMBUTIDO'            # desconto ja abatido: saldo == titulo (face - desconto)
ESTADO_ANO_2000 = 'ANO_2000'           # desconto como linha-fantasma date_maturity=2000-01-01
ESTADO_NADA_APLICADO = 'NADA_APLICADO'  # desconto nao abatido: saldo == face cheia


def classificar_estado(caixinhas: Caixinhas, amount_residual, tem_linha_2000: bool,
                       tol: float = TOL_CAIXINHAS) -> str:
    """
    Classifica deterministicamente o estado do titulo no Odoo quanto ao desconto.

    Args:
        caixinhas:       Caixinhas (alvo) ja calculadas (fonte: face + taxa do cliente).
        amount_residual: saldo atual do titulo a receber no Odoo (>= 0).
        tem_linha_2000:  True se ha account.move.line receivable com date_maturity='2000-01-01'.
        tol:             tolerancia em R$ nas comparacoes de saldo.

    Returns:
        ESTADO_ANO_2000 | ESTADO_EMBUTIDO | ESTADO_NADA_APLICADO

    Raises:
        ValueError: se o saldo nao casa nenhum estado conhecido (NAO adivinhar).

    Nota: com desconto == 0 (taxa 0), titulo == face e o estado e' EMBUTIDO (nada a
    fazer com desconto) — comportamento correto.
    """
    if tem_linha_2000:
        return ESTADO_ANO_2000

    residual = round(float(amount_residual or 0), 2)
    if abs(residual - caixinhas.titulo) <= tol:
        return ESTADO_EMBUTIDO
    if abs(residual - caixinhas.face) <= tol:
        return ESTADO_NADA_APLICADO

    raise ValueError(
        f"Saldo do titulo ({residual:.2f}) nao casa nem titulo ({caixinhas.titulo:.2f}) "
        f"nem face ({caixinhas.face:.2f}) — estado indeterminado, requer revisao manual"
    )
