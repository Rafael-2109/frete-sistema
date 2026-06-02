# etapa: audit
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""RELATORIO FINAL — auditoria SOT vs todas as fontes derivadas.

Versao DEFINITIVA com a descoberta-chave: o inventario fisico do sabado NAO
cobriu todos os SKUs do Odoo. Apenas 730 cods de 2231 (33%) foram inventariados.

Gera relatorio com 3 visoes:
A) MACRO (todos os cods do Odoo, assumindo qtd_inv=0 para nao-contados) — visao "ingenua"
B) APENAS CONTADOS (so SKUs presentes no inventario) — visao REAL
C) NAO CONTADOS (SKUs que Odoo tem mas inventario nao) — para confirmar com usuario

NAO MEXE NAS PLANILHAS ORIGINAIS.
Gera: docs/inventario-2026-05/07-relatorios/RELATORIO_FINAL_SOT_2026_05_18.xlsx
"""
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

INVENTARIO_DIR = '/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26'
RELATORIOS_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
OUT_PATH = os.path.join(RELATORIOS_DIR, 'RELATORIO_FINAL_SOT_2026_05_18.xlsx')

COMPANY_ID = {'FB': 1, 'CD': 4, 'LF': 5}
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}


def _norm_cod(x):
    if x is None:
        return ''
    if isinstance(x, float):
        if pd.isna(x):
            return ''
        if x == int(x):
            return str(int(x))
        return str(x)
    if isinstance(x, int):
        return str(x)
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s


def carregar_inv():
    path = os.path.join(INVENTARIO_DIR, 'COMPILADO INV. 16.05.2026.xlsx')
    out = []
    for filial in ['FB', 'LF', 'CD']:
        df = pd.read_excel(path, sheet_name=filial)
        df.columns = [c.strip().upper() for c in df.columns]
        df = df.rename(columns={c: 'LOTE' for c in df.columns if c.strip() == 'LOTE'})
        df['cod_produto'] = df['CODIGO'].apply(_norm_cod)
        df = df[df['cod_produto'].str.isdigit()]
        df['qtd'] = pd.to_numeric(df['QTD'], errors='coerce').fillna(0)
        df['filial'] = filial
        df['company_id'] = COMPANY_ID[filial]
        out.append(df[['company_id', 'filial', 'cod_produto', 'qtd']])
    return pd.concat(out, ignore_index=True)


def carregar_odoo():
    out = []
    for filial in ['FB', 'LF', 'CD']:
        path = os.path.join(INVENTARIO_DIR, f'estoque-odoo-{filial}.xlsx')
        df = pd.read_excel(path)
        df['cod_produto'] = df['cod_produto'].apply(_norm_cod)
        df['qtd'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['valor'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
        df['filial'] = filial
        df['company_id'] = COMPANY_ID[filial]
        out.append(df[['company_id', 'filial', 'cod_produto', 'qtd', 'valor']])
    return pd.concat(out, ignore_index=True)


def carregar_tabela():
    from app import create_app, db
    app = create_app()
    with app.app_context():
        rows = db.session.execute(db.text("""
            SELECT company_id, cod_produto,
                   SUM(qtd_ajuste)::float AS tab_qtd,
                   SUM(qtd_ajuste * COALESCE(custo_medio,0))::float AS tab_valor,
                   COUNT(*) AS tab_n,
                   STRING_AGG(DISTINCT acao_decidida, ',') AS tab_acoes,
                   STRING_AGG(DISTINCT status, ',') AS tab_statuses,
                   SUM(CASE WHEN status='EXECUTADO' THEN qtd_ajuste ELSE 0 END)::float AS exec_qtd,
                   SUM(CASE WHEN status='EXECUTADO' THEN qtd_ajuste*COALESCE(custo_medio,0) ELSE 0 END)::float AS exec_valor,
                   SUM(CASE WHEN status='PROPOSTO' THEN qtd_ajuste ELSE 0 END)::float AS prop_qtd,
                   SUM(CASE WHEN status='PROPOSTO' THEN qtd_ajuste*COALESCE(custo_medio,0) ELSE 0 END)::float AS prop_valor,
                   SUM(CASE WHEN status='FALHA' THEN qtd_ajuste ELSE 0 END)::float AS falha_qtd,
                   SUM(CASE WHEN status='APROVADO' THEN qtd_ajuste ELSE 0 END)::float AS aprov_qtd
            FROM ajuste_estoque_inventario
            WHERE ciclo='INVENTARIO_2026_05'
              AND status <> 'CANCELADO'
            GROUP BY company_id, cod_produto
        """)).mappings().all()
    df = pd.DataFrame(rows)
    df['cod_produto'] = df['cod_produto'].apply(_norm_cod)
    return df


def main():
    print('=' * 70)
    print('RELATORIO FINAL SOT — INVENTARIO 2026-05')
    print('=' * 70)

    inv = carregar_inv()
    odoo = carregar_odoo()
    tab = carregar_tabela()

    # Agregar Odoo por (company, cod)
    odoo_g = odoo.groupby(['company_id', 'filial', 'cod_produto'], as_index=False).agg(
        qtd_odoo=('qtd', 'sum'),
        valor_odoo=('valor', 'sum')
    )
    odoo_g['custo_unit'] = np.where(odoo_g['qtd_odoo'] != 0,
                                     odoo_g['valor_odoo'] / odoo_g['qtd_odoo'], 0)

    # Agregar inventario por (company, cod)
    inv_g = inv.groupby(['company_id', 'filial', 'cod_produto'], as_index=False).agg(
        qtd_inv=('qtd', 'sum')
    )

    # ==============================================================
    # VISAO A: TODOS os SKUs Odoo + INV (full outer join)
    # ==============================================================
    full = odoo_g.merge(inv_g, on=['company_id', 'filial', 'cod_produto'], how='outer')
    full['qtd_odoo'] = full['qtd_odoo'].fillna(0)
    full['qtd_inv'] = full['qtd_inv'].fillna(0)
    full['valor_odoo'] = full['valor_odoo'].fillna(0)
    full['custo_unit'] = full['custo_unit'].fillna(0)
    # company_id pode estar NaN se veio so do inv
    full['filial'] = full.apply(
        lambda r: r['filial'] if pd.notna(r['filial']) else COMPANY_NAME.get(r['company_id'], '?'),
        axis=1
    )
    full['diff_qtd'] = full['qtd_inv'] - full['qtd_odoo']
    full['valor_diff'] = full['diff_qtd'] * full['custo_unit']

    # categoria
    def categoria_cobertura(row):
        i, o = row['qtd_inv'], row['qtd_odoo']
        if abs(i) < 0.001 and o > 0.001:
            return 'SO_ODOO (nao contado fisicamente)'
        if i > 0.001 and abs(o) < 0.001:
            return 'SO_INV (sem saldo Odoo)'
        if abs(i) < 0.001 and abs(o) < 0.001:
            return 'AMBOS_ZERO'
        return 'AMBOS'
    full['categoria_cob'] = full.apply(categoria_cobertura, axis=1)

    # merge tabela
    full = full.merge(tab, on=['company_id', 'cod_produto'], how='left')
    for c in ['tab_qtd', 'tab_valor', 'tab_n', 'exec_qtd', 'exec_valor',
              'prop_qtd', 'prop_valor', 'falha_qtd', 'aprov_qtd']:
        if c in full.columns:
            full[c] = full[c].fillna(0)
    for c in ['tab_acoes', 'tab_statuses']:
        if c in full.columns:
            full[c] = full[c].fillna('')

    # delta vs SOT
    full['delta_tab_vs_sot'] = full['tab_qtd'] - full['diff_qtd']
    full['delta_valor'] = full['delta_tab_vs_sot'] * full['custo_unit']

    # ==============================================================
    # RESUMO POR FILIAL — VISAO A (todos cods)
    # ==============================================================
    resumo_full = full.groupby(['filial', 'company_id'], as_index=False).agg(
        n_cods_total=('cod_produto', 'count'),
        sot_qtd_inv=('qtd_inv', 'sum'),
        sot_qtd_odoo=('qtd_odoo', 'sum'),
        sot_diff=('diff_qtd', 'sum'),
        sot_valor_diff=('valor_diff', 'sum'),
        tab_qtd=('tab_qtd', 'sum'),
        tab_valor=('tab_valor', 'sum'),
        exec_valor=('exec_valor', 'sum'),
        prop_valor=('prop_valor', 'sum'),
        delta_valor=('delta_valor', 'sum')
    )

    # ==============================================================
    # VISAO B: APENAS SKUs CONTADOS
    # ==============================================================
    contados = full[full['categoria_cob'].isin(['AMBOS', 'SO_INV'])].copy()
    resumo_contados = contados.groupby(['filial', 'company_id'], as_index=False).agg(
        n_cods_contados=('cod_produto', 'count'),
        sot_qtd_inv=('qtd_inv', 'sum'),
        sot_qtd_odoo=('qtd_odoo', 'sum'),
        sot_diff=('diff_qtd', 'sum'),
        sot_valor_diff=('valor_diff', 'sum'),
        tab_qtd=('tab_qtd', 'sum'),
        tab_valor=('tab_valor', 'sum'),
        delta_valor=('delta_valor', 'sum')
    )

    # ==============================================================
    # VISAO C: NAO CONTADOS
    # ==============================================================
    nao_contados = full[full['categoria_cob'] == 'SO_ODOO (nao contado fisicamente)'].copy()
    resumo_nao_contados = nao_contados.groupby(['filial', 'company_id'], as_index=False).agg(
        n_cods_nao_contados=('cod_produto', 'count'),
        sot_qtd_odoo=('qtd_odoo', 'sum'),
        valor_odoo=('valor_odoo', 'sum'),
        tab_qtd=('tab_qtd', 'sum'),
        tab_valor=('tab_valor', 'sum'),
        n_ajustes_tab=('tab_n', 'sum')
    )

    # ==============================================================
    # VEREDITO POR FILIAL
    # ==============================================================
    veredito = []
    for cid, fil in [(1, 'FB'), (4, 'CD'), (5, 'LF')]:
        rc = resumo_contados[resumo_contados['company_id'] == cid].iloc[0]
        rnc = resumo_nao_contados[resumo_nao_contados['company_id'] == cid].iloc[0]
        rf = resumo_full[resumo_full['company_id'] == cid].iloc[0]
        v_real = rc['sot_valor_diff']
        v_tab = rf['tab_valor']
        v_inflado = rnc['valor_odoo']
        veredito.append({
            'filial': fil,
            'cods_contados': int(rc['n_cods_contados']),
            'cods_nao_contados': int(rnc['n_cods_nao_contados']),
            'ajuste_real_necessario_R$': round(v_real, 2),
            'tabela_atual_R$': round(v_tab, 2),
            'inflacao_da_tabela_R$': round(v_tab - v_real, 2),
            'odoo_sem_contagem_R$': round(v_inflado, 2),
            'analise': '',
        })
    df_veredito = pd.DataFrame(veredito)

    def avaliar(row):
        real = row['ajuste_real_necessario_R$']
        tab = row['tabela_atual_R$']
        if abs(real) < 1:
            return 'TABELA OK (sem ajuste necessario)'
        ratio = abs(tab) / abs(real) if abs(real) > 0 else 0
        if ratio > 5:
            return 'TABELA MUITO INFLADA (>5x do real) — pode incluir SKUs nao contados'
        if ratio < 0.1:
            return 'TABELA SUB-APLICADA (<10% do real) — faltam ajustes'
        if 0.8 <= ratio <= 1.2:
            return 'TABELA ALINHADA com SOT (delta <20%)'
        if ratio < 0.8:
            return 'TABELA SUB-APLICADA (delta significativo)'
        return 'TABELA INFLADA (>20% do real)'
    df_veredito['analise'] = df_veredito.apply(avaliar, axis=1)

    # ==============================================================
    # DETALHES: ajustes da tabela que SE REFEREM a cods NAO CONTADOS
    # ==============================================================
    nao_cont_com_ajuste = nao_contados[nao_contados['tab_n'] > 0].copy()
    nao_cont_com_ajuste['abs_v'] = nao_cont_com_ajuste['tab_valor'].abs()
    nao_cont_com_ajuste = nao_cont_com_ajuste.sort_values('abs_v', ascending=False)

    # ==============================================================
    # ESCREVER
    # ==============================================================
    os.makedirs(RELATORIOS_DIR, exist_ok=True)
    print(f'\nEscrevendo {OUT_PATH}...')
    with pd.ExcelWriter(OUT_PATH, engine='xlsxwriter') as writer:
        # README
        readme = pd.DataFrame([
            ['Data', '2026-05-18'],
            ['Hora', pd.Timestamp.now().strftime('%H:%M')],
            ['', ''],
            ['SOT-INV', 'COMPILADO INV. 16.05.2026.xlsx (sabado, fisico)'],
            ['SOT-ODOO', 'estoque-odoo-{FB,LF,CD}.xlsx (domingo 21:44, PRE-execucoes)'],
            ['', ''],
            ['DESCOBERTA CHAVE',
             'INVENTARIO NAO COBRIU TODOS OS SKUs DO ODOO. Apenas 730/2231 cods (33%) foram contados fisicamente.'],
            ['', ''],
            ['VISAO A (Macro)',
             'Compara TODOS os cods do Odoo, assumindo qtd_inv=0 para nao-contados. Esta e a visao "ingenua" — a tabela do sistema gerou ajustes assim, inflando totais.'],
            ['VISAO B (Real)',
             'Compara APENAS os cods presentes no inventario fisico. Esta e a visao REAL do ajuste necessario.'],
            ['VISAO C (Nao contados)',
             'Lista os 1570 SKUs no Odoo SEM contagem fisica. A tabela criou ajustes para muitos deles — provavel inflacao.'],
            ['', ''],
            ['RECOMENDACAO',
             'Limpar a tabela removendo ajustes para SKUs nao contados (VISAO C). So manter os ajustes da VISAO B.'],
        ], columns=['Campo', 'Valor'])
        readme.to_excel(writer, sheet_name='README', index=False)

        # Veredito
        df_veredito.to_excel(writer, sheet_name='1_VEREDITO', index=False)

        # Resumo VISAO A
        resumo_full.to_excel(writer, sheet_name='2_VisaoA_Macro_Todos', index=False)

        # Resumo VISAO B
        resumo_contados.to_excel(writer, sheet_name='3_VisaoB_So_Contados', index=False)

        # Resumo VISAO C
        resumo_nao_contados.to_excel(writer, sheet_name='4_VisaoC_Nao_Contados', index=False)

        # Detalhe FULL (todos cods)
        cols = ['company_id', 'filial', 'cod_produto',
                'qtd_inv', 'qtd_odoo', 'diff_qtd', 'custo_unit', 'valor_diff',
                'categoria_cob',
                'tab_qtd', 'tab_valor', 'tab_n', 'tab_acoes', 'tab_statuses',
                'exec_qtd', 'exec_valor', 'prop_qtd', 'prop_valor', 'falha_qtd', 'aprov_qtd',
                'delta_tab_vs_sot', 'delta_valor']
        full[cols].sort_values(['company_id', 'cod_produto']).to_excel(
            writer, sheet_name='5_Detalhe_TODOS', index=False
        )

        # Detalhe SO contados (visao REAL)
        contados[cols].sort_values(['company_id', 'cod_produto']).to_excel(
            writer, sheet_name='6_Detalhe_SO_Contados', index=False
        )

        # Nao contados COM ajuste na tabela (CANDIDATOS A LIMPAR)
        cols_nc = ['company_id', 'filial', 'cod_produto', 'qtd_odoo', 'valor_odoo',
                   'tab_qtd', 'tab_valor', 'tab_n', 'tab_acoes', 'tab_statuses']
        nao_cont_com_ajuste[cols_nc].to_excel(
            writer, sheet_name='7_NaoContados_C_Ajuste', index=False
        )

    print(f'OK. Arquivo: {OUT_PATH}')

    print('\n' + '=' * 70)
    print('VEREDITO POR FILIAL')
    print('=' * 70)
    for _, r in df_veredito.iterrows():
        print(f"\n{r['filial']}:")
        print(f"  Cods contados: {r['cods_contados']:>4} | Nao contados: {r['cods_nao_contados']:>5}")
        print(f"  Ajuste REAL necessario:    R$ {r['ajuste_real_necessario_R$']:>18,.2f}")
        print(f"  Tabela atual diz:           R$ {r['tabela_atual_R$']:>18,.2f}")
        print(f"  Inflacao/sub-aplicacao:    R$ {r['inflacao_da_tabela_R$']:>18,.2f}")
        print(f"  Odoo sem contagem:         R$ {r['odoo_sem_contagem_R$']:>18,.2f}")
        print(f"  Avaliacao: {r['analise']}")

    # Total geral
    total_real = df_veredito['ajuste_real_necessario_R$'].sum()
    total_tab = df_veredito['tabela_atual_R$'].sum()
    total_nc = df_veredito['odoo_sem_contagem_R$'].sum()
    print('\n' + '=' * 70)
    print(f"AJUSTE REAL NECESSARIO TOTAL:        R$ {total_real:>18,.2f}")
    print(f"TABELA SISTEMA ATUAL:                R$ {total_tab:>18,.2f}")
    print(f"INFLACAO (tabela - real):            R$ {total_tab - total_real:>18,.2f}")
    print(f"ODOO sem contagem (potencial inflado): R$ {total_nc:>18,.2f}")
    print('=' * 70)


if __name__ == '__main__':
    main()
