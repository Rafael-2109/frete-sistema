"""Data-fix: revalidar EmbarqueItem CarVia que ficaram com erro_validacao legado.

Contexto (2026-04-24 — P4):
    `validar_nf_cliente` (app/embarques/routes.py) antes do fix do P4 so
    detectava CarVia via `carvia_cotacao_id`. Itens CarVia criados por fluxos
    legados/hooks que nao populavam esse campo (mas tinham `separacao_lote_id`
    com prefixo `CARVIA-`) eram validados contra `RelatorioFaturamentoImportado`
    (Nacom), que nao conhece NFs CarVia. Resultado:
      - erro_validacao = 'NF_PENDENTE_FATURAMENTO' permanente
      - listar_embarques exibia STATUS NFs = 'Pendente Import.' e
        STATUS Fretes = 'Pendentes' para embarques CarVia validos.

Este script:
    1. Identifica EmbarqueItems CarVia (lote LIKE 'CARVIA-%' OU
       carvia_cotacao_id IS NOT NULL) com nota_fiscal preenchida e
       erro_validacao nao-nulo.
    2. Para cada um: executa a nova `validar_nf_cliente` que consulta
       `CarviaNf` corretamente. Se a NF existe ativa no CarVia com CNPJ
       compativel, `erro_validacao` e limpo e peso/valor atualizados.
    3. Reporta antes/depois.

Idempotente: pode rodar multiplas vezes sem efeito colateral (se ja foi
limpo, nao ha nada a fazer).

Nao-destrutivo: nunca altera NF ou CNPJ; apenas reclassifica.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def _contar_afetados():
    """Conta EmbarqueItems CarVia com erro_validacao nao-nulo."""
    return db.session.execute(db.text("""
        SELECT COUNT(*)
        FROM embarque_itens ei
        WHERE ei.status = 'ativo'
          AND ei.nota_fiscal IS NOT NULL
          AND TRIM(ei.nota_fiscal) != ''
          AND ei.erro_validacao IS NOT NULL
          AND (
            ei.carvia_cotacao_id IS NOT NULL
            OR ei.separacao_lote_id LIKE 'CARVIA-%%'
          )
    """)).scalar()


def verificar_antes():
    total = _contar_afetados()
    print(f"[BEFORE] EmbarqueItems CarVia com erro_validacao nao-nulo: {total}")
    return total


def executar_datafix():
    """Revalida cada item CarVia elegivel chamando validar_nf_cliente."""
    from app.embarques.models import EmbarqueItem
    from app.embarques.routes import validar_nf_cliente

    itens = EmbarqueItem.query.filter(
        EmbarqueItem.status == 'ativo',
        EmbarqueItem.nota_fiscal.isnot(None),
        EmbarqueItem.nota_fiscal != '',
        EmbarqueItem.erro_validacao.isnot(None),
        db.or_(
            EmbarqueItem.carvia_cotacao_id.isnot(None),
            EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
        ),
    ).all()

    print(f"[RUN] {len(itens)} item(ns) candidato(s) a revalidacao")

    limpos = 0
    divergentes = 0
    pendentes = 0
    erros = 0

    for item in itens:
        erro_antes = item.erro_validacao
        try:
            validar_nf_cliente(item)
            erro_depois = item.erro_validacao

            if erro_depois is None:
                limpos += 1
                print(
                    f"  [OK] item={item.id} lote={item.separacao_lote_id} "
                    f"nf={item.nota_fiscal} — {erro_antes!r} → LIMPO"
                )
            elif 'NF_DIVERGENTE' in (erro_depois or ''):
                divergentes += 1
                print(
                    f"  [DIVERG] item={item.id} lote={item.separacao_lote_id} "
                    f"nf_original_apagada — {erro_depois}"
                )
            elif 'NF_PENDENTE_FATURAMENTO' in (erro_depois or ''):
                pendentes += 1
                # Sem alteracao: NF realmente ausente no CarviaNf ainda
            else:
                print(
                    f"  [NOOP] item={item.id} lote={item.separacao_lote_id} "
                    f"erro mantido: {erro_depois}"
                )
        except Exception as e:
            erros += 1
            print(f"  [ERR] item={item.id} falhou: {e}")

    db.session.commit()
    print(
        f"[DONE] limpos={limpos} divergentes={divergentes} "
        f"pendentes_real={pendentes} erros={erros}"
    )
    return limpos


def verificar_depois():
    total = _contar_afetados()
    print(f"[AFTER] EmbarqueItems CarVia com erro_validacao nao-nulo: {total}")
    return total


def main():
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("DATA-FIX: limpar erro_validacao em EmbarqueItems CarVia (P4)")
        print("=" * 70)

        antes = verificar_antes()
        if antes == 0:
            print("[SKIP] Nenhum item candidato. Nada a fazer.")
            return

        limpos = executar_datafix()
        depois = verificar_depois()

        print("-" * 70)
        print(f"Resumo: antes={antes} depois={depois} limpos_nesta_rodada={limpos}")
        print("=" * 70)


if __name__ == '__main__':
    main()
