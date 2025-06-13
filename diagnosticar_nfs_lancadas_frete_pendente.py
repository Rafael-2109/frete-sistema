#!/usr/bin/env python3
"""
Script para diagnosticar casos onde NFs estão "Lançadas" mas Frete está "Pendente".
Identifica as causas técnicas específicas.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.embarques.models import Embarque, EmbarqueItem
from app.fretes.models import Frete
from app.fretes.routes import verificar_requisitos_para_lancamento_frete, lancar_frete_automatico
from app.utils.calculadora_frete import calcular_valor_frete_pela_tabela
from app.faturamento.models import RelatorioFaturamentoImportado
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnosticar_nfs_lancadas_frete_pendente():
    """
    Diagnostica embarques onde NFs estão "Lançadas" mas Frete está "Pendente".
    """
    app = create_app()
    
    with app.app_context():
        print("🔧 DIAGNÓSTICO: NFs LANÇADAS + FRETE PENDENTE")
        print("=" * 60)
        
        # Busca embarques com NFs "Lançadas" mas Frete "Pendente"
        embarques = Embarque.query.filter(Embarque.status == 'ativo').all()
        
        casos_encontrados = []
        
        for embarque in embarques:
            if embarque.status_nfs == 'NFs Lançadas' and embarque.status_fretes == 'Pendentes':
                casos_encontrados.append(embarque)
        
        if not casos_encontrados:
            print("✅ Nenhum caso encontrado de NFs Lançadas + Frete Pendente")
            return
        
        print(f"🔍 ENCONTRADOS {len(casos_encontrados)} CASO(S) PARA DIAGNÓSTICO")
        print("=" * 60)
        
        for i, embarque in enumerate(casos_encontrados, 1):
            print(f"\n📋 CASO {i}: EMBARQUE #{embarque.numero or embarque.id}")
            print(f"   Status NFs: {embarque.status_nfs}")
            print(f"   Status Fretes: {embarque.status_fretes}")
            print(f"   Tipo Carga: {embarque.tipo_carga}")
            print(f"   Transportadora: {embarque.transportadora.razao_social if embarque.transportadora else 'N/A'}")
            
            # ✅ CORREÇÃO: Busca CNPJs únicos do embarque (apenas itens ATIVOS)
            cnpjs_embarque = db.session.query(EmbarqueItem.cnpj_cliente)\
                .filter(EmbarqueItem.embarque_id == embarque.id)\
                .filter(EmbarqueItem.status == 'ativo')\
                .filter(EmbarqueItem.nota_fiscal.isnot(None))\
                .filter(EmbarqueItem.cnpj_cliente.isnot(None))\
                .distinct().all()
            
            print(f"   CNPJs no embarque: {len(cnpjs_embarque)}")
            
            for j, (cnpj,) in enumerate(cnpjs_embarque, 1):
                print(f"\n   🔍 CNPJ {j}: {cnpj}")
                
                # Verifica se já existe frete
                frete_existente = Frete.query.filter(
                    Frete.embarque_id == embarque.id,
                    Frete.cnpj_cliente == cnpj
                ).first()
                
                if frete_existente:
                    print(f"      ✅ Frete já existe: #{frete_existente.id} (Status: {frete_existente.status})")
                    continue
                
                print(f"      ❌ Frete não existe - diagnosticando...")
                
                # 1. Verifica requisitos
                pode_lancar, motivo_requisitos = verificar_requisitos_para_lancamento_frete(embarque.id, cnpj)
                print(f"      📋 Requisitos: {'✅ OK' if pode_lancar else '❌ FALHA'}")
                if not pode_lancar:
                    print(f"         Motivo: {motivo_requisitos}")
                    continue
                
                # 2. Verifica dados da tabela
                print(f"      🔧 Verificando dados da tabela...")
                dados_tabela_ok = True
                
                if embarque.tipo_carga == 'DIRETA':
                    campos_obrigatorios = ['modalidade', 'tabela_valor_kg', 'tabela_percentual_valor']
                    for campo in campos_obrigatorios:
                        valor = getattr(embarque, campo, None)
                        if valor is None:
                            print(f"         ❌ Campo {campo} está None")
                            dados_tabela_ok = False
                else:
                    # FRACIONADA - verifica item ATIVO
                    item_ref = EmbarqueItem.query.filter(
                        EmbarqueItem.embarque_id == embarque.id,
                        EmbarqueItem.cnpj_cliente == cnpj,
                        EmbarqueItem.status == 'ativo'
                    ).first()
                    
                    if item_ref:
                        campos_obrigatorios = ['modalidade', 'tabela_valor_kg', 'tabela_percentual_valor']
                        for campo in campos_obrigatorios:
                            valor = getattr(item_ref, campo, None)
                            if valor is None:
                                print(f"         ❌ Campo {campo} está None no item")
                                dados_tabela_ok = False
                
                if not dados_tabela_ok:
                    print(f"      ❌ Dados da tabela incompletos")
                    continue
                
                # 3. Verifica peso e valor no faturamento (apenas itens ATIVOS)
                print(f"      💰 Verificando peso/valor no faturamento...")
                itens_cnpj = EmbarqueItem.query.filter(
                    EmbarqueItem.embarque_id == embarque.id,
                    EmbarqueItem.cnpj_cliente == cnpj,
                    EmbarqueItem.status == 'ativo',
                    EmbarqueItem.nota_fiscal.isnot(None)
                ).all()
                
                nfs_faturamento = []
                for item in itens_cnpj:
                    nf_fat = RelatorioFaturamentoImportado.query.filter_by(
                        numero_nf=item.nota_fiscal,
                        cnpj_cliente=cnpj
                    ).first()
                    if nf_fat:
                        nfs_faturamento.append(nf_fat)
                
                peso_total = sum(float(nf.peso_bruto or 0) for nf in nfs_faturamento)
                valor_total = sum(float(nf.valor_total or 0) for nf in nfs_faturamento)
                
                print(f"         Peso total: {peso_total} kg")
                print(f"         Valor total: R$ {valor_total:.2f}")
                
                if peso_total == 0 or valor_total == 0:
                    print(f"      ❌ Peso ou valor zerado no faturamento")
                    continue
                
                # 4. Testa calculadora de frete
                print(f"      🧮 Testando calculadora de frete...")
                try:
                    if embarque.tipo_carga == 'DIRETA':
                        tabela_dados = {
                            'modalidade': embarque.modalidade,
                            'valor_kg': embarque.tabela_valor_kg,
                            'percentual_valor': embarque.tabela_percentual_valor,
                            'frete_minimo_valor': embarque.tabela_frete_minimo_valor,
                            'frete_minimo_peso': embarque.tabela_frete_minimo_peso,
                            'icms': embarque.tabela_icms,
                            'percentual_gris': embarque.tabela_percentual_gris,
                            'pedagio_por_100kg': embarque.tabela_pedagio_por_100kg,
                            'valor_tas': embarque.tabela_valor_tas,
                            'percentual_adv': embarque.tabela_percentual_adv,
                            'percentual_rca': embarque.tabela_percentual_rca,
                            'valor_despacho': embarque.tabela_valor_despacho,
                            'valor_cte': embarque.tabela_valor_cte,
                            'icms_incluso': embarque.tabela_icms_incluso,
                            'icms_destino': embarque.icms_destino or 0
                        }
                    else:
                        item_ref = itens_cnpj[0]
                        tabela_dados = {
                            'modalidade': item_ref.modalidade,
                            'valor_kg': item_ref.tabela_valor_kg,
                            'percentual_valor': item_ref.tabela_percentual_valor,
                            'frete_minimo_valor': item_ref.tabela_frete_minimo_valor,
                            'frete_minimo_peso': item_ref.tabela_frete_minimo_peso,
                            'icms': item_ref.tabela_icms,
                            'percentual_gris': item_ref.tabela_percentual_gris,
                            'pedagio_por_100kg': item_ref.tabela_pedagio_por_100kg,
                            'valor_tas': item_ref.tabela_valor_tas,
                            'percentual_adv': item_ref.tabela_percentual_adv,
                            'percentual_rca': item_ref.tabela_percentual_rca,
                            'valor_despacho': item_ref.tabela_valor_despacho,
                            'valor_cte': item_ref.tabela_valor_cte,
                            'icms_incluso': item_ref.tabela_icms_incluso,
                            'icms_destino': item_ref.icms_destino or 0
                        }
                    
                    valor_calculado = calcular_valor_frete_pela_tabela(tabela_dados, peso_total, valor_total)
                    print(f"         Valor calculado: R$ {valor_calculado:.2f}")
                    
                    if valor_calculado <= 0:
                        print(f"      ❌ Calculadora retornou valor inválido: {valor_calculado}")
                        continue
                    
                except Exception as e:
                    print(f"      ❌ Erro na calculadora: {str(e)}")
                    continue
                
                # 5. Tenta lançar o frete
                print(f"      🚀 Tentando lançar frete...")
                try:
                    sucesso, resultado = lancar_frete_automatico(embarque.id, cnpj, 'DIAGNOSTICO')
                    if sucesso:
                        print(f"      ✅ Frete lançado com sucesso: {resultado}")
                    else:
                        print(f"      ❌ Falha ao lançar frete: {resultado}")
                except Exception as e:
                    print(f"      ❌ Exceção ao lançar frete: {str(e)}")
        
        print("\n" + "=" * 60)
        print("🏁 DIAGNÓSTICO CONCLUÍDO")

if __name__ == "__main__":
    diagnosticar_nfs_lancadas_frete_pendente() 