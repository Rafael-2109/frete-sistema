#!/usr/bin/env python
"""
Script de migração de dados: ValePallet → PalletDocumento + PalletSolucao

Este script migra os dados históricos de vales pallet do modelo antigo (ValePallet)
para os novos modelos estruturados v2 (PalletDocumento + PalletSolucao).

Fonte: ValePallet (vale_pallets)
    - Todos os registros ativos

Destino:
    1. PalletDocumento (um por ValePallet)
       - Vinculado a PalletCredito via nf_pallet → PalletNFRemessa.numero_nf
    2. PalletSolucao (se ValePallet.resolvido = True)
       - Tipo baseado em tipo_resolucao: VENDA ou RECEBIMENTO (coleta)

Dependências:
    - Script 001 deve ter sido executado (tabelas existem)
    - Script 002 deve ter sido executado (PalletNFRemessa e PalletCredito existem)
    - PalletNFRemessa deve existir para o numero_nf correspondente

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
IMPLEMENTATION_PLAN.md: Fase 1.3.2

Uso:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source .venv/bin/activate
    python scripts/pallet/003_migrar_vale_pallet_para_documento.py

    # Para dry-run (não executa, apenas mostra o que faria):
    python scripts/pallet/003_migrar_vale_pallet_para_documento.py --dry-run

    # Para forçar remigração (limpa documentos migrados antes):
    python scripts/pallet/003_migrar_vale_pallet_para_documento.py --force

    # Verbose (mostra detalhes de cada registro):
    python scripts/pallet/003_migrar_vale_pallet_para_documento.py --verbose
"""
import sys
import os
import argparse
from datetime import datetime

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


# Mapeamento de tipo_vale para tipo de documento
TIPO_VALE_MAP = {
    'CANHOTO_ASSINADO': 'CANHOTO',
    'VALE_PALLET': 'VALE_PALLET',
    # Fallback para tipos não mapeados
    None: 'CANHOTO',
    '': 'CANHOTO',
}

# Mapeamento de tipo_resolucao para tipo de solução
TIPO_RESOLUCAO_MAP = {
    'VENDA': 'VENDA',
    'COLETA': 'RECEBIMENTO',
    'PENDENTE': None,  # Não cria solução
    None: None,
    '': None,
}


def verificar_tabelas_existem():
    """Verifica se as tabelas necessárias existem"""
    print("\n📋 Verificando tabelas...")

    tabelas_necessarias = [
        'vale_pallets',          # Origem
        'pallet_documentos',     # Destino 1
        'pallet_solucoes',       # Destino 2
        'pallet_creditos',       # Para vincular
        'pallet_nf_remessa',     # Para buscar crédito
    ]
    faltando = []

    for tabela in tabelas_necessarias:
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
        if 'vale_pallets' in faltando:
            print("\n⚠️  Tabela de origem (vale_pallets) não existe!")
        else:
            print("\n⚠️  Execute primeiro os scripts anteriores:")
            print("    python scripts/pallet/001_criar_tabelas_pallet_v2.py")
            print("    python scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py")
        return False

    return True


def contar_registros_fonte():
    """Conta quantos registros serão migrados"""
    result = db.session.execute(text("""
        SELECT COUNT(*)
        FROM vale_pallets
        WHERE ativo = TRUE
    """)).scalar()

    return result or 0


def contar_registros_destino():
    """Conta quantos registros já existem no destino"""
    documentos = db.session.execute(text("""
        SELECT COUNT(*) FROM pallet_documentos WHERE vale_pallet_id IS NOT NULL
    """)).scalar() or 0

    solucoes = db.session.execute(text("""
        SELECT COUNT(*) FROM pallet_solucoes WHERE vale_pallet_id IS NOT NULL
    """)).scalar() or 0

    return documentos, solucoes


def listar_registros_fonte():
    """Lista todos os registros que serão migrados"""
    return db.session.execute(text("""
        SELECT
            id,
            nf_pallet,
            data_emissao,
            data_validade,
            quantidade,
            cnpj_cliente,
            nome_cliente,
            tipo_vale,
            posse_atual,
            cnpj_posse,
            nome_posse,
            cnpj_transportadora,
            nome_transportadora,
            pasta_arquivo,
            aba_arquivo,
            tipo_resolucao,
            responsavel_resolucao,
            cnpj_resolucao,
            valor_resolucao,
            nf_resolucao,
            recebido,
            recebido_em,
            recebido_por,
            enviado_coleta,
            enviado_coleta_em,
            enviado_coleta_por,
            resolvido,
            resolvido_em,
            resolvido_por,
            observacao,
            criado_em,
            criado_por
        FROM vale_pallets
        WHERE ativo = TRUE
        ORDER BY data_emissao, id
    """)).fetchall()


