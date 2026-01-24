"""
Migração: Atualizar nomes e cod_produto dos perfis fiscais existentes.

Operações:
1. Preenche nome_empresa_compradora usando mapeamento hardcoded CNPJ → Nome
2. Preenche razao_fornecedor buscando no Odoo via res.partner pelo CNPJ
3. Preenche nome_produto buscando no Odoo via product.product:
   - Se cod_produto é numérico (product_id antigo): busca default_code e name,
     e ATUALIZA cod_produto para o default_code correto
   - Se cod_produto não é numérico: busca name pelo default_code
4. Commit em batches de 50

Uso:
    python scripts/migrations/atualizar_nomes_perfis_existentes.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.recebimento.models import PerfilFiscalProdutoFornecedor
from app.odoo.utils.connection import get_odoo_connection

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


def buscar_produtos_por_id(odoo, product_ids):
    """Busca default_code e name de produtos no Odoo pelo ID numérico."""
    mapa = {}
    if not product_ids:
        return mapa
    try:
        produtos = odoo.search_read(
            'product.product',
            [['id', 'in', list(product_ids)]],
            fields=['id', 'default_code', 'name']
        )
        for p in produtos:
            mapa[p['id']] = {
                'default_code': str(p.get('default_code', '')).strip() if p.get('default_code') else None,
                'name': p.get('name', '')
            }
    except Exception as e:
        print(f"  ⚠️  Erro ao buscar produtos por ID: {e}")
    return mapa


def cod_produto_eh_numerico(cod):
    """Verifica se cod_produto é numérico puro (indica product_id antigo do Odoo)."""
    if not cod:
        return False
    return cod.strip().isdigit()


def executar_atualizacao():
    app = create_app()
    with app.app_context():
        try:
            odoo = get_odoo_connection()
            print("✅ Conexão com Odoo estabelecida")
        except Exception as e:
            print(f"❌ Erro ao conectar ao Odoo: {e}")
            print("   O script preencherá apenas nome_empresa (hardcoded) sem Odoo.")
            odoo = None

        # Buscar todos os perfis que precisam de atualização
        perfis = PerfilFiscalProdutoFornecedor.query.all()
        total = len(perfis)
        print(f"\n📊 Total de perfis encontrados: {total}")

        if total == 0:
            print("ℹ️  Nenhum perfil para atualizar.")
            return

        # Separar perfis por tipo de atualização necessária
        perfis_sem_nome_empresa = [p for p in perfis if not p.nome_empresa_compradora]
        perfis_sem_razao_forn = [p for p in perfis if not p.razao_fornecedor]
        perfis_sem_nome_prod = [p for p in perfis if not p.nome_produto]
        perfis_cod_numerico = [p for p in perfis if cod_produto_eh_numerico(p.cod_produto)]

        print(f"   - Sem nome_empresa: {len(perfis_sem_nome_empresa)}")
        print(f"   - Sem razao_fornecedor: {len(perfis_sem_razao_forn)}")
        print(f"   - Sem nome_produto: {len(perfis_sem_nome_prod)}")
        print(f"   - Com cod_produto numérico (product_id antigo): {len(perfis_cod_numerico)}")

        # ═══════════════════════════════════════════════
        # ETAPA 1: Preencher nome_empresa (hardcoded, sem Odoo)
        # ═══════════════════════════════════════════════
        print("\n── ETAPA 1: Preenchendo nome_empresa_compradora (hardcoded) ──")
        count_empresa = 0
        for perfil in perfis_sem_nome_empresa:
            cnpj_empresa = perfil.cnpj_empresa_compradora
            if cnpj_empresa and cnpj_empresa in EMPRESAS_CNPJ_NOME:
                perfil.nome_empresa_compradora = EMPRESAS_CNPJ_NOME[cnpj_empresa]
                count_empresa += 1
        print(f"   ✅ {count_empresa} perfis atualizados com nome_empresa")

        # ═══════════════════════════════════════════════
        # ETAPA 2: Resolver cod_produto numérico → default_code
        # ═══════════════════════════════════════════════
        if odoo and perfis_cod_numerico:
            print("\n── ETAPA 2: Resolvendo cod_produto numérico → default_code ──")
            # Coletar IDs únicos
            product_ids_unicos = set()
            for perfil in perfis_cod_numerico:
                try:
                    product_ids_unicos.add(int(perfil.cod_produto.strip()))
                except (ValueError, AttributeError):
                    pass

            print(f"   Buscando {len(product_ids_unicos)} product_ids no Odoo...")
            mapa_por_id = buscar_produtos_por_id(odoo, product_ids_unicos)
            print(f"   Encontrados: {len(mapa_por_id)} produtos")

            count_cod_atualizado = 0
            count_nome_prod_via_id = 0
            for perfil in perfis_cod_numerico:
                try:
                    pid = int(perfil.cod_produto.strip())
                except (ValueError, AttributeError):
                    continue

                if pid in mapa_por_id:
                    dados = mapa_por_id[pid]
                    # Atualizar cod_produto para default_code
                    if dados['default_code']:
                        perfil.cod_produto = dados['default_code']
                        count_cod_atualizado += 1
                    # Preencher nome_produto se estiver vazio
                    if not perfil.nome_produto and dados['name']:
                        perfil.nome_produto = dados['name']
                        count_nome_prod_via_id += 1

            print(f"   ✅ {count_cod_atualizado} cod_produto atualizados (product_id → default_code)")
            print(f"   ✅ {count_nome_prod_via_id} nome_produto preenchidos via product_id")
        elif perfis_cod_numerico:
            print("\n── ETAPA 2: IGNORADA (sem conexão Odoo) ──")

        # ═══════════════════════════════════════════════
        # ETAPA 3: Preencher nome_produto (busca por default_code)
        # ═══════════════════════════════════════════════
        if odoo:
            # Recalcular perfis sem nome (alguns podem ter sido preenchidos na etapa 2)
            perfis_ainda_sem_nome_prod = [
                p for p in perfis
                if not p.nome_produto and p.cod_produto and not cod_produto_eh_numerico(p.cod_produto)
            ]

            if perfis_ainda_sem_nome_prod:
                print(f"\n── ETAPA 3: Preenchendo nome_produto por default_code ({len(perfis_ainda_sem_nome_prod)} perfis) ──")
                codigos_unicos = set(p.cod_produto.strip() for p in perfis_ainda_sem_nome_prod if p.cod_produto)
                print(f"   Buscando {len(codigos_unicos)} default_codes no Odoo...")
                mapa_por_dc = buscar_produtos_por_default_code(odoo, codigos_unicos)
                print(f"   Encontrados: {len(mapa_por_dc)} produtos")

                count_nome_prod = 0
                for perfil in perfis_ainda_sem_nome_prod:
                    cod = perfil.cod_produto.strip() if perfil.cod_produto else ''
                    if cod in mapa_por_dc:
                        perfil.nome_produto = mapa_por_dc[cod]
                        count_nome_prod += 1
                print(f"   ✅ {count_nome_prod} nome_produto preenchidos via default_code")
            else:
                print("\n── ETAPA 3: Nenhum perfil restante sem nome_produto ──")

        # ═══════════════════════════════════════════════
        # ETAPA 4: Preencher razao_fornecedor (busca por CNPJ no Odoo)
        # ═══════════════════════════════════════════════
        if odoo:
            # Recalcular perfis sem razão (nenhum deveria ter mudado, mas por segurança)
            perfis_ainda_sem_razao = [p for p in perfis if not p.razao_fornecedor and p.cnpj_fornecedor]

            if perfis_ainda_sem_razao:
                print(f"\n── ETAPA 4: Preenchendo razao_fornecedor ({len(perfis_ainda_sem_razao)} perfis) ──")
                cnpjs_unicos = set(p.cnpj_fornecedor.strip() for p in perfis_ainda_sem_razao if p.cnpj_fornecedor)
                print(f"   Buscando {len(cnpjs_unicos)} CNPJs no Odoo...")
                mapa_fornecedores = buscar_fornecedores_odoo(odoo, cnpjs_unicos)
                print(f"   Encontrados: {len(mapa_fornecedores)} fornecedores")

                count_razao = 0
                for perfil in perfis_ainda_sem_razao:
                    cnpj = perfil.cnpj_fornecedor.strip() if perfil.cnpj_fornecedor else ''
                    if cnpj in mapa_fornecedores:
                        perfil.razao_fornecedor = mapa_fornecedores[cnpj]
                        count_razao += 1
                print(f"   ✅ {count_razao} razao_fornecedor preenchidos")
            else:
                print("\n── ETAPA 4: Nenhum perfil restante sem razao_fornecedor ──")

        # ═══════════════════════════════════════════════
        # COMMIT em batches
        # ═══════════════════════════════════════════════
        print(f"\n── COMMIT: Salvando alterações em batches de {BATCH_SIZE} ──")
        try:
            # Verificar quantos perfis foram realmente modificados
            modificados = [p for p in perfis if db.session.is_modified(p)]
            total_mod = len(modificados)

            if total_mod == 0:
                print("ℹ️  Nenhuma alteração detectada. Nada a salvar.")
                return

            print(f"   Total de perfis modificados: {total_mod}")

            # Commit em batches
            for i in range(0, total_mod, BATCH_SIZE):
                db.session.flush()
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (total_mod + BATCH_SIZE - 1) // BATCH_SIZE
                print(f"   Batch {batch_num}/{total_batches}...")

            db.session.commit()
            print(f"\n✅ CONCLUÍDO: {total_mod} perfis atualizados com sucesso!")

        except Exception as e:
            print(f"\n❌ Erro ao salvar: {e}")
            db.session.rollback()
            raise

        # ═══════════════════════════════════════════════
        # RESUMO FINAL
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("RESUMO DA ATUALIZAÇÃO RETROATIVA")
        print("=" * 60)

        # Recontar para verificação
        total_com_empresa = PerfilFiscalProdutoFornecedor.query.filter(
            PerfilFiscalProdutoFornecedor.nome_empresa_compradora.isnot(None)
        ).count()
        total_com_razao = PerfilFiscalProdutoFornecedor.query.filter(
            PerfilFiscalProdutoFornecedor.razao_fornecedor.isnot(None)
        ).count()
        total_com_nome_prod = PerfilFiscalProdutoFornecedor.query.filter(
            PerfilFiscalProdutoFornecedor.nome_produto.isnot(None)
        ).count()
        total_cod_numerico = len([
            p for p in PerfilFiscalProdutoFornecedor.query.all()
            if cod_produto_eh_numerico(p.cod_produto)
        ])

        print(f"  Perfis com nome_empresa:    {total_com_empresa}/{total}")
        print(f"  Perfis com razao_fornecedor: {total_com_razao}/{total}")
        print(f"  Perfis com nome_produto:     {total_com_nome_prod}/{total}")
        print(f"  Perfis com cod numérico:     {total_cod_numerico}/{total} (deveria ser 0)")
        print("=" * 60)


if __name__ == '__main__':
    executar_atualizacao()
