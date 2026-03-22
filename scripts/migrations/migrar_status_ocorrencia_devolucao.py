"""
Migration: Migrar status de ocorrencia_devolucao para novo modelo auto-computado
============================================================================

Status antigos: ABERTA, EM_ANALISE, AGUARDANDO_RETORNO, RETORNADA, RESOLVIDA, CANCELADA
Status novos: PENDENTE, EM_ANDAMENTO, RESOLVIDO (auto-computados)

Logica:
- PENDENTE: campos comerciais incompletos
- EM_ANDAMENTO: todos 7 campos comerciais preenchidos, NF sem entrada
- RESOLVIDO: todos 7 campos preenchidos + NF com entrada (odoo_status_codigo='06')

Criado em: 22/03/2026
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.devolucao.models import OcorrenciaDevolucao


def migrar_status():
    """Migra status existentes usando calcular_status() do modelo."""
    app = create_app()
    with app.app_context():
        # Verificar estado antes
        total = OcorrenciaDevolucao.query.filter_by(ativo=True).count()
        print(f"Total de ocorrencias ativas: {total}")

        # Contar status antigos
        for status in ['ABERTA', 'EM_ANALISE', 'AGUARDANDO_RETORNO', 'RETORNADA', 'RESOLVIDA', 'CANCELADA']:
            count = OcorrenciaDevolucao.query.filter_by(ativo=True, status=status).count()
            if count > 0:
                print(f"  {status}: {count}")

        # Contar novos (caso ja tenha sido parcialmente migrado)
        for status in ['PENDENTE', 'EM_ANDAMENTO', 'RESOLVIDO']:
            count = OcorrenciaDevolucao.query.filter_by(ativo=True, status=status).count()
            if count > 0:
                print(f"  {status} (novo): {count}")

        # Migrar usando calcular_status()
        ocorrencias = OcorrenciaDevolucao.query.filter_by(ativo=True).all()
        migrados = 0
        for oc in ocorrencias:
            novo_status = oc.calcular_status()
            if oc.status != novo_status:
                oc.status = novo_status
                migrados += 1

        db.session.commit()

        # Verificar estado depois
        print(f"\nMigrados: {migrados} de {total}")
        for status in ['PENDENTE', 'EM_ANDAMENTO', 'RESOLVIDO']:
            count = OcorrenciaDevolucao.query.filter_by(ativo=True, status=status).count()
            print(f"  {status}: {count}")

        print("\nMigracao concluida com sucesso!")


if __name__ == '__main__':
    migrar_status()
