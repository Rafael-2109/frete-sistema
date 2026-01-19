#!/usr/bin/env python3
"""
Script para reprocessar validacao IBS/CBS com nova regra de base de calculo.

CONTEXTO:
=========
A base de calculo do IBS/CBS foi corrigida para:
    Base IBS/CBS = Valor Total - ICMS - PIS - COFINS

Este script reprocessa todos os CTes que:
1. Ja foram validados anteriormente
2. Podem ter pendencias incorretas devido a regra antiga

MODOS DE EXECUCAO:
==================
1. DRY-RUN (padrao): Apenas simula e mostra o que seria feito
   python scripts/reprocessar_ibscbs.py

2. EXECUTAR: Aplica as alteracoes
   python scripts/reprocessar_ibscbs.py --executar

3. LIMITAR: Processar apenas N documentos (para teste)
   python scripts/reprocessar_ibscbs.py --limite 10

4. APENAS CTEs: Reprocessar apenas CTes
   python scripts/reprocessar_ibscbs.py --apenas-cte

5. VERBOSO: Mostrar detalhes de cada documento
   python scripts/reprocessar_ibscbs.py --verbose

EXEMPLOS:
=========
# Teste com 5 documentos
python scripts/reprocessar_ibscbs.py --limite 5 --verbose

# Executar reprocessamento completo
python scripts/reprocessar_ibscbs.py --executar

# Apenas CTes, modo verbose
python scripts/reprocessar_ibscbs.py --apenas-cte --executar --verbose

Autor: Sistema de Fretes
Data: 2026-01-19
"""

import sys
import os
import argparse
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.recebimento.models import PendenciaFiscalIbsCbs
from app.recebimento.services.validacao_ibscbs_service import validacao_ibscbs_service
from app.odoo.models import ConhecimentoTransporte
from app.odoo.utils.cte_xml_parser import CTeXMLParser


