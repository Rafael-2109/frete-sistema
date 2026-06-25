"""
Núcleo de cálculo PURO do Relatório Semanal de Estoque.

NÃO importa banco/app context/rede (apenas regras determinísticas), no mesmo
espírito de `relatorios_semanais_calc.py`. A orquestração (queries/Excel/e-mail)
vive em `estoque_semanal_service.py`.

Régua de datas (saldo de abertura):
  estoque0     = saldo até < seg_anterior
  estoque_hoje = saldo até < seg_atual
  período      = seg_anterior <= data < seg_atual
Garante por construção: estoque0 + entradas - consumos + outros == estoque_hoje.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Tuple

from app.manufatura.services.relatorios_semanais_calc import (
    classificar_aba,
    colapsar_por_unificacao,
)

# Sentido das colunas "Entradas"/"Consumos" por grupo.
_GRUPOS_COMPONENTE = ("INSUMOS", "EMBALAGENS")
_TIPOS_PRODUCAO = ("PRODUÇÃO", "PRODUCAO")  # gravado com acento; aceita ambos

# Aba de destino por classificação (MP_EXCLUIDO é descartado).
_ABA_POR_GRUPO = {
    "INSUMOS": "Insumos",
    "EMBALAGENS": "Embalagens",
    "PRODUTO_ACABADO": "Produto_Acabado",
    "OUTROS": "Outros",
}


def semanas_referencia(hoje: date) -> Tuple[date, date]:
    """(seg_anterior, seg_atual). Normaliza `hoje` para a segunda da semana."""
    seg_atual = hoje - timedelta(days=hoje.weekday())  # weekday(): seg=0
    seg_anterior = seg_atual - timedelta(days=7)
    return seg_anterior, seg_atual


def classificar_movimento(grupo: str, tipo_mov: str, local_mov: str) -> str:
    """'ENTRADA' | 'CONSUMO' | 'OUTRO' conforme o sentido do grupo."""
    t = (tipo_mov or "").strip().upper()
    l = (local_mov or "").strip().upper()
    if grupo in _GRUPOS_COMPONENTE:
        if t == "ENTRADA" and l == "COMPRA":
            return "ENTRADA"
        if t == "CONSUMO":
            return "CONSUMO"
        return "OUTRO"
    if grupo == "PRODUTO_ACABADO":
        if t in _TIPOS_PRODUCAO:
            return "ENTRADA"
        if l == "VENDA" and t in ("FATURAMENTO", "SAIDA"):
            return "CONSUMO"
        return "OUTRO"
    return "OUTRO"


def _round(v: float) -> float:
    return round(float(v) if v is not None else 0.0, 3)


def montar_abas(
    estoque0: Dict[str, float],
    estoque_hoje: Dict[str, float],
    movimentos: List[Tuple[str, str, str, float]],
    cadastro: Dict[str, Dict[str, str]],
    mapa_unif: Dict[str, str],
) -> Dict[str, List[Dict[str, Any]]]:
    """Monta as abas do relatório semanal a partir de dados já agregados."""
    estoque0 = colapsar_por_unificacao(estoque0, mapa_unif)
    estoque_hoje = colapsar_por_unificacao(estoque_hoje, mapa_unif)

    # entradas/consumos exibidos positivos, por código canônico
    entradas: Dict[str, float] = {}
    consumos: Dict[str, float] = {}
    for cod, tipo_mov, local_mov, qtd in movimentos:
        canon = mapa_unif.get(str(cod), str(cod))
        cad = cadastro.get(canon, {})
        grupo = classificar_aba(canon, cad.get("tipo_materia_prima"), contexto="rel2")
        classe = classificar_movimento(grupo, tipo_mov, local_mov)
        if classe == "ENTRADA":
            entradas[canon] = entradas.get(canon, 0.0) + float(qtd)
        elif classe == "CONSUMO":
            consumos[canon] = consumos.get(canon, 0.0) - float(qtd)  # qtd é negativo -> positivo

    universo = set(estoque0) | set(estoque_hoje) | set(entradas) | set(consumos)
    abas: Dict[str, List[Dict[str, Any]]] = {
        "Insumos": [], "Embalagens": [], "Produto_Acabado": [], "Outros": []
    }
    for cod in sorted(universo):
        e0 = float(estoque0.get(cod, 0.0))
        e1 = float(estoque_hoje.get(cod, 0.0))
        ent = float(entradas.get(cod, 0.0))
        con = float(consumos.get(cod, 0.0))
        if e0 == 0 and e1 == 0 and ent == 0 and con == 0:
            continue  # zerado e sem movimento: não polui
        cad = cadastro.get(cod, {})
        grupo = classificar_aba(cod, cad.get("tipo_materia_prima"), contexto="rel2")
        if grupo == "MP_EXCLUIDO":
            continue
        destino = _ABA_POR_GRUPO.get(grupo, "Outros")
        outros = (e1 - e0) - ent + con  # fecha a conta por construção
        abas[destino].append({
            "cod_produto": cod,
            "nome_produto": cad.get("nome_produto", ""),
            "categoria": cad.get("categoria", ""),
            "estoque_seg_anterior": _round(e0),
            "entradas": _round(ent),
            "consumos": _round(con),
            "outros_ajustes": _round(outros),
            "estoque_seg_atual": _round(e1),
        })
    return abas
