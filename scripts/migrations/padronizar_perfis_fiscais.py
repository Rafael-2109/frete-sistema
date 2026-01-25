"""
Migração: Padronizar perfis fiscais existentes.

Este script garante que os dados existentes na tabela perfil_fiscal_produto_fornecedor
sigam o mesmo padrão que as 3 fontes de criação (primeira compra, perfil automático, Excel).

Operações:
1. Converte NULL → 0.00 nos campos zeráveis (reducao_bc, icms_st, ipi)
2. Preenche nomes faltantes via Odoo (empresa, fornecedor, produto)
3. Preenche campos fiscais faltantes buscando do CadastroPrimeiraCompra relacionado

IMPORTANTE: Este script NÃO infere/deduz cnpj_empresa_compradora.
Perfis sem empresa compradora devem ser corrigidos manualmente via interface.

PADRÃO DEFINIDO:
┌───────────────────────────────┬─────────────────────────────────────┐
│ Campo                         │ Padrão Quando Vazio                 │
├───────────────────────────────┼─────────────────────────────────────┤
│ cnpj_empresa_compradora       │ OBRIGATÓRIO (corrigir manualmente)  │
│ nome_empresa_compradora       │ NULL (buscar Odoo)                  │
│ razao_fornecedor              │ NULL (buscar Odoo)                  │
│ nome_produto                  │ NULL (buscar Odoo)                  │
│ reducao_bc_icms_esperada      │ 0.00 (detecta divergência)          │
│ aliquota_icms_st_esperada     │ 0.00 (detecta divergência)          │
│ aliquota_ipi_esperada         │ 0.00 (detecta divergência)          │
│ cst_*, aliq_icms, aliq_pis... │ NULL (validação pula)               │
└───────────────────────────────┴─────────────────────────────────────┘

Uso:
    python scripts/migrations/padronizar_perfis_fiscais.py

    # Apenas relatório (sem modificar)
    python scripts/migrations/padronizar_perfis_fiscais.py --dry-run
"""
import sys
import os
import argparse
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.recebimento.models import PerfilFiscalProdutoFornecedor, CadastroPrimeiraCompra
from app.odoo.utils.connection import get_odoo_connection
from sqlalchemy import text

# Mapeamento hardcoded de empresas (CNPJ digits → Nome)
EMPRESAS_CNPJ_NOME = {
    '61724241000330': 'NACOM GOYA - CD',
    '61724241000178': 'NACOM GOYA - FB',
    '61724241000259': 'NACOM GOYA - SC',
    '18467441000163': 'LA FAMIGLIA - LF',
}

BATCH_SIZE = 50


def formatar_cnpj_odoo(cnpj_digits):
    """Formata CNPJ de digits (14 chars) para formato Odoo (XX.XXX.XXX/XXXX-XX)."""
    if not cnpj_digits or len(cnpj_digits) < 14:
        return None
    cnpj = cnpj_digits[:14]
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"


def buscar_fornecedores_odoo(odoo, cnpjs_unicos):
    """Busca nomes de fornecedores no Odoo em batch por CNPJ."""
    mapa = {}
    for cnpj in cnpjs_unicos:
        cnpj_fmt = formatar_cnpj_odoo(cnpj)
        if not cnpj_fmt:
            continue
        try:
            partners = odoo.search_read(
                'res.partner',
                [['l10n_br_cnpj', '=', cnpj_fmt]],
                fields=['id', 'name'],
                limit=1
            )
            if partners:
                mapa[cnpj] = partners[0].get('name', '')
        except Exception as e:
            print(f"  ⚠️  Erro ao buscar fornecedor CNPJ {cnpj}: {e}")
    return mapa


def buscar_produtos_por_default_code(odoo, codigos):
    """Busca nomes de produtos no Odoo pelo default_code em batch."""
    mapa = {}
    if not codigos:
        return mapa
    try:
        produtos = odoo.search_read(
            'product.product',
            [['default_code', 'in', list(codigos)]],
            fields=['id', 'default_code', 'name']
        )
        for p in produtos:
            dc = str(p.get('default_code', '')).strip()
            if dc:
                mapa[dc] = p.get('name', '')
    except Exception as e:
        print(f"  ⚠️  Erro ao buscar produtos por default_code: {e}")
    return mapa


