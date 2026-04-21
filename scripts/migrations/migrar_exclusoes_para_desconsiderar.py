"""Converte PessoalExclusaoEmpresa (ativo=True) em regras PADRAO apontando
para a categoria 'Desconsiderar / Empresa (Migrado)'.

Apos este script:
- Cada padrao de exclusao ativa vira uma regra ativa (origem='manual').
- Registros originais de PessoalExclusaoEmpresa ficam ativo=False (preservados para auditoria).
- O Layer 0 do pipeline de categorizacao pode ser removido no codigo (regras cobrem o caso
  via eh_categoria_desconsiderar em _aplicar_regra).

Uso:
    source .venv/bin/activate
    python scripts/migrations/migrar_exclusoes_para_desconsiderar.py

Idempotente: pode rodar varias vezes sem efeito colateral.
"""
from app import create_app, db
from app.pessoal.models import (
    PessoalExclusaoEmpresa, PessoalCategoria, PessoalRegraCategorizacao,
)
from app.pessoal.services.aprendizado_service import normalizar_padrao


CATEGORIA_RECEPTORA_GRUPO = 'Desconsiderar'
CATEGORIA_RECEPTORA_NOME = 'Empresa (Migrado)'
CATEGORIA_RECEPTORA_ICONE = 'fa-ban'


def main():
    app = create_app()
    with app.app_context():
        # 1. Garantir categoria receptora no grupo 'Desconsiderar'
        cat = PessoalCategoria.query.filter_by(
            grupo=CATEGORIA_RECEPTORA_GRUPO,
            nome=CATEGORIA_RECEPTORA_NOME,
        ).first()
        if not cat:
            cat = PessoalCategoria(
                grupo=CATEGORIA_RECEPTORA_GRUPO,
                nome=CATEGORIA_RECEPTORA_NOME,
                icone=CATEGORIA_RECEPTORA_ICONE,
                ativa=True,
            )
            db.session.add(cat)
            db.session.flush()
            print(f'[+] Criada categoria "{CATEGORIA_RECEPTORA_GRUPO} / {CATEGORIA_RECEPTORA_NOME}" id={cat.id}')
        else:
            print(f'[=] Categoria receptora ja existe id={cat.id}')

        # 2. Verificar ANTES
        exclusoes_ativas = PessoalExclusaoEmpresa.query.filter_by(ativo=True).all()
        print(f'[*] Exclusoes ativas a migrar: {len(exclusoes_ativas)}')

        criadas = 0
        ja_existentes = 0
        desativadas = 0
        for excl in exclusoes_ativas:
            padrao_norm = normalizar_padrao(excl.padrao)
            if not padrao_norm:
                continue

            ja = PessoalRegraCategorizacao.query.filter_by(
                padrao_historico=padrao_norm,
                categoria_id=cat.id,
                tipo_regra='PADRAO',
            ).first()
            if ja:
                ja_existentes += 1
                if not ja.ativo:
                    ja.ativo = True
            else:
                regra = PessoalRegraCategorizacao(
                    padrao_historico=padrao_norm,
                    tipo_regra='PADRAO',
                    categoria_id=cat.id,
                    origem='manual',
                    ativo=True,
                    confianca=100,
                )
                db.session.add(regra)
                criadas += 1

            excl.ativo = False
            desativadas += 1

        db.session.commit()

        # 3. Verificar DEPOIS
        ativas_pos = PessoalExclusaoEmpresa.query.filter_by(ativo=True).count()
        total_regras = PessoalRegraCategorizacao.query.filter_by(
            categoria_id=cat.id, tipo_regra='PADRAO', ativo=True,
        ).count()
        print(f'[OK] Regras criadas: {criadas}')
        print(f'[OK] Regras ja existentes reutilizadas: {ja_existentes}')
        print(f'[OK] Exclusoes desativadas: {desativadas}')
        print(f'[OK] Exclusoes ativas restantes: {ativas_pos} (esperado: 0)')
        print(f'[OK] Total de regras PADRAO apontando para a categoria receptora: {total_regras}')

        # 4. Invalidar cache do pipeline
        from app.pessoal.services.categorizacao_service import invalidar_cache_desconsiderar
        invalidar_cache_desconsiderar()
        print('[OK] Cache de Desconsiderar invalidado.')


if __name__ == '__main__':
    main()
