"""Gera arquivo SQL com inserts em massa para pedidos historicos HORA.

Le planilha Excel + mapeamentos validados (modelo_id, loja_id) e produz UM
arquivo .sql idempotente que pode ser executado direto no Render Shell:

    psql $DATABASE_URL -f /tmp/hora_seed_pedidos.sql

USO:
    python scripts/migrations/gerar_sql_pedidos_hora.py

Saida:
    scripts/migrations/hora_seed_pedidos_2026_04_30.sql

ESTRUTURA DO SQL GERADO:
    BEGIN;
    -- 1) INSERT 778 motos (insert-once em hora_moto)
    -- 2) INSERT 76 pedidos (numero_pedido com sufixo loja: -TAT/-PG/-BR)
    -- 3) INSERT 778 itens (JOIN por numero_pedido para resolver pedido_id)
    -- 4) Verificacoes (counts esperados)
    COMMIT;
"""
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd  # noqa: E402

EXCEL_PATH = '/mnt/c/Users/rafael.nascimento/Downloads/INSERT INICIAL - LOJAS MOTOCHEFE.xlsx'
OUTPUT_SQL = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'hora_seed_pedidos_2026_04_30.sql'
))

CNPJ_MATRIZ = '62634044000120'
CRIADO_POR = 'import_inicial'
COR_MOTO_PADRAO = 'NAO INFORMADA'  # hora_moto.cor e NOT NULL

# Sufixo de loja para split
LOJA_SUFIXO = {
    'MOTOCHEFE TATUAPE': 'TAT',
    'MOTOCHEFE PRAIA GRANDE': 'PG',
    'MOTOCHEFE BRAGANÇA': 'BR',
}

# IDs reais validados em hora_loja
LOJA_ID = {
    'MOTOCHEFE TATUAPE': 5,
    'MOTOCHEFE PRAIA GRANDE': 4,
    'MOTOCHEFE BRAGANÇA': 2,
}

# nome_modelo (planilha) -> hora_modelo.id (banco)
MODELO_ID = {
    'BIG TRI': 17,
    'BOB': 9,
    'GIGA': 10,
    'JET': 6,
    'JET MAX': 13,
    'RET': 2,
    'ROMA': 11,
    'S8-MINI': 20,
    'VED': 14,
    'X11-12': 15,
    'X15': 4,
    # Novos (criados pela Parte 1)
    'X12-10': 23,
    'SOMA': 24,
    'JOY SUPER': 25,
    'MIA TRI': 26,
    'SOFIA': 27,
    'MIA': 28,
    'S8-12': 29,
    'PITICA 500': 30,
    'VTB 3': 22,
    'VTB 4': 21,
}


def sql_escape(s):
    """Escapa string para SQL (single-quote)."""
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''") + "'"


def parse_preco(v):
    if pd.isna(v):
        raise ValueError("preco vazio")
    if isinstance(v, (int, float)):
        return Decimal(str(round(float(v), 2)))
    if isinstance(v, str):
        s = v.replace('R$', '').replace('\xa0', '').strip()
        s = s.replace('.', '').replace(',', '.')
        return Decimal(str(round(float(s), 2)))
    raise ValueError(f"preco invalido: {v!r}")


def parse_cor(v, para_moto=True):
    """para_moto=True: hora_moto.cor (NOT NULL) -> 'NAO INFORMADA' se vazio.
       para_moto=False: hora_pedido_item.cor (nullable) -> NULL se vazio."""
    if pd.isna(v):
        return COR_MOTO_PADRAO if para_moto else None
    s = str(v).strip()
    if not s or s.upper() == '[VAZIO]':
        return COR_MOTO_PADRAO if para_moto else None
    return s


