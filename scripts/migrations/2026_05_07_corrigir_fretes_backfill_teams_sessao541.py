"""
Data fix: Corrige 31 fretes backfill criados pelo Agente Web (Teams) em 07/05/2026.

Sessao: agent_sessions.id=541 (channel=teams, user_id=55, model=claude-opus-4-7)
Fretes afetados: carvia_fretes id 108-115 e 118-140 (gap 116/117 nao pertence a
sessao). 31 registros.

PROBLEMA DETECTADO:
  Todos os 31 fretes foram criados com:
  - tabela_nome_tabela = NULL
  - tabela_valor_kg, tabela_percentual_valor, tabela_frete_minimo_*,
    tabela_percentual_gris, tabela_pedagio_por_100kg, tabela_valor_despacho,
    tabela_icms_proprio, tabela_icms_incluso, etc. = NULL
  - valor_cotado preenchido como valor MANUAL direto, sem ancoragem em TabelaFrete

  Auditoria do agente confirma na ultima mensagem da sessao 541:
  "valores foram gravados como valor_cotado manual direto, sem ancoragem em
  tabela_frete. Isso significa que a CalculadoraFrete nao foi efetivamente
  aplicada — o backfill apenas inseriu valores."

CAUSA RAIZ:
  Agente chamou diretamente POST /carvia/fretes/backfill passando apenas
  `valor_cotado` no form, sem antes invocar /carvia/api/fretes/cotar-backfill
  (que retorna parametros completos da tabela). A rota POST so persiste os
  campos tabela_* que vierem no form (linhas 646-675 frete_routes.py),
  portanto todos ficaram NULL.

CORRECAO:
  Para cada frete:
    1. Determina peso_efetivo = max(peso_bruto, peso_cubado) das NFs vinculadas
       (peso_cubado calculado via MotoRecognitionService.calcular_peso_cubado_batch)
    2. Busca melhor tabela usando o mesmo fluxo de api_cotar_backfill:
       CotacaoService._obter_grupo_transportadora -> CidadeAtendida -> TabelaFrete
    3. Calcula via CalculadoraFrete.calcular_frete_unificado (cidade=None — CarVia
       usa apenas icms_proprio da tabela)
    4. Pega tabela com MENOR valor_com_icms
    5. Atualiza tabela_* + valor_cotado + valor_considerado + peso_total
    6. Adiciona nota nas observacoes com timestamp

VALORES MANUAIS PRESERVADOS (informados pelo usuario na sessao):
  Frete #111 Velocargas R$ 217,33 (NFs 1729+1730 PI — Velocargas sem tabela PI)
  Frete #137 Cazan      R$ 304,46 (NF 1859 BA, peso=0)
  Frete #138 Cazan      R$ 369,68 (NF 1680 AL — usuario informou divergente da tabela)
  Frete #127 Satisfacao R$    0,00 (NF 664 MG — sem tabela MG cadastrada)

  Para fretes 111, 137, 138: aplica tabela_* (referencia) mas mantem valor_cotado
  manual quando --preservar-manual. Frete 127 fica intocado (sem tabela).

USO:
  # Dry-run (default — nao modifica banco)
  source .venv/bin/activate && python scripts/migrations/2026_05_07_corrigir_fretes_backfill_teams_sessao541.py

  # Apenas dump JSON do que seria feito
  python scripts/migrations/2026_05_07_corrigir_fretes_backfill_teams_sessao541.py --json

  # Aplicar (PRESERVA valor_cotado manual nos 3 fretes informados)
  python scripts/migrations/2026_05_07_corrigir_fretes_backfill_teams_sessao541.py --apply --preservar-manual

  # Aplicar SOBRESCREVENDO TUDO (ignora valor manual usuario)
  python scripts/migrations/2026_05_07_corrigir_fretes_backfill_teams_sessao541.py --apply

  # Subset de fretes (para debug)
  python scripts/migrations/2026_05_07_corrigir_fretes_backfill_teams_sessao541.py --frete-ids 108,109,110

  # Rodar contra Render (banco prod):
  DATABASE_URL=<URL_RENDER> python ... --apply --preservar-manual

IDEMPOTENTE:
  Roda em qualquer frete cujo tabela_nome_tabela ja esteja preenchido sera PULADO
  com mensagem [SKIP-already-fixed]. Re-execucoes sao seguras.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402

# Fretes da sessao 541 (gap 116/117 NAO sao desta sessao)
FRETE_IDS_DEFAULT = list(range(108, 116)) + list(range(118, 141))

# Valores manuais informados pelo usuario na propria sessao
VALOR_MANUAL_USUARIO = {
    111: ("Velocargas NFs 1729+1730 — informado pelo usuario", 217.33),
    137: ("Cazan NF 1859 — informado pelo usuario (peso bruto NULL)", 304.46),
    138: ("Cazan NF 1680 — informado pelo usuario (diverge tabela)", 369.68),
}

# Frete #127: Satisfacao MG sem tabela. Deixa intocado.
FRETES_SEM_TABELA = {127: "Satisfacao em Logistica NF 664 MG — sem tabela cadastrada"}

NOTA_CORRECAO = (
    "[CORRECAO 2026-05-07 sessao 541] tabela_* preenchidos via "
    "CalculadoraFrete + CotacaoService."
)


def buscar_melhor_tabela(svc, transportadora_id, cidade_destino, uf_destino, peso, valor_mercadoria):
    """Espelha api_cotar_backfill: busca tabelas via grupo+cidade e retorna a melhor."""
    from app.tabelas.models import TabelaFrete
    from app.utils.calculadora_frete import CalculadoraFrete
    from app.utils.tabela_frete_manager import TabelaFreteManager

    grupo_ids = svc._obter_grupo_transportadora(int(transportadora_id))
    tabelas = []

    if cidade_destino:
        cidade_obj = svc._resolver_cidade(cidade_destino, uf_destino)
        if cidade_obj:
            vinculos = svc._buscar_vinculos_cidade(cidade_obj.codigo_ibge)
            for v in vinculos:
                if v.transportadora_id not in grupo_ids:
                    continue
                q = TabelaFrete.query.filter(
                    TabelaFrete.transportadora_id.in_(grupo_ids),
                    TabelaFrete.uf_destino == uf_destino,
                    TabelaFrete.nome_tabela == v.nome_tabela,
                )
                tabelas.extend(q.all())

    # Fallback UF: apenas se cidade NAO foi informada
    if not tabelas and not cidade_destino:
        tabelas = TabelaFrete.query.filter(
            TabelaFrete.transportadora_id.in_(grupo_ids),
            TabelaFrete.uf_destino == uf_destino,
        ).all()

    if not tabelas:
        return None, None, None

    tabelas_unicas = {t.id: t for t in tabelas}
    melhor_tabela = None
    melhor_dados = None
    melhor_resultado = None
    melhor_valor = None

    for t in tabelas_unicas.values():
        try:
            dados = TabelaFreteManager.preparar_dados_tabela(t)
            r = CalculadoraFrete.calcular_frete_unificado(
                peso=peso,
                valor_mercadoria=valor_mercadoria,
                tabela_dados=dados,
                cidade=None,  # CarVia: apenas icms_proprio
            )
            if r and "valor_com_icms" in r:
                v = float(r["valor_com_icms"])
                if melhor_valor is None or v < melhor_valor:
                    melhor_valor = v
                    melhor_tabela = t
                    melhor_dados = dados
                    melhor_resultado = r
        except Exception as e:
            print(f"    WARN: erro tabela {t.id} ({t.nome_tabela}): {e}")
            continue

    return melhor_tabela, melhor_dados, melhor_resultado


def calcular_peso_efetivo(nf_ids):
    """Retorna (peso_total_efetivo, lista_detalhe_por_nf)."""
    from app.carvia.models import CarviaNf
    from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService

    moto = MotoRecognitionService()
    cubado_map = moto.calcular_peso_cubado_batch(nf_ids) if nf_ids else {}
    nfs = CarviaNf.query.filter(CarviaNf.id.in_(nf_ids)).all() if nf_ids else []

    peso_total = 0.0
    detalhes = []
    for nf in nfs:
        bruto = float(nf.peso_bruto or 0)
        cubado = float(cubado_map.get(nf.id, 0) or 0)
        efetivo = max(bruto, cubado)
        peso_total += efetivo
        detalhes.append({
            "nf_id": nf.id,
            "numero_nf": nf.numero_nf,
            "peso_bruto": bruto,
            "peso_cubado": cubado,
            "peso_efetivo": efetivo,
            "fonte": "CUBADO" if cubado > bruto else ("BRUTO" if bruto > 0 else "ZERO"),
        })
    return peso_total, detalhes


def localizar_nfs_do_frete(frete):
    """Resolve NFs do frete a partir de numeros_nfs + cnpj_emitente + cnpj_destino."""
    from app.carvia.models import CarviaNf

    if not frete.numeros_nfs:
        return []
    numeros = [n.strip() for n in frete.numeros_nfs.split(",") if n.strip()]
    # NAO filtrar por status — frete e a fonte autoritativa, NF pode ter
    # mudado de status (CANCELADA = soft delete) entre criacao do frete e fix.
    return CarviaNf.query.filter(
        CarviaNf.numero_nf.in_(numeros),
        CarviaNf.cnpj_emitente == frete.cnpj_emitente,
        CarviaNf.cnpj_destinatario == frete.cnpj_destino,
    ).all()


def processar_frete(svc, frete, preservar_manual, apply_changes):
    """Processa um frete. Retorna dict com resultado."""
    out = {
        "frete_id": frete.id,
        "numeros_nfs": frete.numeros_nfs,
        "transportadora_id": frete.transportadora_id,
        "uf_destino": frete.uf_destino,
        "cidade_destino": frete.cidade_destino,
        "valor_atual": float(frete.valor_cotado or 0),
        "peso_atual": float(frete.peso_total or 0),
        "status": "PENDING",
        "razao": None,
    }

    # Skip se ja corrigido
    if frete.tabela_nome_tabela:
        out["status"] = "SKIP-already-fixed"
        out["razao"] = f"tabela_nome_tabela ja = {frete.tabela_nome_tabela}"
        return out

    # Skip frete 127 (sem tabela MG)
    if frete.id in FRETES_SEM_TABELA:
        out["status"] = "SKIP-sem-tabela"
        out["razao"] = FRETES_SEM_TABELA[frete.id]
        return out

    nfs = localizar_nfs_do_frete(frete)
    if not nfs:
        out["status"] = "FAIL-nf-nao-encontrada"
        out["razao"] = f"NFs {frete.numeros_nfs} nao localizadas"
        return out

    nf_ids = [n.id for n in nfs]
    peso, detalhes_peso = calcular_peso_efetivo(nf_ids)
    out["peso_calculado"] = peso
    out["peso_detalhes"] = detalhes_peso

    if peso <= 0:
        out["status"] = "FAIL-peso-zero"
        out["razao"] = "Todas NFs com peso_bruto e peso_cubado zerados — necessita peso manual"
        return out

    valor_merc = float(frete.valor_total_nfs or 0)
    tabela, dados, resultado = buscar_melhor_tabela(
        svc, frete.transportadora_id, frete.cidade_destino, frete.uf_destino,
        peso, valor_merc,
    )

    if not tabela or not dados or not resultado:
        out["status"] = "FAIL-sem-tabela"
        out["razao"] = (
            f"Sem tabela para transportadora {frete.transportadora_id} -> "
            f"{frete.uf_destino}/{frete.cidade_destino}"
        )
        return out

    valor_calc = round(float(resultado["valor_com_icms"]), 2)
    out["tabela_nome"] = tabela.nome_tabela
    out["tabela_modalidade"] = tabela.modalidade
    out["tabela_id"] = tabela.id
    out["valor_calculado"] = valor_calc

    # Decidir valor final
    valor_final = valor_calc
    obs_extra = ""
    if frete.id in VALOR_MANUAL_USUARIO and preservar_manual:
        descricao_manual, valor_manual = VALOR_MANUAL_USUARIO[frete.id]
        valor_final = valor_manual
        obs_extra = (
            f" valor_cotado preservado MANUAL R$ {valor_manual:.2f} — "
            f"{descricao_manual}. Tabela referencia calculo: R$ {valor_calc:.2f}."
        )

    out["valor_final"] = valor_final
    out["preservar_manual"] = bool(obs_extra)

    if apply_changes:
        # Atualizar campos da tabela (snapshot)
        frete.tabela_nome_tabela = tabela.nome_tabela
        frete.tabela_valor_kg = float(dados.get("valor_kg") or 0)
        frete.tabela_percentual_valor = float(dados.get("percentual_valor") or 0)
        frete.tabela_frete_minimo_valor = float(dados.get("frete_minimo_valor") or 0)
        frete.tabela_frete_minimo_peso = float(dados.get("frete_minimo_peso") or 0)
        frete.tabela_icms_proprio = float(dados.get("icms_proprio") or 0)
        frete.tabela_icms_incluso = bool(dados.get("icms_incluso"))
        frete.tabela_percentual_gris = float(dados.get("percentual_gris") or 0)
        frete.tabela_gris_minimo = float(dados.get("gris_minimo") or 0)
        frete.tabela_pedagio_por_100kg = float(dados.get("pedagio_por_100kg") or 0)
        frete.tabela_valor_tas = float(dados.get("valor_tas") or 0)
        frete.tabela_percentual_adv = float(dados.get("percentual_adv") or 0)
        frete.tabela_adv_minimo = float(dados.get("adv_minimo") or 0)
        frete.tabela_percentual_rca = float(dados.get("percentual_rca") or 0)
        frete.tabela_valor_despacho = float(dados.get("valor_despacho") or 0)
        frete.tabela_valor_cte = float(dados.get("valor_cte") or 0)
        # tabela_icms: campo composito (servico canonico sempre escreve, mesmo
        # que zero — TabelaFrete nao tem este campo, vem 0 do TabelaFreteManager)
        frete.tabela_icms = float(dados.get("icms") or 0)
        # tabela_icms_destino: copiado do embarque pelo servico. Backfill nao
        # tem embarque -> mantem NULL (correto, CarVia usa apenas icms_proprio).

        # Atualizar peso (caso esteja diferente do efetivo calculado).
        # Para fretes manual-preserved: nao mexe no peso (pode ter sido o que
        # gerou o valor manual informado pelo usuario).
        peso_preservar = frete.id in VALOR_MANUAL_USUARIO and preservar_manual
        if not peso_preservar and abs((frete.peso_total or 0) - peso) > 0.01:
            frete.peso_total = peso
        elif peso_preservar and abs((frete.peso_total or 0) - peso) > 0.01:
            print(
                f"    NOTA: peso_total preservado ({frete.peso_total:.2f}kg) "
                f"mesmo com calc divergente ({peso:.2f}kg) — manual-preserve"
            )

        # Atualizar valor cotado/considerado
        frete.valor_cotado = valor_final
        if frete.valor_considerado is None or float(frete.valor_considerado) == out["valor_atual"]:
            # So atualiza valor_considerado se ele acompanhava o cotado
            frete.valor_considerado = valor_final

        # Adicionar nota
        nota = (
            f"\n{NOTA_CORRECAO} Tabela: {tabela.nome_tabela} ({tabela.modalidade}). "
            f"Peso efetivo: {peso:.2f}kg (anterior: {out['peso_atual']:.2f}). "
            f"Valor calculo: R$ {valor_calc:.2f} (anterior: R$ {out['valor_atual']:.2f})."
            f"{obs_extra}"
        )
        frete.observacoes = (frete.observacoes or "") + nota

    out["status"] = "OK"
    return out


def imprimir_resumo(resultados):
    """Imprime relatorio agregado."""
    por_status = {}
    for r in resultados:
        por_status.setdefault(r["status"], []).append(r)

    print("\n" + "=" * 70)
    print("RESUMO DA EXECUCAO")
    print("=" * 70)
    for status, items in sorted(por_status.items()):
        print(f"\n{status} ({len(items)} fretes):")
        for r in items:
            extra = ""
            if r.get("tabela_nome"):
                extra = (
                    f" | tabela={r['tabela_nome']} | calc=R${r.get('valor_calculado', 0):.2f}"
                    f" | atual=R${r['valor_atual']:.2f}"
                    + (" [MANUAL preservado]" if r.get("preservar_manual") else "")
                )
            elif r.get("razao"):
                extra = f" | {r['razao']}"
            print(f"  #{r['frete_id']:3d} (NFs {r['numeros_nfs']}){extra}")

    total_ok = len(por_status.get("OK", []))
    total_skip = sum(len(v) for k, v in por_status.items() if k.startswith("SKIP"))
    total_fail = sum(len(v) for k, v in por_status.items() if k.startswith("FAIL"))
    print(f"\nTotal: {len(resultados)} | OK: {total_ok} | SKIP: {total_skip} | FAIL: {total_fail}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="Persistir mudancas no banco (default: dry-run)")
    parser.add_argument("--preservar-manual", action="store_true",
                        help="Mantem valor_cotado dos 3 fretes com valor manual informado pelo usuario")
    parser.add_argument("--frete-ids", type=str, default=None,
                        help="Lista CSV de IDs de fretes (ex: 108,109,110). Default: todos da sessao 541")
    parser.add_argument("--json", action="store_true", help="Imprime resultados em JSON ao final")
    args = parser.parse_args()

    if args.frete_ids:
        frete_ids = [int(x) for x in args.frete_ids.split(",") if x.strip()]
    else:
        frete_ids = FRETE_IDS_DEFAULT

    print(f"Modo: {'APPLY (persiste)' if args.apply else 'DRY-RUN (sem commit)'}")
    print(f"Preservar valor manual: {'SIM' if args.preservar_manual else 'NAO'}")
    print(f"Fretes: {len(frete_ids)} -> {frete_ids[:5]}...{frete_ids[-3:]}")

    app = create_app()
    with app.app_context():
        from app.carvia.models import CarviaFrete
        from app.carvia.services.pricing.cotacao_service import CotacaoService

        svc = CotacaoService()
        resultados = []
        for fid in frete_ids:
            frete = CarviaFrete.query.get(fid)
            if not frete:
                resultados.append({
                    "frete_id": fid, "status": "FAIL-nao-existe",
                    "razao": f"Frete {fid} nao encontrado", "numeros_nfs": "",
                    "transportadora_id": None, "uf_destino": None, "cidade_destino": None,
                    "valor_atual": 0, "peso_atual": 0,
                })
                continue

            print(f"\n--- Frete #{fid} (NFs {frete.numeros_nfs}, transp={frete.transportadora_id}, {frete.uf_destino}/{frete.cidade_destino}) ---")
            try:
                r = processar_frete(svc, frete, args.preservar_manual, args.apply)
                resultados.append(r)
                print(f"  -> {r['status']}", end="")
                if r.get("tabela_nome"):
                    print(f" | tabela={r['tabela_nome']} ({r.get('tabela_modalidade')})")
                    print(f"  Peso: {r['peso_calculado']:.2f}kg | Valor calc: R${r['valor_calculado']:.2f} | Final: R${r.get('valor_final', 0):.2f}")
                else:
                    print(f" | {r.get('razao', '')}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                # Limpar sessao para nao contaminar proximos fretes
                db.session.rollback()
                resultados.append({
                    "frete_id": fid, "status": "FAIL-exception",
                    "razao": str(e), "numeros_nfs": frete.numeros_nfs,
                    "transportadora_id": frete.transportadora_id,
                    "uf_destino": frete.uf_destino, "cidade_destino": frete.cidade_destino,
                    "valor_atual": float(frete.valor_cotado or 0),
                    "peso_atual": float(frete.peso_total or 0),
                })

        imprimir_resumo(resultados)

        if args.apply:
            ok_count = sum(1 for r in resultados if r["status"] == "OK")
            if ok_count > 0:
                print(f"\nCommitando {ok_count} fretes corrigidos...")
                db.session.commit()
                print(f"OK — {ok_count} fretes atualizados em {datetime.now().isoformat()}")
            else:
                print("\nNenhum frete OK para commitar.")
        else:
            db.session.rollback()
            print("\nDRY-RUN — nenhuma alteracao persistida.")

        if args.json:
            print("\n=== JSON ===")
            print(json.dumps(resultados, default=str, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