def salvar_em_batches(atualizacoes, dry_run=False):
    """Salva atualizações em batches de BATCH_SIZE usando SQL direto.

    Args:
        atualizacoes: dict {perfil_id: {campo: valor, ...}}
        dry_run: Se True, apenas simula sem salvar

    Returns:
        Tuple (total_salvos, total_erros)
    """
    if not atualizacoes:
        print("ℹ️  Nenhuma alteração para salvar.")
        return 0, 0

    if dry_run:
        print(f"   [DRY-RUN] Seriam atualizados {len(atualizacoes)} perfis")
        return len(atualizacoes), 0

    items = list(atualizacoes.items())
    total = len(items)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    total_salvos = 0
    total_erros = 0

    print(f"   Total de perfis a atualizar: {total}")
    print(f"   Batches de {BATCH_SIZE}: {total_batches}")

    for batch_num in range(total_batches):
        inicio = batch_num * BATCH_SIZE
        fim = min(inicio + BATCH_SIZE, total)
        chunk = items[inicio:fim]

        try:
            for perfil_id, campos in chunk:
                campos['atualizado_em'] = datetime.now(timezone.utc)
                set_parts = []
                params = {'id': perfil_id}
                for idx, (campo, valor) in enumerate(campos.items()):
                    param_name = f"p{idx}"
                    set_parts.append(f"{campo} = :{param_name}")
                    params[param_name] = valor

                set_clause = ', '.join(set_parts)
                sql = text(f"UPDATE perfil_fiscal_produto_fornecedor SET {set_clause} WHERE id = :id")
                db.session.execute(sql, params)

            db.session.commit()
            total_salvos += len(chunk)
            print(f"   ✅ Batch {batch_num + 1}/{total_batches} - {len(chunk)} registros salvos")

        except Exception as e:
            print(f"   ❌ Erro no batch {batch_num + 1}/{total_batches}: {e}")
            db.session.rollback()
            total_erros += len(chunk)

            # Tentar registro por registro no batch que falhou
            print(f"   🔄 Tentando registro por registro...")
            for perfil_id, campos in chunk:
                try:
                    campos['atualizado_em'] = datetime.now(timezone.utc)
                    set_parts = []
                    params = {'id': perfil_id}
                    for idx, (campo, valor) in enumerate(campos.items()):
                        param_name = f"p{idx}"
                        set_parts.append(f"{campo} = :{param_name}")
                        params[param_name] = valor

                    set_clause = ', '.join(set_parts)
                    sql = text(f"UPDATE perfil_fiscal_produto_fornecedor SET {set_clause} WHERE id = :id")
                    db.session.execute(sql, params)
                    db.session.commit()
                    total_salvos += 1
                    total_erros -= 1
                except Exception as e2:
                    print(f"      ❌ Perfil ID {perfil_id}: {e2}")
                    db.session.rollback()

    return total_salvos, total_erros


