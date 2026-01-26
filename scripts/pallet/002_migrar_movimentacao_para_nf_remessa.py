#!/usr/bin/env python
"""
Script de migração de dados: MovimentacaoEstoque → PalletNFRemessa + PalletCredito

Este script migra os dados históricos de pallets do modelo antigo (MovimentacaoEstoque)
para o novo modelo estruturado v2 (PalletNFRemessa + PalletCredito).

Fonte: MovimentacaoEstoque
    Filtro: local_movimentacao='PALLET' AND tipo_movimentacao='REMESSA'

Destino:
    1. PalletNFRemessa (uma por NF de remessa)
    2. PalletCredito (um por cada NF, vinculado à NFRemessa)

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
IMPLEMENTATION_PLAN.md: Fase 1.3.1

Uso:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source .venv/bin/activate
    python scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py

    # Para dry-run (não executa, apenas mostra o que faria):
    python scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py --dry-run

    # Para forçar remigração (limpa tabelas antes):
    python scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py --force
"""
import sys
import os
import argparse
from datetime import datetime

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


# Mapeamento de company_id do Odoo para código de empresa
# Fonte: app/pallet/services/sync_odoo_service.py:39
COMPANY_ID_TO_EMPRESA = {
    4: 'CD',  # Centro de Distribuição
    1: 'FB',  # Fábrica
    3: 'SC',  # Santa Catarina
}


