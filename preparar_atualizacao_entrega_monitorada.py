#!/usr/bin/env python3
"""
📊 PREPARAR ATUALIZAÇÕES DA ENTREGA MONITORADA

Este script permite atualizar informações da EntregaMonitorada baseado numa planilha Excel.

ATUALIZAÇÕES SUPORTADAS:
a) Data de embarque, data de entrega prevista e data da agenda
b) Flag de "Cancelada" e "Devolvida" (através do status_finalizacao)
c) Criar Agendamento com "Protocolo" e "Data Agendada"
d) Criar Acompanhamento com "Tipo" = Informação e "Descrição"

ESTRUTURA DA PLANILHA:
- numero_nf (obrigatório)
- data_embarque (opcional)
- data_entrega_prevista (opcional)
- data_agenda (opcional)
- status_finalizacao (opcional: 'Cancelada', 'Devolvida', etc.)
- protocolo_agendamento (opcional)
- data_agendamento (opcional)
- acompanhamento_descricao (opcional)

Uso: python preparar_atualizacao_entrega_monitorada.py arquivo.xlsx [--sheet=Nome] [--dry-run] [--confirmar]
"""

import sys
import os
import pandas as pd
import argparse
from datetime import datetime, date

# Adiciona o diretório pai ao Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega, RegistroLogEntrega

def converter_data_segura(valor):
    """Converte valor para data de forma segura"""
    if pd.isna(valor) or valor is None:
        return None
    
    if isinstance(valor, (date, datetime)):
        return valor.date() if isinstance(valor, datetime) else valor
    
    # Tenta converter string
    valor_str = str(valor).strip()
    if valor_str.lower() in ['', 'nan', 'nat', '-', 'none']:
        return None
    
    try:
        # Tenta formato brasileiro
        if '/' in valor_str:
            return datetime.strptime(valor_str, '%d/%m/%Y').date()
        # Tenta formato ISO
        elif '-' in valor_str:
            return datetime.strptime(valor_str[:10], '%Y-%m-%d').date()
    except:
        pass
    
    return None