def ja_migrado(vale_pallet_id):
    """Verifica se um registro já foi migrado"""
    result = db.session.execute(text("""
        SELECT id FROM pallet_documentos WHERE vale_pallet_id = :id
    """), {'id': vale_pallet_id}).scalar()

    return result is not None


def limpar_registros_migrados():
    """Limpa os registros migrados (para --force)"""
    print("\n🗑️  Limpando registros migrados (--force)...")

    # Limpar na ordem correta (FK) - solucoes primeiro, depois documentos
    db.session.execute(text("DELETE FROM pallet_solucoes WHERE vale_pallet_id IS NOT NULL"))
    db.session.execute(text("DELETE FROM pallet_documentos WHERE vale_pallet_id IS NOT NULL"))
    db.session.commit()

    print("  ✅ Registros limpos")


def buscar_credito_por_nf(numero_nf):
    """
    Busca o PalletCredito correspondente ao número da NF.

    Fluxo: numero_nf → PalletNFRemessa → PalletCredito

    Args:
        numero_nf: Número da NF de remessa

    Returns:
        tuple: (credito_id, nf_remessa_id) ou (None, None)
    """
    # Buscar NF Remessa pelo número
    result = db.session.execute(text("""
        SELECT
            c.id as credito_id,
            nr.id as nf_remessa_id
        FROM pallet_nf_remessa nr
        JOIN pallet_creditos c ON c.nf_remessa_id = nr.id
        WHERE nr.numero_nf = :numero_nf
          AND nr.ativo = TRUE
          AND c.ativo = TRUE
        ORDER BY c.id
        LIMIT 1
    """), {'numero_nf': numero_nf}).fetchone()

    if result:
        return result.credito_id, result.nf_remessa_id

    return None, None


def migrar_registro(vale, dry_run=False, verbose=False):
    """
    Migra um único registro de ValePallet para os novos modelos.

    Args:
        vale: Registro de ValePallet (row result)
        dry_run: Se True, não executa, apenas mostra
        verbose: Se True, mostra detalhes

    Returns:
        tuple: (documento_id, solucao_id, status) ou (None, None, status) se dry_run
        status: 'OK', 'SEM_CREDITO', 'ERRO'
    """
    vale_id = vale.id
    numero_nf = vale.nf_pallet
    quantidade = vale.quantidade or 0

    # Buscar crédito correspondente
    credito_id, _ = buscar_credito_por_nf(numero_nf)

    if credito_id is None:
        if verbose:
            print(f"    ⚠️  Vale #{vale_id}: Crédito não encontrado para NF {numero_nf}")
        return None, None, 'SEM_CREDITO'

    # Determinar tipo de documento
    tipo_documento = TIPO_VALE_MAP.get(vale.tipo_vale, 'CANHOTO')

    # Dados do emissor
    cnpj_emissor = vale.cnpj_cliente or vale.cnpj_posse or ''
    nome_emissor = vale.nome_cliente or vale.nome_posse or ''

    if dry_run:
        msg = f"    DRY-RUN: Vale #{vale_id} | NF {numero_nf} | {tipo_documento} | {quantidade}un"
        if vale.resolvido:
            tipo_sol = TIPO_RESOLUCAO_MAP.get(vale.tipo_resolucao)
            msg += f" | RESOLVIDO ({tipo_sol})"
        print(msg)
        return None, None, 'OK'

    # 1. Criar PalletDocumento
    result = db.session.execute(text("""
        INSERT INTO pallet_documentos (
            credito_id,
            tipo,
            numero_documento,
            data_emissao,
            data_validade,
            quantidade,
            cnpj_emissor,
            nome_emissor,
            recebido,
            recebido_em,
            recebido_por,
            pasta_arquivo,
            aba_arquivo,
            vale_pallet_id,
            observacao,
            criado_em,
            criado_por,
            ativo
        ) VALUES (
            :credito_id,
            :tipo,
            :numero_documento,
            :data_emissao,
            :data_validade,
            :quantidade,
            :cnpj_emissor,
            :nome_emissor,
            :recebido,
            :recebido_em,
            :recebido_por,
            :pasta_arquivo,
            :aba_arquivo,
            :vale_pallet_id,
            :observacao,
            :criado_em,
            :criado_por,
            TRUE
        ) RETURNING id
    """), {
        'credito_id': credito_id,
        'tipo': tipo_documento,
        'numero_documento': numero_nf,
        'data_emissao': vale.data_emissao,
        'data_validade': vale.data_validade,
        'quantidade': quantidade,
        'cnpj_emissor': cnpj_emissor,
        'nome_emissor': nome_emissor,
        'recebido': vale.recebido or False,
        'recebido_em': vale.recebido_em,
        'recebido_por': vale.recebido_por,
        'pasta_arquivo': vale.pasta_arquivo,
        'aba_arquivo': vale.aba_arquivo,
        'vale_pallet_id': vale_id,
        'observacao': vale.observacao or f'Migrado de ValePallet #{vale_id}',
        'criado_em': vale.criado_em or datetime.now(),
        'criado_por': vale.criado_por or 'migracao_v2',
    })

    documento_id = result.scalar()
    solucao_id = None

    # 2. Se vale resolvido, criar PalletSolucao correspondente
    if vale.resolvido and vale.tipo_resolucao:
        tipo_solucao = TIPO_RESOLUCAO_MAP.get(vale.tipo_resolucao)

        if tipo_solucao:
            solucao_id = criar_solucao(
                vale=vale,
                credito_id=credito_id,
                tipo_solucao=tipo_solucao,
                quantidade=quantidade
            )

    if verbose:
        msg = f"    ✅ Vale #{vale_id} → Documento #{documento_id}"
        if solucao_id:
            msg += f" + Solução #{solucao_id}"
        print(msg)

    return documento_id, solucao_id, 'OK'


