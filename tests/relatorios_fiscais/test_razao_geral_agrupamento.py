"""Testes da agregacao por documento/diario do Razao Geral.

Motivacao (sessao 213d6f0b, contadora Tamiris, 2026-06-29): para conciliar o
razao de uma conta de imposto a recuperar contra a apuracao fiscal e descobrir
"quais notas compoem a diferenca", e preciso reduzir as N linhas de
account.move.line a 1 linha por (conta, documento) — somando debito/credito.
A skill so' exportava Excel linha-a-linha; este agrupamento faltava (feito
ad-hoc via ~30 scripts `python -c` na sessao).
"""

from app.relatorios_fiscais.services.razao_geral_service import agrupar_por_documento


def _dados():
    """Conta de COFINS a recuperar com 2 notas (uma com 2 lancamentos) + 1 conta de receita."""
    dados = {
        10: [
            {'move_name': 'RDVEND/2026/00933', 'journal_name': 'Devolucao', 'debit': 100.0, 'credit': 0.0, 'balance': 100.0},
            {'move_name': 'RDVEND/2026/00933', 'journal_name': 'Devolucao', 'debit': 50.0, 'credit': 0.0, 'balance': 50.0},
            {'move_name': 'RDVEND/2026/00934', 'journal_name': 'Devolucao', 'debit': 0.0, 'credit': 30.0, 'balance': -30.0},
        ],
        20: [
            {'move_name': 'FAT/2026/00001', 'journal_name': 'Vendas', 'debit': 0.0, 'credit': 200.0, 'balance': -200.0},
        ],
    }
    contas = {
        10: {'id': 10, 'code': '1140200003', 'name': 'COFINS a recuperar', 'account_type': 'asset_current'},
        20: {'id': 20, 'code': '3110100001', 'name': 'Receita de vendas', 'account_type': 'income'},
    }
    return dados, contas


def test_agrupa_por_conta_e_documento_somando_debito_credito():
    dados, contas = _dados()
    res = agrupar_por_documento(dados, contas)
    # 3 grupos: conta10/933, conta10/934, conta20/FAT
    assert len(res) == 3
    g933 = next(r for r in res if r['documento'] == 'RDVEND/2026/00933')
    assert g933['conta_code'] == '1140200003'
    assert g933['conta_nome'] == 'COFINS a recuperar'
    assert g933['n_lancamentos'] == 2
    assert g933['total_debito'] == 150.0
    assert g933['total_credito'] == 0.0
    assert g933['saldo'] == 150.0  # debito - credito


def test_documento_so_credito_tem_saldo_negativo():
    dados, contas = _dados()
    res = agrupar_por_documento(dados, contas)
    g934 = next(r for r in res if r['documento'] == 'RDVEND/2026/00934')
    assert g934['total_credito'] == 30.0
    assert g934['saldo'] == -30.0


def test_ordena_por_conta_code_e_documento():
    dados, contas = _dados()
    res = agrupar_por_documento(dados, contas)
    codes = [(r['conta_code'], r['documento'], r['diario']) for r in res]
    assert codes == sorted(codes)


def test_por_diario_separa_mesmo_documento_em_diarios_distintos():
    dados = {
        10: [
            {'move_name': 'NF/1', 'journal_name': 'Diario A', 'debit': 10.0, 'credit': 0.0, 'balance': 10.0},
            {'move_name': 'NF/1', 'journal_name': 'Diario B', 'debit': 5.0, 'credit': 0.0, 'balance': 5.0},
        ],
    }
    contas = {10: {'id': 10, 'code': '100', 'name': 'X', 'account_type': 'asset_current'}}
    sem = agrupar_por_documento(dados, contas, por_diario=False)
    com = agrupar_por_documento(dados, contas, por_diario=True)
    # Sem diario: 1 grupo (2 lancamentos somados); o campo diario fica vazio
    assert len(sem) == 1
    assert sem[0]['n_lancamentos'] == 2 and sem[0]['diario'] == ''
    # Por diario: 2 grupos distintos
    assert len(com) == 2
    assert {g['diario'] for g in com} == {'Diario A', 'Diario B'}
    assert all(g['n_lancamentos'] == 1 for g in com)


def test_campos_ausentes_e_dados_vazios_nao_quebram():
    assert agrupar_por_documento({}, {}) == []
    assert agrupar_por_documento(None, None) == []
    # mov sem move_name/journal e conta sem info -> documento '' e zeros, sem KeyError
    res = agrupar_por_documento({7: [{'debit': 5.0}]}, {})
    assert len(res) == 1
    assert res[0]['documento'] == '' and res[0]['conta_code'] == ''
    assert res[0]['total_debito'] == 5.0 and res[0]['total_credito'] == 0.0
