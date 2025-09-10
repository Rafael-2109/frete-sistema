#!/usr/bin/env python3
"""
Script de Migração - Sincronização de Status da Separação
===========================================================

Este script corrige divergências entre o campo 'status' persistido
e o valor calculado por 'status_calculado' em todos os registros
da tabela Separacao.

Execução:
    python scripts/sincronizar_status_separacao.py [--dry-run] [--verbose]

Opções:
    --dry-run   : Simula a execução sem alterar o banco
    --verbose   : Mostra detalhes de cada alteração
    --limit N   : Processa apenas N registros (para teste)
"""

import sys
import os
import argparse

# Adicionar o diretório pai ao path para importar a aplicação
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.separacao.models import Separacao


def calcular_status_correto(sep):
    """
    Calcula o status correto baseado nos campos da separação.
    Replica a lógica do @property status_calculado.
    """
    # REGRA 1: PREVISAO é manual, não alterar
    if sep.status == 'PREVISAO':
        return 'PREVISAO'
    
    # REGRA 2: NF no CD tem prioridade máxima
    if getattr(sep, 'nf_cd', False):
        return 'NF no CD'
    
    # REGRA 3: FATURADO - tem NF
    if sep.sincronizado_nf or (sep.numero_nf and str(sep.numero_nf).strip()):
        return 'FATURADO'
    
    # REGRA 4: EMBARCADO - tem data de embarque
    if sep.data_embarque:
        return 'EMBARCADO'
    
    # REGRA 5: COTADO - tem cotação
    if sep.cotacao_id:
        return 'COTADO'
    
    # REGRA 6: ABERTO - estado padrão
    return 'ABERTO'


def sincronizar_status(dry_run=False, verbose=False, limit=None):
    """
    Sincroniza o campo status com o valor calculado.
    
    Args:
        dry_run: Se True, não faz alterações no banco
        verbose: Se True, mostra detalhes de cada alteração
        limit: Limita o número de registros processados
    
    Returns:
        Tupla (total_processados, total_corrigidos, erros)
    """
    
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("SINCRONIZAÇÃO DE STATUS - SEPARAÇÃO")
        print("="*60)
        print(f"Modo: {'SIMULAÇÃO' if dry_run else 'EXECUÇÃO'}")
        print(f"Verbose: {'SIM' if verbose else 'NÃO'}")
        if limit:
            print(f"Limite: {limit} registros")
        print("="*60 + "\n")
        
        # Estatísticas
        total_processados = 0
        total_corrigidos = 0
        erros = []
        
        # Contadores por tipo de correção
        correcoes = {
            'ABERTO→COTADO': 0,
            'ABERTO→EMBARCADO': 0,
            'ABERTO→FATURADO': 0,
            'COTADO→ABERTO': 0,
            'COTADO→EMBARCADO': 0,
            'COTADO→FATURADO': 0,
            'EMBARCADO→ABERTO': 0,
            'EMBARCADO→COTADO': 0,
            'EMBARCADO→FATURADO': 0,
            'FATURADO→ABERTO': 0,
            'FATURADO→COTADO': 0,
            'FATURADO→EMBARCADO': 0,
            'NF no CD→FATURADO': 0,
            'OUTROS': 0
        }
        
        # Query base - ignora PREVISAO
        query = Separacao.query.filter(
            Separacao.status != 'PREVISAO'
        )
        
        if limit:
            query = query.limit(limit)
        
        # Processar em lotes para melhor performance
        batch_size = 100
        offset = 0
        
        while True:
            batch = query.offset(offset).limit(batch_size).all()
            if not batch:
                break
            
            for sep in batch:
                try:
                    total_processados += 1
                    
                    # Calcular status correto
                    status_atual = sep.status
                    status_correto = calcular_status_correto(sep)
                    
                    # Verificar se precisa correção
                    if status_atual != status_correto:
                        total_corrigidos += 1
                        
                        # Registrar tipo de correção
                        chave_correcao = f"{status_atual}→{status_correto}"
                        if chave_correcao in correcoes:
                            correcoes[chave_correcao] += 1
                        else:
                            correcoes['OUTROS'] += 1
                        
                        if verbose:
                            print(f"[{total_processados}] Separação {sep.id} (Lote: {sep.separacao_lote_id}, Pedido: {sep.num_pedido})")
                            print(f"    Status atual: {status_atual}")
                            print(f"    Status correto: {status_correto}")
                            print(f"    Motivo: ", end="")
                            
                            if status_correto == 'NF no CD':
                                print(f"nf_cd=True")
                            elif status_correto == 'FATURADO':
                                print(f"sincronizado_nf={sep.sincronizado_nf}, numero_nf='{sep.numero_nf}'")
                            elif status_correto == 'EMBARCADO':
                                print(f"data_embarque={sep.data_embarque}")
                            elif status_correto == 'COTADO':
                                print(f"cotacao_id={sep.cotacao_id}")
                            else:
                                print("Sem vínculos")
                        
                        # Aplicar correção
                        if not dry_run:
                            sep.status = status_correto
                    
                    # Mostrar progresso
                    if total_processados % 100 == 0:
                        print(f"Processados: {total_processados} | Corrigidos: {total_corrigidos}")
                
                except Exception as e:
                    erros.append({
                        'id': sep.id,
                        'erro': str(e)
                    })
                    if verbose:
                        print(f"❌ Erro ao processar Separação {sep.id}: {e}")
            
            # Commit do lote
            if not dry_run and total_corrigidos > 0:
                try:
                    db.session.commit()
                    print(f"✅ Lote commitado: {offset} a {offset + batch_size}")
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Erro ao commitar lote: {e}")
                    erros.append({
                        'lote': f"{offset}-{offset + batch_size}",
                        'erro': str(e)
                    })
            
            offset += batch_size
        
        # Relatório final
        print("\n" + "="*60)
        print("RELATÓRIO FINAL")
        print("="*60)
        print(f"Total processados: {total_processados}")
        print(f"Total corrigidos: {total_corrigidos}")
        print(f"Taxa de correção: {(total_corrigidos/total_processados*100 if total_processados > 0 else 0):.2f}%")
        print(f"Erros encontrados: {len(erros)}")
        
        if total_corrigidos > 0:
            print("\n📊 DETALHAMENTO DAS CORREÇÕES:")
            print("-"*40)
            for tipo, qtd in sorted(correcoes.items(), key=lambda x: x[1], reverse=True):
                if qtd > 0:
                    print(f"  {tipo:.<30} {qtd:>5} ({qtd/total_corrigidos*100:.1f}%)")
        
        if erros and verbose:
            print("\n❌ ERROS DETALHADOS:")
            print("-"*40)
            for erro in erros[:10]:  # Mostrar apenas primeiros 10 erros
                print(f"  {erro}")
        
        if dry_run:
            print("\n⚠️  MODO SIMULAÇÃO - Nenhuma alteração foi feita no banco!")
        else:
            print(f"\n✅ Sincronização concluída! {total_corrigidos} registros atualizados.")
        
        print("="*60 + "\n")
        
        return total_processados, total_corrigidos, erros