def verificar_tabelas_existem():
    """Verifica se as tabelas de destino existem"""
    print("\n📋 Verificando tabelas de destino...")

    tabelas = ['pallet_nf_remessa', 'pallet_creditos']
    faltando = []

    for tabela in tabelas:
        result = db.session.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = '{tabela}'
            )
        """)).scalar()

        if result:
            print(f"  ✅ Tabela {tabela} existe")
        else:
            print(f"  ❌ Tabela {tabela} NÃO existe")
            faltando.append(tabela)

    if faltando:
        print("\n⚠️  Execute primeiro: python scripts/pallet/001_criar_tabelas_pallet_v2.py")
        return False

    return True


def contar_registros_fonte():
    """Conta quantos registros serão migrados"""
    result = db.session.execute(text("""
        SELECT COUNT(*)
        FROM movimentacao_estoque
        WHERE local_movimentacao = 'PALLET'
          AND tipo_movimentacao = 'REMESSA'
          AND ativo = TRUE
    """)).scalar()

    return result or 0


def contar_registros_destino():
    """Conta quantos registros já existem no destino"""
    nf_remessa = db.session.execute(text("""
        SELECT COUNT(*) FROM pallet_nf_remessa WHERE movimentacao_estoque_id IS NOT NULL
    """)).scalar() or 0

    creditos = db.session.execute(text("""
        SELECT COUNT(*) FROM pallet_creditos WHERE movimentacao_estoque_id IS NOT NULL
    """)).scalar() or 0

    return nf_remessa, creditos


def listar_registros_fonte():
    """Lista todos os registros que serão migrados"""
    return db.session.execute(text("""
        SELECT
            id,
            numero_nf,
            data_movimentacao,
            qtd_movimentacao,
            qtd_abatida,
            tipo_destinatario,
            cnpj_destinatario,
            nome_destinatario,
            cnpj_responsavel,
            nome_responsavel,
            nf_remessa_origem,
            observacao,
            criado_em,
            criado_por,
            baixado,
            baixado_em,
            baixado_por
        FROM movimentacao_estoque
        WHERE local_movimentacao = 'PALLET'
          AND tipo_movimentacao = 'REMESSA'
          AND ativo = TRUE
        ORDER BY data_movimentacao, id
    """)).fetchall()


def ja_migrado(movimentacao_id):
    """Verifica se um registro já foi migrado"""
    result = db.session.execute(text("""
        SELECT id FROM pallet_nf_remessa WHERE movimentacao_estoque_id = :id
    """), {'id': movimentacao_id}).scalar()

    return result is not None


def limpar_tabelas_destino():
    """Limpa as tabelas de destino (para --force)"""
    print("\n🗑️  Limpando tabelas de destino (--force)...")

    # Limpar na ordem correta (FK)
    db.session.execute(text("DELETE FROM pallet_creditos WHERE movimentacao_estoque_id IS NOT NULL"))
    db.session.execute(text("DELETE FROM pallet_nf_remessa WHERE movimentacao_estoque_id IS NOT NULL"))
    db.session.commit()

    print("  ✅ Tabelas limpas")


def determinar_empresa(numero_nf):
    """
    Determina a empresa emissora baseada no número da NF ou série.

    Heurística:
    - Se não temos informação do Odoo, usamos CD como padrão
    - No futuro, podemos buscar no Odoo pelo número da NF
    """
    # Por padrão, assumimos CD se não temos informação
    # Isso pode ser ajustado manualmente ou via script posterior
    # numero_nf mantido para extensão futura (ex: buscar empresa no Odoo)
    _ = numero_nf  # Silenciar warning - parâmetro reservado para uso futuro
    return 'CD'


def calcular_prazo_dias(uf=None):
    """
    Calcula o prazo de cobrança baseado na UF.

    Regra:
    - SP ou rota RED = 7 dias
    - Demais = 30 dias
    """
    if uf and uf.upper() == 'SP':
        return 7
    return 30


def migrar_registro(mov, dry_run=False):
    """
    Migra um único registro de MovimentacaoEstoque para os novos modelos.

    Args:
        mov: Registro de MovimentacaoEstoque (row result)
        dry_run: Se True, não executa, apenas mostra

    Returns:
        tuple: (nf_remessa_id, credito_id) ou (None, None) se dry_run
    """
    # Extrair dados do registro
    mov_id = mov.id
    numero_nf = mov.numero_nf or f'LEGADO-{mov_id}'  # Fallback se não tiver NF
    data_emissao = mov.data_movimentacao
    quantidade = int(mov.qtd_movimentacao or 0)
    qtd_abatida = int(mov.qtd_abatida or 0)
    tipo_destinatario = mov.tipo_destinatario or 'TRANSPORTADORA'
    cnpj_destinatario = mov.cnpj_destinatario or ''
    nome_destinatario = mov.nome_destinatario or ''

    # Responsável pode ser diferente do destinatário (substituição)
    tipo_responsavel = tipo_destinatario  # Por padrão é o mesmo
    cnpj_responsavel = mov.cnpj_responsavel or cnpj_destinatario
    nome_responsavel = mov.nome_responsavel or nome_destinatario

    # Se tem nf_remessa_origem, é uma substituição
    nf_remessa_origem = mov.nf_remessa_origem

    # Calcular saldo (quantidade - abatida)
    qtd_saldo = max(0, quantidade - qtd_abatida)

    # Determinar status baseado no saldo e baixado
    if mov.baixado:
        status_nf = 'RESOLVIDA'
        status_credito = 'RESOLVIDO'
    elif qtd_saldo == 0:
        status_nf = 'RESOLVIDA'
        status_credito = 'RESOLVIDO'
    elif qtd_saldo < quantidade:
        status_nf = 'ATIVA'  # NF ainda ativa
        status_credito = 'PARCIAL'
    else:
        status_nf = 'ATIVA'
        status_credito = 'PENDENTE'

    # Determinar empresa
    empresa = determinar_empresa(numero_nf)

    # Calcular prazo
    prazo_dias = calcular_prazo_dias()

    if dry_run:
        print(f"    DRY-RUN: NF {numero_nf} | {tipo_destinatario} | {quantidade} un | Saldo: {qtd_saldo}")
        return None, None

    # 1. Criar PalletNFRemessa
    result = db.session.execute(text("""
        INSERT INTO pallet_nf_remessa (
            numero_nf,
            serie,
            data_emissao,
            empresa,
            tipo_destinatario,
            cnpj_destinatario,
            nome_destinatario,
            quantidade,
            status,
            qtd_resolvida,
            movimentacao_estoque_id,
            observacao,
            criado_em,
            criado_por,
            ativo
        ) VALUES (
            :numero_nf,
            '1',
            :data_emissao,
            :empresa,
            :tipo_destinatario,
            :cnpj_destinatario,
            :nome_destinatario,
            :quantidade,
            :status,
            :qtd_resolvida,
            :movimentacao_estoque_id,
            :observacao,
            :criado_em,
            :criado_por,
            TRUE
        ) RETURNING id
    """), {
        'numero_nf': numero_nf,
        'data_emissao': data_emissao,
        'empresa': empresa,
        'tipo_destinatario': tipo_destinatario,
        'cnpj_destinatario': cnpj_destinatario,
        'nome_destinatario': nome_destinatario,
        'quantidade': quantidade,
        'status': status_nf,
        'qtd_resolvida': quantidade - qtd_saldo,
        'movimentacao_estoque_id': mov_id,
        'observacao': mov.observacao or f'Migrado de MovimentacaoEstoque #{mov_id}',
        'criado_em': mov.criado_em or datetime.now(),
        'criado_por': mov.criado_por or 'migracao_v2',
    })

    nf_remessa_id = result.scalar()

    # 2. Criar PalletCredito vinculado
    result = db.session.execute(text("""
        INSERT INTO pallet_creditos (
            nf_remessa_id,
            qtd_original,
            qtd_saldo,
            tipo_responsavel,
            cnpj_responsavel,
            nome_responsavel,
            prazo_dias,
            data_vencimento,
            status,
            movimentacao_estoque_id,
            observacao,
            criado_em,
            criado_por,
            ativo
        ) VALUES (
            :nf_remessa_id,
            :qtd_original,
            :qtd_saldo,
            :tipo_responsavel,
            :cnpj_responsavel,
            :nome_responsavel,
            :prazo_dias,
            :data_vencimento,
            :status,
            :movimentacao_estoque_id,
            :observacao,
            :criado_em,
            :criado_por,
            TRUE
        ) RETURNING id
    """), {
        'nf_remessa_id': nf_remessa_id,
        'qtd_original': quantidade,
        'qtd_saldo': qtd_saldo,
        'tipo_responsavel': tipo_responsavel,
        'cnpj_responsavel': cnpj_responsavel,
        'nome_responsavel': nome_responsavel,
        'prazo_dias': prazo_dias,
        'data_vencimento': None,  # Será calculado baseado na data de emissão
        'status': status_credito,
        'movimentacao_estoque_id': mov_id,
        'observacao': nf_remessa_origem if nf_remessa_origem else None,
        'criado_em': mov.criado_em or datetime.now(),
        'criado_por': mov.criado_por or 'migracao_v2',
    })

    credito_id = result.scalar()

    return nf_remessa_id, credito_id


def executar_migracao(dry_run=False, force=False):
    """Executa a migração completa"""
    print("=" * 70)
    print("  MIGRAÇÃO: MovimentacaoEstoque → PalletNFRemessa + PalletCredito")
    print("=" * 70)

    if dry_run:
        print("\n⚠️  MODO DRY-RUN: Nenhuma alteração será feita no banco\n")

    # 1. Verificar tabelas
    if not verificar_tabelas_existem():
        return False

    # 2. Contar registros fonte
    total_fonte = contar_registros_fonte()
    print(f"\n📊 Registros para migrar: {total_fonte}")

    if total_fonte == 0:
        print("  ℹ️  Nenhum registro para migrar")
        return True

    # 3. Contar registros já migrados
    nf_destino, cred_destino = contar_registros_destino()
    if nf_destino > 0 or cred_destino > 0:
        print(f"  ⚠️  Já migrados: {nf_destino} NFs, {cred_destino} créditos")

        if force:
            if not dry_run:
                limpar_tabelas_destino()
        else:
            print("  ℹ️  Use --force para remigrar todos os registros")

    # 4. Listar e migrar registros
    registros = listar_registros_fonte()
    print(f"\n🔄 Iniciando migração de {len(registros)} registros...")

    migrados = 0
    pulados = 0
    erros = 0

    for mov in registros:
        try:
            # Verificar se já migrado (se não for force)
            if not force and not dry_run and ja_migrado(mov.id):
                pulados += 1
                continue

            nf_id, cred_id = migrar_registro(mov, dry_run=dry_run)

            if not dry_run:
                if nf_id and cred_id:
                    migrados += 1

                    # Commit a cada 100 registros
                    if migrados % 100 == 0:
                        db.session.commit()
                        print(f"  📦 Migrados {migrados}/{total_fonte}...")
            else:
                migrados += 1

        except Exception as e:
            erros += 1
            print(f"  ❌ Erro no registro #{mov.id}: {e}")
            if not dry_run:
                db.session.rollback()

    # 5. Commit final
    if not dry_run:
        db.session.commit()

    # 6. Relatório final
    print("\n" + "=" * 70)
    print("  RELATÓRIO DE MIGRAÇÃO")
    print("=" * 70)
    print(f"  Total na fonte:     {total_fonte}")
    print(f"  Migrados:           {migrados}")
    print(f"  Pulados (já exist): {pulados}")
    print(f"  Erros:              {erros}")

    if not dry_run:
        # Verificar contagens finais
        nf_final, cred_final = contar_registros_destino()
        print(f"\n  Tabelas finais:")
        print(f"    pallet_nf_remessa:  {nf_final} registros")
        print(f"    pallet_creditos:    {cred_final} registros")

    print("=" * 70)

    return erros == 0


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Migra MovimentacaoEstoque para PalletNFRemessa + PalletCredito'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Executa em modo dry-run (não altera o banco)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Força remigração (limpa registros migrados anteriormente)'
    )

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        try:
            sucesso = executar_migracao(dry_run=args.dry_run, force=args.force)

            if sucesso:
                print("\n✅ Migração concluída com sucesso!\n")
                sys.exit(0)
            else:
                print("\n❌ Migração falhou. Verifique os erros acima.\n")
                sys.exit(1)

        except Exception as e:
            print(f"\n❌ Erro fatal: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()
