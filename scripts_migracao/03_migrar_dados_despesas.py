"""
SCRIPT 3: Migrar dados existentes - Vincular despesas às faturas
Objetivo: Preencher fatura_frete_id para as 829 despesas existentes
Executar: LOCALMENTE (equivalente ao SQL para Render)
Data: 2025-01-23
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.fretes.models import DespesaExtra, FaturaFrete
from sqlalchemy import text

def migrar_dados_despesas():
    """Migra despesas existentes para usar FK em vez de observações"""

    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("MIGRAÇÃO DE DADOS: DespesaExtra → FaturaFrete (FK)")
        print("=" * 80)
        print()

        # Estatísticas iniciais
        total_despesas = DespesaExtra.query.count()
        despesas_com_fatura_obs = DespesaExtra.query.filter(
            DespesaExtra.observacoes.ilike('%Fatura:%')
        ).count()

        print(f"📊 ESTATÍSTICAS INICIAIS:")
        print(f"   Total de despesas: {total_despesas}")
        print(f"   Despesas com 'Fatura:' nas observações: {despesas_com_fatura_obs}")
        print()

        # ========================================================================
        # ETAPA 1: Migração de casos com MATCH ÚNICO
        # ========================================================================
        print("=" * 80)
        print("ETAPA 1: Migrando casos com MATCH ÚNICO")
        print("=" * 80)
        print()

        despesas_atualizadas_etapa1 = 0

        # Busca despesas que têm "Fatura:" nas observações e ainda não têm FK
        despesas_para_migrar = DespesaExtra.query.filter(
            DespesaExtra.observacoes.ilike('%Fatura:%'),
            DespesaExtra.fatura_frete_id.is_(None)
        ).all()

        print(f"Despesas para processar: {len(despesas_para_migrar)}")
        print()

        for despesa in despesas_para_migrar:
            try:
                # Extrai número da fatura das observações
                numero_fatura_extraido = None
                if despesa.observacoes and 'Fatura:' in despesa.observacoes:
                    partes = despesa.observacoes.split('Fatura:')
                    if len(partes) > 1:
                        numero_fatura_extraido = partes[1].split('|')[0].strip()

                if not numero_fatura_extraido:
                    print(f"  ⚠️ Despesa #{despesa.id}: Não foi possível extrair número da fatura")
                    continue

                # Busca faturas com esse número (match exato)
                faturas_encontradas = FaturaFrete.query.filter_by(
                    numero_fatura=numero_fatura_extraido
                ).all()

                # ETAPA 1: Só migra se encontrar exatamente 1 fatura
                if len(faturas_encontradas) == 1:
                    despesa.fatura_frete_id = faturas_encontradas[0].id
                    despesas_atualizadas_etapa1 += 1

                    if despesas_atualizadas_etapa1 % 50 == 0:
                        print(f"  ✅ Processadas: {despesas_atualizadas_etapa1} despesas...")

            except Exception as e:
                print(f"  ❌ Erro ao processar despesa #{despesa.id}: {str(e)}")

        # Commit ETAPA 1
        try:
            db.session.commit()
            print()
            print(f"✅ ETAPA 1 CONCLUÍDA: {despesas_atualizadas_etapa1} despesas atualizadas")
            print()
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERRO ao commitar ETAPA 1: {str(e)}")
            return

        # ========================================================================
        # ETAPA 2: Migração de casos com MÚLTIPLOS MATCHES
        # Estratégia: Escolher fatura com ID MENOR (mais antiga)
        # ========================================================================
        print("=" * 80)
        print("ETAPA 2: Migrando casos com MÚLTIPLOS MATCHES")
        print("=" * 80)
        print()

        despesas_atualizadas_etapa2 = 0

        # Busca despesas que ainda não têm FK
        despesas_restantes = DespesaExtra.query.filter(
            DespesaExtra.observacoes.ilike('%Fatura:%'),
            DespesaExtra.fatura_frete_id.is_(None)
        ).all()

        print(f"Despesas restantes para processar: {len(despesas_restantes)}")
        print()

        for despesa in despesas_restantes:
            try:
                # Extrai número da fatura das observações
                numero_fatura_extraido = None
                if despesa.observacoes and 'Fatura:' in despesa.observacoes:
                    partes = despesa.observacoes.split('Fatura:')
                    if len(partes) > 1:
                        numero_fatura_extraido = partes[1].split('|')[0].strip()

                if not numero_fatura_extraido:
                    continue

                # Busca faturas com esse número
                faturas_encontradas = FaturaFrete.query.filter_by(
                    numero_fatura=numero_fatura_extraido
                ).order_by(FaturaFrete.id).all()

                # Se encontrou múltiplas, escolhe a mais antiga (ID menor)
                if len(faturas_encontradas) > 1:
                    despesa.fatura_frete_id = faturas_encontradas[0].id  # ID menor
                    despesas_atualizadas_etapa2 += 1
                    print(f"  ⚠️ Despesa #{despesa.id}: {len(faturas_encontradas)} faturas encontradas → Escolhida fatura #{faturas_encontradas[0].id} (mais antiga)")
                elif len(faturas_encontradas) == 1:
                    # Caso raro: deveria ter sido pego na ETAPA 1
                    despesa.fatura_frete_id = faturas_encontradas[0].id
                    despesas_atualizadas_etapa2 += 1
                else:
                    print(f"  ❌ Despesa #{despesa.id}: Fatura '{numero_fatura_extraido}' não encontrada")

            except Exception as e:
                print(f"  ❌ Erro ao processar despesa #{despesa.id}: {str(e)}")

        # Commit ETAPA 2
        try:
            db.session.commit()
            print()
            print(f"✅ ETAPA 2 CONCLUÍDA: {despesas_atualizadas_etapa2} despesas atualizadas")
            print()
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERRO ao commitar ETAPA 2: {str(e)}")
            return

        # ========================================================================
        # RELATÓRIO FINAL
        # ========================================================================
        print("=" * 80)
        print("RELATÓRIO FINAL DE MIGRAÇÃO")
        print("=" * 80)
        print()

        # Estatísticas finais
        despesas_migradas = DespesaExtra.query.filter(
            DespesaExtra.fatura_frete_id.isnot(None)
        ).count()

        despesas_nao_migradas = DespesaExtra.query.filter(
            DespesaExtra.observacoes.ilike('%Fatura:%'),
            DespesaExtra.fatura_frete_id.is_(None)
        ).count()

        percentual_sucesso = (despesas_migradas / despesas_com_fatura_obs * 100) if despesas_com_fatura_obs > 0 else 0

        print(f"📊 RESULTADOS:")
        print(f"   Total de despesas: {total_despesas}")
        print(f"   Despesas com 'Fatura:' nas observações: {despesas_com_fatura_obs}")
        print(f"   Despesas migradas: {despesas_migradas}")
        print(f"   Despesas não migradas: {despesas_nao_migradas}")
        print(f"   Percentual de sucesso: {percentual_sucesso:.2f}%")
        print()

        if despesas_nao_migradas > 0:
            print("⚠️ DESPESAS NÃO MIGRADAS (primeiras 10):")
            print("-" * 80)

            despesas_falhas = DespesaExtra.query.filter(
                DespesaExtra.observacoes.ilike('%Fatura:%'),
                DespesaExtra.fatura_frete_id.is_(None)
            ).limit(10).all()

            for despesa in despesas_falhas:
                numero_extraido = "N/A"
                if despesa.observacoes and 'Fatura:' in despesa.observacoes:
                    try:
                        numero_extraido = despesa.observacoes.split('Fatura:')[1].split('|')[0].strip()
                    except:
                        pass

                print(f"   Despesa #{despesa.id}: Fatura '{numero_extraido}'")
            print()

        # Validação: Comparar método antigo vs novo
        print("=" * 80)
        print("VALIDAÇÃO: Método Antigo vs Novo (primeiras 5 faturas)")
        print("=" * 80)
        print()

        faturas_com_despesas = FaturaFrete.query.join(
            DespesaExtra, DespesaExtra.fatura_frete_id == FaturaFrete.id
        ).distinct().limit(5).all()

        for fatura in faturas_com_despesas:
            # Método ANTIGO (LIKE - problemático)
            despesas_antigo = DespesaExtra.query.filter(
                DespesaExtra.observacoes.ilike(f'%Fatura: {fatura.numero_fatura}%')
            ).count()

            # Método NOVO (FK - correto)
            despesas_novo = DespesaExtra.query.filter_by(
                fatura_frete_id=fatura.id
            ).count()

            diferenca = despesas_antigo - despesas_novo
            status = "✅ OK" if diferenca == 0 else f"⚠️ DIFF: {diferenca}"

            print(f"   Fatura #{fatura.id} ({fatura.numero_fatura}):")
            print(f"      Método antigo (LIKE): {despesas_antigo}")
            print(f"      Método novo (FK): {despesas_novo}")
            print(f"      Status: {status}")
            print()

        # Mensagem final
        print("=" * 80)
        if percentual_sucesso == 100:
            print("✅ MIGRAÇÃO 100% COMPLETA!")
        elif percentual_sucesso >= 99:
            print("✅ MIGRAÇÃO >99% COMPLETA (ACEITÁVEL)")
        elif percentual_sucesso >= 95:
            print("⚠️ MIGRAÇÃO >95% (REVISAR PENDENTES)")
        else:
            print("❌ MIGRAÇÃO INCOMPLETA (INVESTIGAR)")
        print("=" * 80)
        print()

        print("PRÓXIMOS PASSOS:")
        print("1. Executar script 04_validar_migracao.sql no Render")
        print("2. Fazer commit do código atualizado")
        print("3. Deploy em produção")
        print()

if __name__ == '__main__':
    migrar_dados_despesas()