def executar_padronizacao(dry_run=False):
    """Executa a padronização dos perfis fiscais."""
    app = create_app()
    with app.app_context():
        mode_str = "[DRY-RUN] " if dry_run else ""
        print(f"\n{'=' * 70}")
        print(f"{mode_str}PADRONIZAÇÃO DE PERFIS FISCAIS")
        print("=" * 70)

        # Conectar ao Odoo
        try:
            odoo = get_odoo_connection()
            print("✅ Conexão com Odoo estabelecida")
        except Exception as e:
            print(f"❌ Erro ao conectar ao Odoo: {e}")
            print("   O script preencherá apenas dados locais sem Odoo.")
            odoo = None

        # Buscar todos os perfis
        perfis = PerfilFiscalProdutoFornecedor.query.all()
        total = len(perfis)
        print(f"\n📊 Total de perfis encontrados: {total}")

        if total == 0:
            print("ℹ️  Nenhum perfil para padronizar.")
            return

        # Diagnóstico inicial
        print("\n── DIAGNÓSTICO INICIAL ──")

        perfis_sem_empresa = [p for p in perfis if not p.cnpj_empresa_compradora]
        perfis_reducao_null = [p for p in perfis if p.reducao_bc_icms_esperada is None]
        perfis_st_null = [p for p in perfis if p.aliquota_icms_st_esperada is None]
        perfis_ipi_null = [p for p in perfis if p.aliquota_ipi_esperada is None]
        perfis_icms_null = [p for p in perfis if p.aliquota_icms_esperada is None]
        perfis_pis_null = [p for p in perfis if p.aliquota_pis_esperada is None]
        perfis_cofins_null = [p for p in perfis if p.aliquota_cofins_esperada is None]
        perfis_sem_nome_empresa = [p for p in perfis if not p.nome_empresa_compradora]
        perfis_sem_razao_forn = [p for p in perfis if not p.razao_fornecedor]
        perfis_sem_nome_prod = [p for p in perfis if not p.nome_produto]
        perfis_sem_cst_icms = [p for p in perfis if not p.cst_icms_esperado]

        print(f"   ❗ Sem cnpj_empresa_compradora:    {len(perfis_sem_empresa)}")
        print(f"   ❗ reducao_bc_icms NULL:           {len(perfis_reducao_null)}")
        print(f"   ❗ aliquota_icms_st NULL:          {len(perfis_st_null)}")
        print(f"   ❗ aliquota_ipi NULL:              {len(perfis_ipi_null)}")
        print(f"   ❗ aliquota_icms NULL:             {len(perfis_icms_null)}")
        print(f"   ❗ aliquota_pis NULL:              {len(perfis_pis_null)}")
        print(f"   ❗ aliquota_cofins NULL:           {len(perfis_cofins_null)}")
        print(f"   ⚠️  Sem nome_empresa:              {len(perfis_sem_nome_empresa)}")
        print(f"   ⚠️  Sem razao_fornecedor:          {len(perfis_sem_razao_forn)}")
        print(f"   ⚠️  Sem nome_produto:              {len(perfis_sem_nome_prod)}")
        print(f"   ℹ️  Sem cst_icms_esperado:         {len(perfis_sem_cst_icms)}")

        # Dicionário para acumular atualizações
        atualizacoes = {}

        # Expunge todos para evitar flush automático
        db.session.expunge_all()

        # ═══════════════════════════════════════════════
        # ETAPA 1: Campos zeráveis NULL → 0.00
        # ═══════════════════════════════════════════════
        print("\n── ETAPA 1: Convertendo campos zeráveis NULL → 0.00 ──")
        print("   Campos: reducao_bc, icms_st, ipi, icms, pis, cofins")
        count_zeraveis = 0

        for perfil in perfis:
            campos_atualizar = {}

            # Campos já tratados anteriormente
            if perfil.reducao_bc_icms_esperada is None:
                campos_atualizar['reducao_bc_icms_esperada'] = Decimal('0')

            if perfil.aliquota_icms_st_esperada is None:
                campos_atualizar['aliquota_icms_st_esperada'] = Decimal('0')

            if perfil.aliquota_ipi_esperada is None:
                campos_atualizar['aliquota_ipi_esperada'] = Decimal('0')

            # NOVOS: ICMS, PIS, COFINS também devem ser 0.00 se vazios
            if perfil.aliquota_icms_esperada is None:
                campos_atualizar['aliquota_icms_esperada'] = Decimal('0')

            if perfil.aliquota_pis_esperada is None:
                campos_atualizar['aliquota_pis_esperada'] = Decimal('0')

            if perfil.aliquota_cofins_esperada is None:
                campos_atualizar['aliquota_cofins_esperada'] = Decimal('0')

            if campos_atualizar:
                if perfil.id not in atualizacoes:
                    atualizacoes[perfil.id] = {}
                atualizacoes[perfil.id].update(campos_atualizar)
                count_zeraveis += 1

        print(f"   ✅ {count_zeraveis} perfis marcados (campos zeráveis)")

        # Nota: ETAPA 2 (inferir cnpj_empresa_compradora) foi REMOVIDA.
        # Perfis sem empresa compradora devem ser corrigidos manualmente.
        if perfis_sem_empresa:
            print(f"\n⚠️  ATENÇÃO: {len(perfis_sem_empresa)} perfis SEM cnpj_empresa_compradora")
            print("   Esses perfis devem ser corrigidos MANUALMENTE via interface de edição.")
            print("   O script NÃO infere/deduz a empresa compradora.")

        # ═══════════════════════════════════════════════
        # ETAPA 2: Preencher nomes via Odoo
        # ═══════════════════════════════════════════════
        if odoo:
            # 2.1 nome_empresa_compradora (hardcoded)
            if perfis_sem_nome_empresa:
                print(f"\n── ETAPA 2.1: Preenchendo nome_empresa_compradora ──")
                count_nome_empresa = 0
                for perfil in perfis_sem_nome_empresa:
                    cnpj_empresa = perfil.cnpj_empresa_compradora
                    # Também verificar se atualizações tem cnpj_empresa
                    if not cnpj_empresa and perfil.id in atualizacoes:
                        cnpj_empresa = atualizacoes[perfil.id].get('cnpj_empresa_compradora')

                    if cnpj_empresa and cnpj_empresa in EMPRESAS_CNPJ_NOME:
                        if perfil.id not in atualizacoes:
                            atualizacoes[perfil.id] = {}
                        atualizacoes[perfil.id]['nome_empresa_compradora'] = EMPRESAS_CNPJ_NOME[cnpj_empresa]
                        count_nome_empresa += 1
                print(f"   ✅ {count_nome_empresa} nome_empresa preenchidos")

            # 2.2 razao_fornecedor (Odoo)
            perfis_para_razao = [p for p in perfis if not p.razao_fornecedor and p.cnpj_fornecedor]
            if perfis_para_razao:
                print(f"\n── ETAPA 2.2: Preenchendo razao_fornecedor ({len(perfis_para_razao)} perfis) ──")
                cnpjs_unicos = set(p.cnpj_fornecedor.strip() for p in perfis_para_razao if p.cnpj_fornecedor)
                print(f"   Buscando {len(cnpjs_unicos)} CNPJs no Odoo...")
                mapa_fornecedores = buscar_fornecedores_odoo(odoo, cnpjs_unicos)
                print(f"   Encontrados: {len(mapa_fornecedores)} fornecedores")

                count_razao = 0
                for perfil in perfis_para_razao:
                    cnpj = perfil.cnpj_fornecedor.strip() if perfil.cnpj_fornecedor else ''
                    if cnpj in mapa_fornecedores:
                        if perfil.id not in atualizacoes:
                            atualizacoes[perfil.id] = {}
                        atualizacoes[perfil.id]['razao_fornecedor'] = mapa_fornecedores[cnpj]
                        count_razao += 1
                print(f"   ✅ {count_razao} razao_fornecedor preenchidos")

            # 2.3 nome_produto (Odoo)
            perfis_para_nome_prod = [p for p in perfis if not p.nome_produto and p.cod_produto]
            if perfis_para_nome_prod:
                print(f"\n── ETAPA 2.3: Preenchendo nome_produto ({len(perfis_para_nome_prod)} perfis) ──")
                codigos_unicos = set(p.cod_produto.strip() for p in perfis_para_nome_prod if p.cod_produto)
                print(f"   Buscando {len(codigos_unicos)} códigos no Odoo...")
                mapa_produtos = buscar_produtos_por_default_code(odoo, codigos_unicos)
                print(f"   Encontrados: {len(mapa_produtos)} produtos")

                count_nome_prod = 0
                for perfil in perfis_para_nome_prod:
                    cod = perfil.cod_produto.strip() if perfil.cod_produto else ''
                    if cod in mapa_produtos:
                        if perfil.id not in atualizacoes:
                            atualizacoes[perfil.id] = {}
                        atualizacoes[perfil.id]['nome_produto'] = mapa_produtos[cod]
                        count_nome_prod += 1
                print(f"   ✅ {count_nome_prod} nome_produto preenchidos")

        # ═══════════════════════════════════════════════
        # ETAPA 3: Preencher campos fiscais do CadastroPrimeiraCompra
        # ═══════════════════════════════════════════════
        print("\n── ETAPA 3: Preenchendo campos fiscais do CadastroPrimeiraCompra ──")

        # Buscar cadastros validados com dados fiscais
        cadastros_validados = CadastroPrimeiraCompra.query.filter(
            CadastroPrimeiraCompra.status == 'validado'
        ).all()

        # Criar mapa: (cnpj_fornecedor, cod_produto) → dados fiscais
        mapa_fiscal = {}
        for c in cadastros_validados:
            chave = (c.cnpj_fornecedor, c.cod_produto)
            mapa_fiscal[chave] = {
                'cst_icms': c.cst_icms,
                'cst_pis': c.cst_pis,
                'aliquota_pis': c.aliquota_pis,
                'cst_cofins': c.cst_cofins,
                'aliquota_cofins': c.aliquota_cofins,
            }

        count_fiscal = 0
        for perfil in perfis:
            chave = (perfil.cnpj_fornecedor, perfil.cod_produto)
            if chave not in mapa_fiscal:
                continue

            dados = mapa_fiscal[chave]
            campos_atualizar = {}

            # Preencher apenas campos que estão NULL no perfil
            if not perfil.cst_icms_esperado and dados['cst_icms']:
                campos_atualizar['cst_icms_esperado'] = dados['cst_icms']

            if not perfil.cst_pis_esperado and dados['cst_pis']:
                campos_atualizar['cst_pis_esperado'] = dados['cst_pis']

            if perfil.aliquota_pis_esperada is None and dados['aliquota_pis'] is not None:
                campos_atualizar['aliquota_pis_esperada'] = dados['aliquota_pis']

            if not perfil.cst_cofins_esperado and dados['cst_cofins']:
                campos_atualizar['cst_cofins_esperado'] = dados['cst_cofins']

            if perfil.aliquota_cofins_esperada is None and dados['aliquota_cofins'] is not None:
                campos_atualizar['aliquota_cofins_esperada'] = dados['aliquota_cofins']

            if campos_atualizar:
                if perfil.id not in atualizacoes:
                    atualizacoes[perfil.id] = {}
                atualizacoes[perfil.id].update(campos_atualizar)
                count_fiscal += 1

        print(f"   ✅ {count_fiscal} perfis com campos fiscais preenchidos do cadastro")

        # ═══════════════════════════════════════════════
        # COMMIT
        # ═══════════════════════════════════════════════
        print(f"\n── COMMIT: Salvando alterações ──")
        total_salvos, total_erros = salvar_em_batches(atualizacoes, dry_run=dry_run)

        # ═══════════════════════════════════════════════
        # RESUMO FINAL
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 70)
        print(f"{mode_str}RESUMO DA PADRONIZAÇÃO")
        print("=" * 70)
        print(f"  Total salvos:  {total_salvos}")
        print(f"  Total erros:   {total_erros}")

        if not dry_run:
            # Recontar para verificação final
            print("\n── VERIFICAÇÃO FINAL ──")

            total_sem_empresa = PerfilFiscalProdutoFornecedor.query.filter(
                PerfilFiscalProdutoFornecedor.cnpj_empresa_compradora.is_(None)
            ).count()
            total_reducao_null = PerfilFiscalProdutoFornecedor.query.filter(
                PerfilFiscalProdutoFornecedor.reducao_bc_icms_esperada.is_(None)
            ).count()
            total_st_null = PerfilFiscalProdutoFornecedor.query.filter(
                PerfilFiscalProdutoFornecedor.aliquota_icms_st_esperada.is_(None)
            ).count()
            total_ipi_null = PerfilFiscalProdutoFornecedor.query.filter(
                PerfilFiscalProdutoFornecedor.aliquota_ipi_esperada.is_(None)
            ).count()
            total_icms_null = PerfilFiscalProdutoFornecedor.query.filter(
                PerfilFiscalProdutoFornecedor.aliquota_icms_esperada.is_(None)
            ).count()
            total_pis_null = PerfilFiscalProdutoFornecedor.query.filter(
                PerfilFiscalProdutoFornecedor.aliquota_pis_esperada.is_(None)
            ).count()
            total_cofins_null = PerfilFiscalProdutoFornecedor.query.filter(
                PerfilFiscalProdutoFornecedor.aliquota_cofins_esperada.is_(None)
            ).count()

            print(f"   Perfis sem cnpj_empresa:     {total_sem_empresa} (corrigir manualmente)")
            print(f"   Perfis reducao_bc NULL:      {total_reducao_null} (deve ser 0)")
            print(f"   Perfis icms_st NULL:         {total_st_null} (deve ser 0)")
            print(f"   Perfis ipi NULL:             {total_ipi_null} (deve ser 0)")
            print(f"   Perfis icms NULL:            {total_icms_null} (deve ser 0)")
            print(f"   Perfis pis NULL:             {total_pis_null} (deve ser 0)")
            print(f"   Perfis cofins NULL:          {total_cofins_null} (deve ser 0)")

            total_zeraveis_null = total_reducao_null + total_st_null + total_ipi_null + total_icms_null + total_pis_null + total_cofins_null
            if total_zeraveis_null == 0:
                if total_sem_empresa == 0:
                    print("\n   🎉 PADRONIZAÇÃO COMPLETA!")
                else:
                    print(f"\n   ✅ Campos zeráveis padronizados!")
                    print(f"   ⚠️  {total_sem_empresa} perfis ainda precisam de cnpj_empresa (editar manualmente)")
            else:
                print("\n   ⚠️  Ainda existem registros fora do padrão.")

        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Padronizar perfis fiscais existentes')
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas simula sem salvar alterações')
    args = parser.parse_args()

    executar_padronizacao(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