def reprocessar_ctes(dry_run: bool = True, limite: int = None, verbose: bool = False):
    """
    Reprocessa CTes com a nova regra de base IBS/CBS.

    Estrategia:
    1. Buscar todas as pendencias de CTe que estao 'pendente'
    2. Para cada CTe, revalidar com a nova regra
    3. Se passar na nova validacao, remover pendencia
    4. Se continuar com divergencia, atualizar detalhes

    Args:
        dry_run: Se True, apenas simula sem alterar dados
        limite: Numero maximo de documentos a processar
        verbose: Se True, mostra detalhes de cada documento

    Returns:
        Dict com estatisticas do processamento
    """
    stats = {
        'total_pendencias': 0,
        'reprocessados': 0,
        'resolvidos': 0,
        'mantidos': 0,
        'erros': 0,
        'sem_xml': 0,
        'detalhes': []
    }

    print("\n" + "="*70)
    print("REPROCESSAMENTO IBS/CBS - CTes")
    print("="*70)
    print(f"Modo: {'DRY-RUN (simulacao)' if dry_run else 'EXECUCAO REAL'}")
    print(f"Limite: {limite if limite else 'Sem limite'}")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

    # Buscar pendencias de CTe pendentes
    query = PendenciaFiscalIbsCbs.query.filter_by(
        tipo_documento='CTe',
        status='pendente'
    )

    if limite:
        query = query.limit(limite)

    pendencias = query.all()
    stats['total_pendencias'] = len(pendencias)

    print(f"Encontradas {len(pendencias)} pendencias de CTe para reprocessar\n")

    for i, pendencia in enumerate(pendencias, 1):
        try:
            if verbose:
                print(f"\n[{i}/{len(pendencias)}] CTe {pendencia.numero_documento}")
                print(f"  Chave: {pendencia.chave_acesso}")
                print(f"  Motivo atual: {pendencia.motivo_pendencia}")
                print(f"  Detalhes: {pendencia.detalhes_pendencia}")

            # Buscar CTe original
            cte = None
            if pendencia.cte_id:
                cte = ConhecimentoTransporte.query.get(pendencia.cte_id)

            if not cte:
                # Tentar buscar pela chave de acesso
                cte = ConhecimentoTransporte.query.filter_by(
                    chave_cte=pendencia.chave_acesso
                ).first()

            if not cte:
                if verbose:
                    print(f"  ⚠️  CTe nao encontrado no banco")
                stats['erros'] += 1
                stats['detalhes'].append({
                    'chave': pendencia.chave_acesso,
                    'erro': 'CTe nao encontrado'
                })
                continue

            # Obter XML do CTe
            xml_content = validacao_ibscbs_service._obter_xml_cte(cte)

            if not xml_content:
                if verbose:
                    print(f"  ⚠️  XML nao disponivel")
                stats['sem_xml'] += 1
                stats['detalhes'].append({
                    'chave': pendencia.chave_acesso,
                    'erro': 'XML nao disponivel'
                })
                continue

            # Revalidar com nova regra
            parser = CTeXMLParser(xml_content)
            ibscbs = parser.get_ibscbs()
            impostos = parser.get_impostos()

            if verbose:
                print(f"  Impostos extraidos: ICMS={impostos.get('valor_icms')}, PIS={impostos.get('valor_pis')}, COFINS={impostos.get('valor_cofins')}")

            # Validar com impostos
            divergencias = validacao_ibscbs_service._validar_campos_cte(ibscbs, cte, impostos)

            stats['reprocessados'] += 1

            if not divergencias:
                # PASSOU na nova validacao - remover pendencia
                if verbose:
                    print(f"  ✅ RESOLVIDO - Passou na nova validacao")

                stats['resolvidos'] += 1
                stats['detalhes'].append({
                    'chave': pendencia.chave_acesso,
                    'numero': pendencia.numero_documento,
                    'acao': 'RESOLVIDO',
                    'motivo_anterior': pendencia.motivo_pendencia,
                    'detalhes_anterior': pendencia.detalhes_pendencia
                })

                if not dry_run:
                    # Marcar como resolvido ao inves de deletar (para historico)
                    pendencia.status = 'aprovado'
                    pendencia.resolucao = 'reprocessamento_regra_corrigida'
                    pendencia.justificativa = f"Reprocessado em {datetime.now().strftime('%Y-%m-%d %H:%M')} - Base IBS/CBS corrigida para Valor - ICMS - PIS - COFINS"
                    pendencia.resolvido_por = 'sistema_reprocessamento'
                    pendencia.resolvido_em = datetime.utcnow()
            else:
                # Continua com divergencias
                if verbose:
                    print(f"  ❌ MANTIDO - Divergencias: {divergencias}")

                stats['mantidos'] += 1

                detalhes_novos = "; ".join(divergencias)
                mudou = pendencia.detalhes_pendencia != detalhes_novos

                stats['detalhes'].append({
                    'chave': pendencia.chave_acesso,
                    'numero': pendencia.numero_documento,
                    'acao': 'MANTIDO' + (' (detalhes atualizados)' if mudou else ''),
                    'divergencias': divergencias
                })

                if not dry_run and mudou:
                    # Atualizar detalhes da pendencia
                    pendencia.detalhes_pendencia = detalhes_novos

        except Exception as e:
            stats['erros'] += 1
            if verbose:
                print(f"  ❌ ERRO: {str(e)}")
            stats['detalhes'].append({
                'chave': pendencia.chave_acesso if pendencia else 'N/A',
                'erro': str(e)
            })

    if not dry_run:
        db.session.commit()
        print("\n✅ Alteracoes salvas no banco de dados")

    return stats


