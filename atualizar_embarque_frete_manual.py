#!/usr/bin/env python3
"""
Script para atualizar manualmente Embarque e Frete de NFs específicas
Uso: python atualizar_embarque_frete_manual.py
"""

from app import create_app, db
from app.faturamento.services.atualizar_peso_service import AtualizadorPesoService

app = create_app()

with app.app_context():
    print("=" * 80)
    print("🔄 ATUALIZANDO EMBARQUE E FRETE DE NFs ESPECÍFICAS")
    print("=" * 80)

    # Pedir NFs interativamente
    print("\nDigite os números das NFs (separados por vírgula ou espaço)")
    print("Exemplo: 140050, 136036")
    print("Ou pressione ENTER para sair")
    print("-" * 80)

    entrada = input("NFs: ").strip()

    if not entrada:
        print("\n❌ Nenhuma NF informada. Saindo...")
        exit(0)

    # Processar entrada (aceita vírgula ou espaço como separador)
    NFS_PARA_ATUALIZAR = []
    for item in entrada.replace(',', ' ').split():
        nf = item.strip()
        if nf:
            NFS_PARA_ATUALIZAR.append(nf)

    if not NFS_PARA_ATUALIZAR:
        print("\n❌ Nenhuma NF válida informada. Saindo...")
        exit(0)

    print(f"\n✅ NFs a processar: {', '.join(NFS_PARA_ATUALIZAR)}")
    print(f"Total: {len(NFS_PARA_ATUALIZAR)} NF(s)")
    print("-" * 80)

    service = AtualizadorPesoService()

    for numero_nf in NFS_PARA_ATUALIZAR:
        print(f"\n{'='*80}")
        print(f"📦 Processando NF: {numero_nf}")
        print(f"{'='*80}")

        try:
            # Atualizar apenas EmbarqueItem, Embarque e Frete
            # (pulando FaturamentoProduto e RelatorioFaturamento)

            print(f"\n1️⃣ Atualizando EmbarqueItem...")
            resultado_embarque_item = service._atualizar_embarque_item(numero_nf)
            print(f"   ✅ Resultado: {resultado_embarque_item}")

            print(f"\n2️⃣ Atualizando Embarque (totais)...")
            resultado_embarque = service._atualizar_embarque_totais(numero_nf)
            print(f"   ✅ Resultado: {resultado_embarque}")

            print(f"\n3️⃣ Atualizando Frete...")
            resultado_frete = service._atualizar_frete(numero_nf)
            print(f"   ✅ Resultado: {resultado_frete}")

            # Commit das mudanças
            db.session.commit()
            print(f"\n✅ NF {numero_nf} atualizada com sucesso!")

        except Exception as e:
            print(f"\n❌ Erro ao atualizar NF {numero_nf}: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print("✅ PROCESSO CONCLUÍDO")
    print(f"{'='*80}")