def criar_solucao(vale, credito_id, tipo_solucao, quantidade):
    """
    Cria uma PalletSolucao baseada nos dados do ValePallet resolvido.

    Args:
        vale: Registro de ValePallet
        credito_id: ID do PalletCredito
        tipo_solucao: 'VENDA' ou 'RECEBIMENTO'
        quantidade: Quantidade resolvida

    Returns:
        int: ID da solução criada
    """
    if tipo_solucao == 'VENDA':
        result = db.session.execute(text("""
            INSERT INTO pallet_solucoes (
                credito_id,
                tipo,
                quantidade,
                nf_venda,
                data_venda,
                valor_total,
                cnpj_comprador,
                nome_comprador,
                cnpj_responsavel,
                nome_responsavel,
                vale_pallet_id,
                observacao,
                criado_em,
                criado_por,
                ativo
            ) VALUES (
                :credito_id,
                'VENDA',
                :quantidade,
                :nf_venda,
                :data_venda,
                :valor_total,
                :cnpj_comprador,
                :nome_comprador,
                :cnpj_responsavel,
                :nome_responsavel,
                :vale_pallet_id,
                :observacao,
                :criado_em,
                :criado_por,
                TRUE
            ) RETURNING id
        """), {
            'credito_id': credito_id,
            'quantidade': quantidade,
            'nf_venda': vale.nf_resolucao,
            'data_venda': vale.resolvido_em.date() if vale.resolvido_em else None,
            'valor_total': vale.valor_resolucao,
            'cnpj_comprador': vale.cnpj_resolucao,
            'nome_comprador': vale.responsavel_resolucao,
            'cnpj_responsavel': vale.cnpj_resolucao,
            'nome_responsavel': vale.responsavel_resolucao,
            'vale_pallet_id': vale.id,
            'observacao': f'Migrado de ValePallet #{vale.id} (resolvido por venda)',
            'criado_em': vale.resolvido_em or datetime.now(),
            'criado_por': vale.resolvido_por or 'migracao_v2',
        })

    else:  # RECEBIMENTO
        result = db.session.execute(text("""
            INSERT INTO pallet_solucoes (
                credito_id,
                tipo,
                quantidade,
                data_recebimento,
                local_recebimento,
                recebido_de,
                cnpj_entregador,
                cnpj_responsavel,
                nome_responsavel,
                vale_pallet_id,
                observacao,
                criado_em,
                criado_por,
                ativo
            ) VALUES (
                :credito_id,
                'RECEBIMENTO',
                :quantidade,
                :data_recebimento,
                :local_recebimento,
                :recebido_de,
                :cnpj_entregador,
                :cnpj_responsavel,
                :nome_responsavel,
                :vale_pallet_id,
                :observacao,
                :criado_em,
                :criado_por,
                TRUE
            ) RETURNING id
        """), {
            'credito_id': credito_id,
            'quantidade': quantidade,
            'data_recebimento': vale.resolvido_em.date() if vale.resolvido_em else None,
            'local_recebimento': 'Nacom',
            'recebido_de': vale.responsavel_resolucao or vale.nome_transportadora,
            'cnpj_entregador': vale.cnpj_resolucao or vale.cnpj_transportadora,
            'cnpj_responsavel': vale.cnpj_resolucao or vale.cnpj_transportadora,
            'nome_responsavel': vale.responsavel_resolucao or vale.nome_transportadora,
            'vale_pallet_id': vale.id,
            'observacao': f'Migrado de ValePallet #{vale.id} (resolvido por coleta)',
            'criado_em': vale.resolvido_em or datetime.now(),
            'criado_por': vale.resolvido_por or 'migracao_v2',
        })

    return result.scalar()