def preparar_atualizacao_entrega_monitorada(arquivo_excel, sheet_name='Sheet1', dry_run=True, confirmar=False):
    """
    Processa planilha e atualiza EntregaMonitorada
    """
    app = create_app()
    
    with app.app_context():
        print("📊 PREPARAR ATUALIZAÇÕES DA ENTREGA MONITORADA")
        print("=" * 60)
        
        # Carrega planilha
        try:
            df = pd.read_excel(arquivo_excel, sheet_name=sheet_name)
            print(f"✅ Planilha carregada: {len(df)} linhas")
        except Exception as e:
            print(f"❌ Erro ao carregar planilha: {e}")
            return
        
        # Verifica colunas obrigatórias
        if 'numero_nf' not in df.columns:
            print("❌ Coluna 'numero_nf' não encontrada na planilha")
            return
        
        # Mostra colunas disponíveis
        print(f"\n📋 COLUNAS ENCONTRADAS:")
        for col in df.columns:
            print(f"   • {col}")
        
        # Mapeia colunas opcionais
        colunas_opcionais = {
            'data_embarque': 'data_embarque',
            'data_entrega_prevista': 'data_entrega_prevista', 
            'data_agenda': 'data_agenda',
            'status_finalizacao': 'status_finalizacao',
            'protocolo_agendamento': 'protocolo_agendamento',
            'data_agendamento': 'data_agendamento',
            'acompanhamento_descricao': 'acompanhamento_descricao'
        }
        
        colunas_encontradas = {}
        for col_sistema, col_planilha in colunas_opcionais.items():
            if col_planilha in df.columns:
                colunas_encontradas[col_sistema] = col_planilha
        
        print(f"\n📊 COLUNAS MAPEADAS:")
        for col_sistema, col_planilha in colunas_encontradas.items():
            valores_nao_vazios = df[col_planilha].notna().sum()
            print(f"   • {col_sistema} ← {col_planilha} ({valores_nao_vazios} valores)")
        
        if not colunas_encontradas:
            print("⚠️  Nenhuma coluna opcional encontrada. Nada para atualizar.")
            return
        
        # Estatísticas de processamento
        stats = {
            'linhas_processadas': 0,
            'entregas_encontradas': 0,
            'entregas_nao_encontradas': 0,
            'entregas_atualizadas': 0,
            'agendamentos_criados': 0,
            'acompanhamentos_criados': 0,
            'erros': 0
        }
        
        print(f"\n🔄 PROCESSANDO LINHAS...")
        
        for index, row in df.iterrows():
            stats['linhas_processadas'] += 1
            
            # Pega número da NF
            numero_nf = str(row['numero_nf']).strip()
            if not numero_nf or numero_nf.lower() in ['nan', 'none']:
                print(f"❌ Linha {index + 1}: NF vazia")
                stats['erros'] += 1
                continue
            
            try:
                # Busca entrega
                entrega = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
                
                if not entrega:
                    print(f"⚠️  Linha {index + 1}: NF {numero_nf} não encontrada no monitoramento")
                    stats['entregas_nao_encontradas'] += 1
                    continue
                
                stats['entregas_encontradas'] += 1
                print(f"📦 Linha {index + 1}: NF {numero_nf} - Cliente: {entrega.cliente[:30]}...")
                
                entrega_atualizada = False
                
                # ATUALIZAÇÃO A: Datas
                if 'data_embarque' in colunas_encontradas:
                    nova_data = converter_data_segura(row[colunas_encontradas['data_embarque']])
                    if nova_data and nova_data != entrega.data_embarque:
                        if not dry_run:
                            entrega.data_embarque = nova_data
                        print(f"   ✏️  Data embarque: {entrega.data_embarque} → {nova_data}")
                        entrega_atualizada = True
                
                if 'data_entrega_prevista' in colunas_encontradas:
                    nova_data = converter_data_segura(row[colunas_encontradas['data_entrega_prevista']])
                    if nova_data and nova_data != entrega.data_entrega_prevista:
                        if not dry_run:
                            entrega.data_entrega_prevista = nova_data
                        print(f"   ✏️  Data entrega prevista: {entrega.data_entrega_prevista} → {nova_data}")
                        entrega_atualizada = True
                
                if 'data_agenda' in colunas_encontradas:
                    nova_data = converter_data_segura(row[colunas_encontradas['data_agenda']])
                    if nova_data and nova_data != entrega.data_agenda:
                        if not dry_run:
                            entrega.data_agenda = nova_data
                        print(f"   ✏️  Data agenda: {entrega.data_agenda} → {nova_data}")
                        entrega_atualizada = True
                
                # ATUALIZAÇÃO B: Status de finalização
                if 'status_finalizacao' in colunas_encontradas:
                    novo_status = str(row[colunas_encontradas['status_finalizacao']]).strip()
                    if novo_status and novo_status.lower() not in ['nan', 'none', '-'] and novo_status != entrega.status_finalizacao:
                        if not dry_run:
                            entrega.status_finalizacao = novo_status
                            if novo_status.lower() in ['cancelada', 'devolvida']:
                                entrega.finalizado_em = datetime.utcnow()
                                entrega.finalizado_por = 'Planilha'
                        print(f"   ✏️  Status: {entrega.status_finalizacao} → {novo_status}")
                        entrega_atualizada = True
                
                # ATUALIZAÇÃO C: Agendamento
                if 'protocolo_agendamento' in colunas_encontradas or 'data_agendamento' in colunas_encontradas:
                    protocolo = str(row.get(colunas_encontradas.get('protocolo_agendamento', ''), '')).strip()
                    data_agend = converter_data_segura(row.get(colunas_encontradas.get('data_agendamento', '')))
                    
                    if protocolo and protocolo.lower() not in ['nan', 'none', '-'] or data_agend:
                        # Verifica se já existe agendamento com esse protocolo
                        existe_agendamento = any(
                            ag.protocolo_agendamento == protocolo 
                            for ag in entrega.agendamentos 
                            if ag.protocolo_agendamento
                        ) if protocolo else False
                        
                        if not existe_agendamento:
                            if not dry_run:
                                agendamento = AgendamentoEntrega(
                                    entrega_id=entrega.id,
                                    data_agendada=data_agend,
                                    protocolo_agendamento=protocolo if protocolo and protocolo.lower() not in ['nan', 'none', '-'] else None,
                                    forma_agendamento='Planilha',
                                    motivo='Importação via planilha',
                                    autor='Sistema'
                                )
                                db.session.add(agendamento)
                                stats['agendamentos_criados'] += 1
                            print(f"   ➕ Agendamento: Protocolo {protocolo}, Data {data_agend}")
                
                # ATUALIZAÇÃO D: Acompanhamento
                if 'acompanhamento_descricao' in colunas_encontradas:
                    descricao = str(row[colunas_encontradas['acompanhamento_descricao']]).strip()
                    if descricao and descricao.lower() not in ['nan', 'none', '-']:
                        if not dry_run:
                            log = RegistroLogEntrega(
                                entrega_id=entrega.id,
                                autor='Sistema',
                                data_hora=datetime.utcnow(),
                                descricao=descricao,
                                tipo='info'
                            )
                            db.session.add(log)
                            stats['acompanhamentos_criados'] += 1
                        print(f"   ➕ Acompanhamento: {descricao[:50]}...")
                
                if entrega_atualizada:
                    stats['entregas_atualizadas'] += 1
                
            except Exception as e:
                print(f"❌ Linha {index + 1}: Erro ao processar NF {numero_nf}: {e}")
                stats['erros'] += 1
        
        # Salva alterações
        if not dry_run and confirmar:
            try:
                db.session.commit()
                print(f"\n✅ ALTERAÇÕES SALVAS COM SUCESSO!")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ ERRO AO SALVAR: {e}")
                return
        elif dry_run:
            print(f"\n🔍 MODO SIMULAÇÃO - Nenhuma alteração foi salva")
        
        # Estatísticas finais
        print(f"\n📊 ESTATÍSTICAS FINAIS:")
        print(f"   • Linhas processadas: {stats['linhas_processadas']}")
        print(f"   • Entregas encontradas: {stats['entregas_encontradas']}")
        print(f"   • Entregas não encontradas: {stats['entregas_nao_encontradas']}")
        print(f"   • Entregas atualizadas: {stats['entregas_atualizadas']}")
        print(f"   • Agendamentos criados: {stats['agendamentos_criados']}")
        print(f"   • Acompanhamentos criados: {stats['acompanhamentos_criados']}")
        print(f"   • Erros: {stats['erros']}")
        
        if dry_run:
            print(f"\n💡 Para executar as alterações, use: python {sys.argv[0]} {arquivo_excel} --confirmar")

def main():
    parser = argparse.ArgumentParser(description='Preparar atualizações da EntregaMonitorada')
    parser.add_argument('arquivo', help='Arquivo Excel com os dados')
    parser.add_argument('--sheet', default='Sheet1', help='Nome da aba da planilha')
    parser.add_argument('--dry-run', action='store_true', help='Simula as alterações sem executar')
    parser.add_argument('--confirmar', action='store_true', help='Confirma e executa as alterações')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.arquivo):
        print(f"❌ Arquivo não encontrado: {args.arquivo}")
        return
    
    # Por padrão, roda em modo simulação
    dry_run = not args.confirmar
    
    preparar_atualizacao_entrega_monitorada(
        args.arquivo, 
        sheet_name=args.sheet,
        dry_run=dry_run, 
        confirmar=args.confirmar
    )

if __name__ == '__main__':
    main() 