def reprocessar_todos_ctes_regime_normal(dry_run: bool = True, limite: int = None, verbose: bool = False):
    """
    Reprocessa TODOS os CTes de regime normal (CRT=3), independente de ter pendencia.

    Util para:
    - Garantir que todos os CTes foram validados com a regra correta
    - Criar novas pendencias se necessario

    Args:
        dry_run: Se True, apenas simula
        limite: Limite de documentos
        verbose: Modo verboso

    Returns:
        Dict com estatisticas
    """
    stats = {
        'total_ctes': 0,
        'reprocessados': 0,
        'ja_ok': 0,
        'nova_pendencia': 0,
        'pendencia_resolvida': 0,
        'sem_xml': 0,
        'erros': 0
    }

    print("\n" + "="*70)
    print("REPROCESSAMENTO COMPLETO - CTes Regime Normal")
    print("="*70)
    print(f"Modo: {'DRY-RUN (simulacao)' if dry_run else 'EXECUCAO REAL'}")
    print(f"Limite: {limite if limite else 'Sem limite'}")
    print("="*70 + "\n")

    # Buscar CTes de regime normal (aproximacao: CNPJ de fornecedores conhecidos)
    # Ou buscar todos os CTes recentes para revalidar
    query = ConhecimentoTransporte.query.filter(
        ConhecimentoTransporte.valor_total > 0
    ).order_by(ConhecimentoTransporte.data_emissao.desc())

    if limite:
        query = query.limit(limite)

    ctes = query.all()
    stats['total_ctes'] = len(ctes)

    print(f"Encontrados {len(ctes)} CTes para reprocessar\n")

    for i, cte in enumerate(ctes, 1):
        try:
            if verbose:
                print(f"\n[{i}/{len(ctes)}] CTe {cte.numero_cte}")

            # Verificar se ja tem pendencia
            pendencia_existente = PendenciaFiscalIbsCbs.query.filter_by(
                chave_acesso=cte.chave_cte,
                status='pendente'
            ).first()

            # Revalidar
            valido, pendencia, msg = validacao_ibscbs_service.validar_cte(cte)

            stats['reprocessados'] += 1

            if valido:
                stats['ja_ok'] += 1
                if pendencia_existente and not dry_run:
                    # Tinha pendencia mas agora passou - resolver
                    pendencia_existente.status = 'aprovado'
                    pendencia_existente.resolucao = 'reprocessamento_regra_corrigida'
                    pendencia_existente.justificativa = f"Reprocessado em {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    pendencia_existente.resolvido_por = 'sistema_reprocessamento'
                    pendencia_existente.resolvido_em = datetime.utcnow()
                    stats['pendencia_resolvida'] += 1
                    if verbose:
                        print(f"  ✅ OK - Pendencia anterior resolvida")
                elif verbose:
                    print(f"  ✅ OK")
            else:
                if pendencia_existente:
                    # Ja tinha pendencia - manter/atualizar
                    if verbose:
                        print(f"  ⚠️  Pendencia mantida: {msg}")
                else:
                    # Nova pendencia criada
                    stats['nova_pendencia'] += 1
                    if verbose:
                        print(f"  ⚠️  Nova pendencia: {msg}")
                    if not dry_run and pendencia:
                        db.session.add(pendencia)

        except Exception as e:
            stats['erros'] += 1
            if verbose:
                print(f"  ❌ Erro: {str(e)}")

    if not dry_run:
        db.session.commit()
        print("\n✅ Alteracoes salvas")

    return stats


def imprimir_resumo(stats: dict, modo: str):
    """Imprime resumo do processamento"""
    print("\n" + "="*70)
    print("RESUMO DO PROCESSAMENTO")
    print("="*70)
    print(f"Modo: {modo}")
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*70)

    for chave, valor in stats.items():
        if chave != 'detalhes':
            print(f"  {chave.replace('_', ' ').title()}: {valor}")

    print("="*70)

    # Se houver resolvidos, listar
    if 'detalhes' in stats:
        resolvidos = [d for d in stats['detalhes'] if d.get('acao', '').startswith('RESOLVIDO')]
        if resolvidos:
            print(f"\n📋 PENDENCIAS RESOLVIDAS ({len(resolvidos)}):")
            print("-"*50)
            for d in resolvidos[:20]:  # Limitar a 20 para nao poluir
                print(f"  - CTe {d.get('numero', 'N/A')}: {d.get('motivo_anterior', 'N/A')}")
            if len(resolvidos) > 20:
                print(f"  ... e mais {len(resolvidos) - 20} documentos")


def main():
    parser = argparse.ArgumentParser(
        description='Reprocessa validacao IBS/CBS com nova regra de base de calculo'
    )
    parser.add_argument(
        '--executar',
        action='store_true',
        help='Executa as alteracoes (padrao: dry-run)'
    )
    parser.add_argument(
        '--limite',
        type=int,
        default=None,
        help='Limita o numero de documentos processados'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostra detalhes de cada documento'
    )
    parser.add_argument(
        '--apenas-cte',
        action='store_true',
        help='Processa apenas CTes (padrao)'
    )
    parser.add_argument(
        '--revalidar-todos',
        action='store_true',
        help='Revalida todos os CTes, nao apenas pendencias'
    )

    args = parser.parse_args()

    dry_run = not args.executar

    # Criar aplicacao Flask
    app = create_app()

    with app.app_context():
        try:
            if args.revalidar_todos:
                stats = reprocessar_todos_ctes_regime_normal(
                    dry_run=dry_run,
                    limite=args.limite,
                    verbose=args.verbose
                )
                modo = "REVALIDACAO COMPLETA"
            else:
                stats = reprocessar_ctes(
                    dry_run=dry_run,
                    limite=args.limite,
                    verbose=args.verbose
                )
                modo = "REPROCESSAMENTO DE PENDENCIAS"

            imprimir_resumo(stats, modo)

            if dry_run:
                print("\n⚠️  MODO DRY-RUN: Nenhuma alteracao foi salva.")
                print("    Para aplicar as alteracoes, execute com --executar")

        except Exception as e:
            print(f"\n❌ Erro fatal: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()