def main():
    print(f"Lendo {EXCEL_PATH}...")
    df = pd.read_excel(EXCEL_PATH)
    print(f"  {len(df)} linhas")

    # Validar modelos
    modelos_planilha = set(df['modelo'].dropna().unique())
    modelos_faltantes = modelos_planilha - set(MODELO_ID.keys())
    if modelos_faltantes:
        raise ValueError(f"Modelos sem mapeamento: {modelos_faltantes}")

    # Validar lojas
    lojas_planilha = set(df['loja_destino'].dropna().unique())
    lojas_faltantes = lojas_planilha - set(LOJA_ID.keys())
    if lojas_faltantes:
        raise ValueError(f"Lojas sem mapeamento: {lojas_faltantes}")

    # Construir colunas derivadas
    df['chassi'] = df['chassi'].astype(str).str.strip()
    df['cor_moto'] = df['cor'].apply(lambda v: parse_cor(v, para_moto=True))
    df['cor_item'] = df['cor'].apply(lambda v: parse_cor(v, para_moto=False))
    df['preco_n'] = df['preco'].apply(parse_preco)
    df['data_pedido_d'] = df['data_pedido'].apply(
        lambda v: v.date() if hasattr(v, 'date') else v
    )
    df['sufixo'] = df['loja_destino'].map(LOJA_SUFIXO)
    df['pedido_split'] = df['numero_pedido'].astype(str).str.strip() + '-' + df['sufixo']
    df['modelo_id'] = df['modelo'].map(MODELO_ID)
    df['loja_destino_id'] = df['loja_destino'].map(LOJA_ID)

    # Pre-agregar pedidos
    grupos = df.groupby('pedido_split', sort=False)
    pedidos = []
    for split, sub in grupos:
        loja_apelido = sub['loja_destino'].iloc[0]
        data_min = sub['data_pedido_d'].min()
        observ = None
        if sub['data_pedido_d'].nunique() > 1:
            datas = sorted(sub['data_pedido_d'].unique())
            observ = (
                f"[import_inicial] Datas multiplas nos itens: "
                f"{', '.join(d.strftime('%d/%m/%Y') for d in datas)}"
            )
        pedidos.append({
            'numero_pedido': split,
            'loja_id': LOJA_ID[loja_apelido],
            'apelido': loja_apelido,
            'data_pedido': data_min,
            'observ': observ,
        })

    print(f"  {len(pedidos)} pedidos apos split")
    print(f"  {df['chassi'].nunique()} chassis distintos (motos)")

    # ----- Gerar SQL -----
    lines = []
    lines.append("-- ============================================================")
    lines.append("-- HORA — Seed inicial de pedidos historicos")
    lines.append("-- Gerado por scripts/migrations/gerar_sql_pedidos_hora.py")
    lines.append(f"-- Linhas planilha: {len(df)}")
    lines.append(f"-- Pedidos apos split: {len(pedidos)}")
    lines.append(f"-- Motos (chassis): {df['chassi'].nunique()}")
    lines.append("-- ============================================================")
    lines.append("")
    lines.append("BEGIN;")
    lines.append("")

    # 1) INSERT motos
    lines.append("-- 1) Insert hora_moto (insert-once)")
    motos_unicas = df.drop_duplicates(subset='chassi')
    chassis_count = len(motos_unicas)
    lines.append(f"-- Total: {chassis_count} motos")
    lines.append("INSERT INTO hora_moto (numero_chassi, modelo_id, cor, criado_por, criado_em) VALUES")
    rows = []
    for _, m in motos_unicas.iterrows():
        rows.append(
            f"  ({sql_escape(m['chassi'])}, {m['modelo_id']}, "
            f"{sql_escape(m['cor_moto'])}, {sql_escape(CRIADO_POR)}, NOW())"
        )
    lines.append(",\n".join(rows) + ";")
    lines.append("")

    # 2) INSERT pedidos
    lines.append("-- 2) Insert hora_pedido (apos split por loja)")
    lines.append(f"-- Total: {len(pedidos)} pedidos")
    lines.append("INSERT INTO hora_pedido")
    lines.append("  (numero_pedido, cnpj_destino, loja_destino_id, data_pedido, status,")
    lines.append("   apelido_detectado, observacoes, criado_por, criado_em)")
    lines.append("VALUES")
    rows = []
    for p in pedidos:
        rows.append(
            f"  ({sql_escape(p['numero_pedido'])}, "
            f"{sql_escape(CNPJ_MATRIZ)}, "
            f"{p['loja_id']}, "
            f"{sql_escape(p['data_pedido'].isoformat())}, "
            f"'ABERTO', "
            f"{sql_escape(p['apelido'])}, "
            f"{sql_escape(p['observ'])}, "
            f"{sql_escape(CRIADO_POR)}, "
            f"NOW())"
        )
    lines.append(",\n".join(rows) + ";")
    lines.append("")

    # 3) INSERT itens com JOIN por numero_pedido
    lines.append("-- 3) Insert hora_pedido_item (resolve pedido_id via JOIN por numero_pedido)")
    lines.append(f"-- Total: {len(df)} itens")
    lines.append("INSERT INTO hora_pedido_item (pedido_id, numero_chassi, modelo_id, cor, preco_compra_esperado)")
    lines.append("SELECT p.id, i.chassi, i.modelo_id, i.cor, i.preco")
    lines.append("FROM hora_pedido p")
    lines.append("JOIN (VALUES")
    rows = []
    for _, r in df.iterrows():
        rows.append(
            f"  ({sql_escape(r['pedido_split'])}, "
            f"{sql_escape(r['chassi'])}, "
            f"{r['modelo_id']}, "
            f"{sql_escape(r['cor_item'])}, "
            f"{r['preco_n']}::numeric)"
        )
    lines.append(",\n".join(rows))
    lines.append(") AS i (numero_pedido, chassi, modelo_id, cor, preco)")
    lines.append("ON p.numero_pedido = i.numero_pedido;")
    lines.append("")

    # 4) Verificacoes
    lines.append("-- 4) Verificacao de contagens (deve bater com os totais acima)")
    lines.append("DO $$")
    lines.append("DECLARE n_motos int; n_pedidos int; n_itens int;")
    lines.append("BEGIN")
    lines.append("  SELECT COUNT(*) INTO n_motos   FROM hora_moto         WHERE criado_por = 'import_inicial';")
    lines.append("  SELECT COUNT(*) INTO n_pedidos FROM hora_pedido       WHERE criado_por = 'import_inicial';")
    lines.append("  SELECT COUNT(*) INTO n_itens   FROM hora_pedido_item pi JOIN hora_pedido p ON p.id = pi.pedido_id WHERE p.criado_por = 'import_inicial';")
    lines.append(f"  IF n_motos   <> {chassis_count} THEN RAISE EXCEPTION 'motos: esperava {chassis_count}, achou %', n_motos; END IF;")
    lines.append(f"  IF n_pedidos <> {len(pedidos)} THEN RAISE EXCEPTION 'pedidos: esperava {len(pedidos)}, achou %', n_pedidos; END IF;")
    lines.append(f"  IF n_itens   <> {len(df)} THEN RAISE EXCEPTION 'itens: esperava {len(df)}, achou %', n_itens; END IF;")
    lines.append("  RAISE NOTICE 'OK: % motos, % pedidos, % itens', n_motos, n_pedidos, n_itens;")
    lines.append("END $$;")
    lines.append("")
    lines.append("COMMIT;")
    lines.append("")

    # Escrever
    with open(OUTPUT_SQL, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    file_size_kb = os.path.getsize(OUTPUT_SQL) / 1024
    print(f"\nArquivo gerado: {OUTPUT_SQL}")
    print(f"Tamanho: {file_size_kb:.1f} KB")
    print(f"Linhas: {sum(1 for _ in open(OUTPUT_SQL))}")
    print(f"\nResumo:")
    print(f"  motos   = {chassis_count}")
    print(f"  pedidos = {len(pedidos)}")
    print(f"  itens   = {len(df)}")
    print(f"\nPara executar:")
    print(f"  psql $DATABASE_URL -f {OUTPUT_SQL}")


if __name__ == '__main__':
    main()