def validar_integridade():
    """
    Valida a integridade após a migração, verificando se
    status = status_calculado para todos os registros.
    """
    app = create_app()
    
    with app.app_context():
        print("\n🔍 VALIDANDO INTEGRIDADE...")
        
        # Contar divergências
        divergencias = 0
        total = 0
        
        for sep in Separacao.query.filter(Separacao.status != 'PREVISAO').yield_per(100):
            total += 1
            status_calculado = calcular_status_correto(sep)
            if sep.status != status_calculado:
                divergencias += 1
                print(f"⚠️  Divergência: Separação {sep.id} - status={sep.status}, calculado={status_calculado}")
        
        if divergencias == 0:
            print(f"✅ INTEGRIDADE OK! Todos os {total} registros estão sincronizados.")
        else:
            print(f"❌ ENCONTRADAS {divergencias} DIVERGÊNCIAS em {total} registros!")
        
        return divergencias == 0


def main():
    """Função principal do script."""
    
    parser = argparse.ArgumentParser(
        description='Sincroniza o campo status com status_calculado na tabela Separacao'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Simula a execução sem alterar o banco'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Mostra detalhes de cada alteração'
    )
    parser.add_argument(
        '--limit', 
        type=int,
        help='Limita o número de registros processados'
    )
    parser.add_argument(
        '--validate', 
        action='store_true',
        help='Apenas valida a integridade sem fazer correções'
    )
    
    args = parser.parse_args()
    
    try:
        if args.validate:
            # Modo validação
            sucesso = validar_integridade()
            sys.exit(0 if sucesso else 1)
        else:
            # Modo sincronização
            total, corrigidos, erros = sincronizar_status(
                dry_run=args.dry_run,
                verbose=args.verbose,
                limit=args.limit
            )
            
            # Validar após sincronização (se não for dry-run)
            if not args.dry_run and corrigidos > 0:
                print("\n" + "="*60)
                validar_integridade()
            
            sys.exit(0 if len(erros) == 0 else 1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()