#!/usr/bin/env python3
"""
🛠️ SCRIPT DE MANUTENÇÃO DO SISTEMA DE APRENDIZADO VITALÍCIO
Ferramentas para verificar, limpar e otimizar o aprendizado
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text
import json


class ManutencaoAprendizado:
    """Classe para manutenção do sistema de aprendizado"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
    
    def verificar_saude(self):
        """Verifica a saúde geral do sistema de aprendizado"""
        print("\n🏥 VERIFICAÇÃO DE SAÚDE DO SISTEMA DE APRENDIZADO")
        print("=" * 80)
        
        # 1. Estatísticas gerais
        stats = db.session.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM ai_knowledge_patterns) as total_padroes,
                (SELECT COUNT(*) FROM ai_knowledge_patterns WHERE confidence > 0.8) as padroes_confiaveis,
                (SELECT COUNT(*) FROM ai_semantic_mappings) as total_mapeamentos,
                (SELECT COUNT(*) FROM ai_grupos_empresariais) as total_grupos,
                (SELECT COUNT(*) FROM ai_learning_history) as total_historico,
                (SELECT COUNT(*) FROM ai_learning_history WHERE created_at > CURRENT_DATE - INTERVAL '7 days') as historico_semana
        """)).first()
        
        print("\n📊 ESTATÍSTICAS GERAIS:")
        print(f"  • Total de Padrões: {stats.total_padroes}")
        print(f"  • Padrões Confiáveis (>0.8): {stats.padroes_confiaveis} ({stats.padroes_confiaveis/max(stats.total_padroes,1)*100:.1f}%)")
        print(f"  • Mapeamentos Semânticos: {stats.total_mapeamentos}")
        print(f"  • Grupos Empresariais: {stats.total_grupos}")
        print(f"  • Histórico Total: {stats.total_historico}")
        print(f"  • Interações na Semana: {stats.historico_semana}")
        
        # 2. Padrões problemáticos
        problemas = db.session.execute(text("""
            SELECT pattern_type, pattern_text, confidence, success_rate, usage_count
            FROM ai_knowledge_patterns
            WHERE confidence < 0.5 AND usage_count > 5
            ORDER BY usage_count DESC
            LIMIT 10
        """)).fetchall()
        
        if problemas:
            print("\n⚠️  PADRÕES PROBLEMÁTICOS (baixa confiança, muito uso):")
            headers = ["Tipo", "Texto", "Confiança", "Taxa Sucesso", "Usos"]
            rows = [(p.pattern_type, p.pattern_text[:40], f"{p.confidence:.2f}", 
                    f"{p.success_rate:.2f}", p.usage_count) for p in problemas]
            print(tabulate(rows, headers=headers, tablefmt="grid"))
        
        # 3. Grupos não confirmados
        grupos_nc = db.session.execute(text("""
            SELECT nome_grupo, tipo_negocio, created_at
            FROM ai_grupos_empresariais
            WHERE aprendido_automaticamente = TRUE AND confirmado_por IS NULL
        """)).fetchall()
        
        if grupos_nc:
            print("\n🏢 GRUPOS EMPRESARIAIS NÃO CONFIRMADOS:")
            for g in grupos_nc:
                print(f"  • {g.nome_grupo} ({g.tipo_negocio}) - Descoberto em {g.created_at.strftime('%d/%m/%Y')}")
        
        # 4. Taxa de aprendizado
        taxa = db.session.execute(text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN tipo_correcao IS NOT NULL THEN 1 ELSE 0 END) as correcoes,
                AVG(CASE WHEN tipo_correcao IS NULL THEN 1 ELSE 0 END) * 100 as taxa_acerto
            FROM ai_learning_history
            WHERE created_at > CURRENT_DATE - INTERVAL '30 days'
        """)).first()
        
        if taxa.total > 0:
            print(f"\n📈 TAXA DE APRENDIZADO (últimos 30 dias):")
            print(f"  • Total de Interações: {taxa.total}")
            print(f"  • Correções Necessárias: {taxa.correcoes}")
            print(f"  • Taxa de Acerto: {taxa.taxa_acerto:.1f}%")
    
    def limpar_padroes_ruins(self, confirmar=True):
        """Remove padrões com baixa performance"""
        print("\n🧹 LIMPEZA DE PADRÕES RUINS")
        print("=" * 80)
        
        # Identificar padrões ruins
        ruins = db.session.execute(text("""
            SELECT id, pattern_type, pattern_text, confidence, success_rate, usage_count
            FROM ai_knowledge_patterns
            WHERE (success_rate < 0.3 AND usage_count > 5)
               OR (confidence < 0.2 AND usage_count > 10)
        """)).fetchall()
        
        if not ruins:
            print("✅ Nenhum padrão ruim encontrado!")
            return
        
        print(f"\n⚠️  Encontrados {len(ruins)} padrões ruins:")
        headers = ["ID", "Tipo", "Texto", "Confiança", "Taxa Sucesso", "Usos"]
        rows = [(p.id, p.pattern_type, p.pattern_text[:30], f"{p.confidence:.2f}", 
                f"{p.success_rate:.2f}", p.usage_count) for p in ruins]
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        
        if confirmar:
            resp = input("\n❓ Deseja remover estes padrões? (s/N): ")
            if resp.lower() != 's':
                print("❌ Operação cancelada")
                return
        
        # Remover padrões
        ids = [p.id for p in ruins]
        db.session.execute(
            text("DELETE FROM ai_knowledge_patterns WHERE id IN :ids"),
            {"ids": tuple(ids)}
        )
        db.session.commit()
        print(f"✅ {len(ruins)} padrões removidos!")
    
    def consolidar_mapeamentos(self):
        """Consolida mapeamentos duplicados"""
        print("\n🔄 CONSOLIDAÇÃO DE MAPEAMENTOS")
        print("=" * 80)
        
        # Encontrar duplicatas
        duplicatas = db.session.execute(text("""
            SELECT termo_usuario, COUNT(DISTINCT campo_sistema) as qtd
            FROM ai_semantic_mappings
            GROUP BY termo_usuario
            HAVING COUNT(DISTINCT campo_sistema) > 1
        """)).fetchall()
        
        if not duplicatas:
            print("✅ Nenhuma duplicata encontrada!")
            return
        
        print(f"\n⚠️  Encontrados {len(duplicatas)} termos com múltiplos mapeamentos:")
        
        for dup in duplicatas:
            print(f"\n📍 Termo: '{dup.termo_usuario}' ({dup.qtd} mapeamentos)")
            
            # Mostrar opções
            opcoes = db.session.execute(text("""
                SELECT id, campo_sistema, modelo, frequencia
                FROM ai_semantic_mappings
                WHERE termo_usuario = :termo
                ORDER BY frequencia DESC
            """), {"termo": dup.termo_usuario}).fetchall()
            
            for i, op in enumerate(opcoes):
                print(f"  {i+1}. {op.campo_sistema} ({op.modelo}) - {op.frequencia} usos")
            
            # Manter o mais usado
            principal = opcoes[0]
            outros_ids = [op.id for op in opcoes[1:]]
            
            # Somar frequências
            total_freq = sum(op.frequencia for op in opcoes)
            
            # Atualizar principal
            db.session.execute(text("""
                UPDATE ai_semantic_mappings
                SET frequencia = :freq
                WHERE id = :id
            """), {"freq": total_freq, "id": principal.id})
            
            # Remover outros
            if outros_ids:
                db.session.execute(
                    text("DELETE FROM ai_semantic_mappings WHERE id IN :ids"),
                    {"ids": tuple(outros_ids)}
                )
            
            print(f"  ✅ Consolidado em: {principal.campo_sistema} ({total_freq} usos)")
        
        db.session.commit()
        print(f"\n✅ {len(duplicatas)} mapeamentos consolidados!")
    
    def validar_grupos(self):
        """Lista grupos para validação"""
        print("\n🏢 VALIDAÇÃO DE GRUPOS EMPRESARIAIS")
        print("=" * 80)
        
        grupos = db.session.execute(text("""
            SELECT id, nome_grupo, tipo_negocio, palavras_chave, 
                   aprendido_automaticamente, confirmado_por
            FROM ai_grupos_empresariais
            WHERE confirmado_por IS NULL
            ORDER BY aprendido_automaticamente DESC, nome_grupo
        """)).fetchall()
        
        if not grupos:
            print("✅ Todos os grupos já foram validados!")
            return
        
        print(f"\n📋 {len(grupos)} grupos aguardando validação:\n")
        
        for g in grupos:
            print(f"ID: {g.id}")
            print(f"Nome: {g.nome_grupo}")
            print(f"Tipo: {g.tipo_negocio}")
            print(f"Palavras-chave: {g.palavras_chave}")
            print(f"Auto-descoberto: {'Sim' if g.aprendido_automaticamente else 'Não'}")
            print("-" * 40)
        
        print("\n💡 Para validar, use:")
        print("UPDATE ai_grupos_empresariais SET confirmado_por = 'seu_nome' WHERE id = <ID>;")
    
    def limpar_historico(self, dias=90):
        """Limpa histórico antigo"""
        print(f"\n🗑️  LIMPEZA DE HISTÓRICO (>{dias} dias)")
        print("=" * 80)
        
        # Contar registros
        total = db.session.execute(text("""
            SELECT COUNT(*) as qtd
            FROM ai_learning_history
            WHERE created_at < CURRENT_DATE - INTERVAL :dias DAY
        """), {"dias": dias}).scalar()
        
        if total == 0:
            print("✅ Nenhum registro antigo encontrado!")
            return
        
        print(f"\n⚠️  Encontrados {total} registros com mais de {dias} dias")
        
        resp = input("\n❓ Deseja remover estes registros? (s/N): ")
        if resp.lower() != 's':
            print("❌ Operação cancelada")
            return
        
        # Limpar
        db.session.execute(text("""
            DELETE FROM ai_learning_history
            WHERE created_at < CURRENT_DATE - INTERVAL :dias DAY
        """), {"dias": dias})
        db.session.commit()
        
        print(f"✅ {total} registros removidos!")
    
    def exportar_conhecimento(self, arquivo="conhecimento_exportado.json"):
        """Exporta todo conhecimento aprendido"""
        print("\n💾 EXPORTANDO CONHECIMENTO")
        print("=" * 80)
        
        conhecimento = {
            "exportado_em": datetime.now().isoformat(),
            "padroes": [],
            "mapeamentos": [],
            "grupos": [],
            "contextos": []
        }
        
        # Padrões
        padroes = db.session.execute(text("""
            SELECT * FROM ai_knowledge_patterns
            WHERE confidence > 0.5
            ORDER BY confidence DESC
        """)).fetchall()
        
        for p in padroes:
            conhecimento["padroes"].append({
                "tipo": p.pattern_type,
                "texto": p.pattern_text,
                "interpretacao": p.interpretation,
                "confianca": p.confidence,
                "taxa_sucesso": p.success_rate,
                "usos": p.usage_count
            })
        
        # Mapeamentos
        mapas = db.session.execute(text("""
            SELECT * FROM ai_semantic_mappings
            WHERE frequencia > 2
        """)).fetchall()
        
        for m in mapas:
            conhecimento["mapeamentos"].append({
                "termo": m.termo_usuario,
                "campo": m.campo_sistema,
                "modelo": m.modelo,
                "frequencia": m.frequencia,
                "validado": m.validado
            })
        
        # Grupos
        grupos = db.session.execute(text("""
            SELECT * FROM ai_grupos_empresariais
            WHERE ativo = TRUE
        """)).fetchall()
        
        for g in grupos:
            conhecimento["grupos"].append({
                "nome": g.nome_grupo,
                "tipo": g.tipo_negocio,
                "palavras": g.palavras_chave,
                "filtro": g.filtro_sql,
                "confirmado": g.confirmado_por is not None
            })
        
        # Salvar
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(conhecimento, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Conhecimento exportado para: {arquivo}")
        print(f"  • {len(conhecimento['padroes'])} padrões")
        print(f"  • {len(conhecimento['mapeamentos'])} mapeamentos")
        print(f"  • {len(conhecimento['grupos'])} grupos")


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Manutenção do Sistema de Aprendizado')
    parser.add_argument('comando', choices=['saude', 'limpar', 'consolidar', 
                                           'validar', 'historico', 'exportar'],
                       help='Comando a executar')
    parser.add_argument('--dias', type=int, default=90,
                       help='Dias para limpeza de histórico (padrão: 90)')
    parser.add_argument('--arquivo', default='conhecimento_exportado.json',
                       help='Arquivo para exportação')
    
    args = parser.parse_args()
    
    manutencao = ManutencaoAprendizado()
    
    if args.comando == 'saude':
        manutencao.verificar_saude()
    elif args.comando == 'limpar':
        manutencao.limpar_padroes_ruins()
    elif args.comando == 'consolidar':
        manutencao.consolidar_mapeamentos()
    elif args.comando == 'validar':
        manutencao.validar_grupos()
    elif args.comando == 'historico':
        manutencao.limpar_historico(args.dias)
    elif args.comando == 'exportar':
        manutencao.exportar_conhecimento(args.arquivo)


if __name__ == "__main__":
    main() 