def executar_migracao(dry_run=False, force=False, verbose=False):
    """Executa a migração completa"""
    print("=" * 70)
    print("  MIGRAÇÃO: ValePallet → PalletDocumento + PalletSolucao")
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
    doc_destino, sol_destino = contar_registros_destino()
    if doc_destino > 0 or sol_destino > 0:
        print(f"  ⚠️  Já migrados: {doc_destino} documentos, {sol_destino} soluções")

        if force:
            if not dry_run:
                limpar_registros_migrados()
        else:
            print("  ℹ️  Use --force para remigrar todos os registros")

    # 4. Listar e migrar registros
    registros = listar_registros_fonte()
    print(f"\n🔄 Iniciando migração de {len(registros)} registros...")

    migrados_ok = 0
    sem_credito = 0
    pulados = 0
    erros = 0
    solucoes_criadas = 0

    for vale in registros:
        try:
            # Verificar se já migrado (se não for force)
            if not force and not dry_run and ja_migrado(vale.id):
                pulados += 1
                continue

            _, sol_id, status = migrar_registro(vale, dry_run=dry_run, verbose=verbose)

            if status == 'OK':
                migrados_ok += 1
                if sol_id:
                    solucoes_criadas += 1

                # Commit a cada 100 registros
                if not dry_run and migrados_ok % 100 == 0:
                    db.session.commit()
                    print(f"  📦 Migrados {migrados_ok}/{total_fonte}...")

            elif status == 'SEM_CREDITO':
                sem_credito += 1

        except Exception as e:
            erros += 1
            print(f"  ❌ Erro no registro #{vale.id}: {e}")
            if not dry_run:
                db.session.rollback()

    # 5. Commit final
    if not dry_run:
        db.session.commit()

    # 6. Relatório final
    print("\n" + "=" * 70)
    print("  RELATÓRIO DE MIGRAÇÃO")
    print("=" * 70)
    print(f"  Total na fonte:       {total_fonte}")
    print(f"  Migrados (OK):        {migrados_ok}")
    print(f"  Sem crédito (NF):     {sem_credito}")
    print(f"  Pulados (já existem): {pulados}")
    print(f"  Erros:                {erros}")
    print(f"  Soluções criadas:     {solucoes_criadas}")

    if sem_credito > 0:
        print(f"\n  ⚠️  {sem_credito} vales não têm crédito correspondente.")
        print("     Execute script 002 primeiro ou verifique NFs faltantes.")

    if not dry_run:
        # Verificar contagens finais
        doc_final, sol_final = contar_registros_destino()
        print(f"\n  Tabelas finais:")
        print(f"    pallet_documentos:  {doc_final} registros")
        print(f"    pallet_solucoes:    {sol_final} registros (com vale_pallet_id)")

    print("=" * 70)

    return erros == 0


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Migra ValePallet para PalletDocumento + PalletSolucao'
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
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostra detalhes de cada registro migrado'
    )

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        try:
            sucesso = executar_migracao(
                dry_run=args.dry_run,
                force=args.force,
                verbose=args.verbose
            )

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
