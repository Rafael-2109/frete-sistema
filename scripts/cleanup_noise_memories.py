"""
Limpeza de memórias empresa de baixo valor (noise).

Contexto: A auditoria de 15/03/2026 identificou 17 memórias com usage_count > 10
mas effective_count = 0, gastando tokens de contexto sem valor.

Estratégia:
- Perfis de usuário vazios (< 100 bytes úteis): deletar
- Termos triviais (definíveis pelo LLM sem contexto Nacom): mover para cold tier
- Admin corrections obsoletas (never effective): mover para cold tier
- Correções one-shot: generalizar ou mover para cold

Uso:
    # Dry-run (default): lista candidatas sem alterar
    python scripts/cleanup_noise_memories.py

    # Executar limpeza
    python scripts/cleanup_noise_memories.py --execute

    # Apenas listar noise com thresholds customizados
    python scripts/cleanup_noise_memories.py --min-usage 5 --max-effective 0
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('cleanup_noise')

# Memórias noise identificadas na auditoria (paths relativos)
NOISE_PATHS_TO_COLD = [
    # Termos triviais — LLM já sabe o que são
    'empresa/termos/cross-docking.xml',
    'empresa/termos/janela-de-descarga.xml',
    'empresa/termos/d-2.xml',
    'empresa/termos/lote.xml',
    'empresa/termos/embarqueitem.xml',
    'empresa/termos/relatoriofaturamentoimportado.xml',
    'empresa/termos/modo-debug.xml',
    'empresa/termos/pedido-de-venda.xml',
    'empresa/termos/carteira.xml',
    'empresa/termos/data-de-expedicao.xml',
    'empresa/termos/separacao.xml',
    # Admin corrections obsoletas
    'empresa/corrections/capacidade-caminhoes-consultar-veiculos.xml',
    # Regras redundantes/óbvias
    'empresa/regras/o-cliente-sanna-possui-pedidos-identific.xml',
    'empresa/regras/o-campo-purchase-order-id-no-odoo-pode-n.xml',
]

# Perfis de usuário vazios (< 100 bytes úteis) — deletar
EMPTY_PROFILES_TO_DELETE = [
    'empresa/usuarios/rafael.xml',
    'empresa/usuarios/edson.xml',
    'empresa/usuarios/fernando.xml',
]


def main():
    parser = argparse.ArgumentParser(description='Limpar memórias empresa noise')
    parser.add_argument('--execute', action='store_true', help='Executar limpeza')
    parser.add_argument(
        '--min-usage', type=int, default=10,
        help='Mínimo de usage_count para considerar noise (default: 10)',
    )
    parser.add_argument(
        '--max-effective', type=int, default=0,
        help='Máximo de effective_count para considerar noise (default: 0)',
    )
    parser.add_argument(
        '--auto-detect', action='store_true',
        help='Detectar noise automaticamente além da lista fixa',
    )
    args = parser.parse_args()

    from app import create_app, db
    app = create_app()

    with app.app_context():
        from app.agente.models import AgentMemory
        from app.utils.timezone import agora_utc_naive

        # === FASE 1: Mover para cold tier (lista fixa) ===
        cold_candidates = []
        for path_suffix in NOISE_PATHS_TO_COLD:
            mem = AgentMemory.query.filter(
                AgentMemory.user_id == 0,
                AgentMemory.path.like(f'%{path_suffix}'),
            ).first()
            if mem:
                cold_candidates.append(mem)

        # === FASE 2: Deletar perfis vazios (lista fixa) ===
        delete_candidates = []
        for path_suffix in EMPTY_PROFILES_TO_DELETE:
            mem = AgentMemory.query.filter(
                AgentMemory.user_id == 0,
                AgentMemory.path.like(f'%{path_suffix}'),
            ).first()
            if mem:
                content_len = len(mem.content or '')
                if content_len < 150:  # Perfil com < 150 bytes não tem informação útil
                    delete_candidates.append(mem)

        # === FASE 3: Auto-detect (opcional) ===
        auto_detected = []
        if args.auto_detect:
            noise_memories = AgentMemory.query.filter(
                AgentMemory.user_id == 0,
                AgentMemory.usage_count >= args.min_usage,
                AgentMemory.effective_count <= args.max_effective,
                AgentMemory.is_cold.is_(False),
            ).order_by(AgentMemory.usage_count.desc()).all()

            # Filtrar os que já estão na lista fixa
            fixed_paths = set(NOISE_PATHS_TO_COLD + EMPTY_PROFILES_TO_DELETE)
            for mem in noise_memories:
                path_short = mem.path.split('/memories/')[-1] if '/memories/' in mem.path else mem.path
                if not any(path_short.endswith(fp) for fp in fixed_paths):
                    auto_detected.append(mem)

        # === RELATÓRIO ===
        logger.info(f"=== {'DRY-RUN' if not args.execute else 'EXECUTANDO'} ===\n")

        logger.info(f"--- MOVER PARA COLD TIER ({len(cold_candidates)}) ---")
        for mem in cold_candidates:
            logger.info(
                f"  {mem.path[-60:]}"
                f"  usage={mem.usage_count} eff={mem.effective_count}"
                f"  len={len(mem.content or '')}b"
            )

        logger.info(f"\n--- DELETAR PERFIS VAZIOS ({len(delete_candidates)}) ---")
        for mem in delete_candidates:
            logger.info(
                f"  {mem.path[-60:]}"
                f"  usage={mem.usage_count} eff={mem.effective_count}"
                f"  len={len(mem.content or '')}b"
            )

        if auto_detected:
            logger.info(f"\n--- AUTO-DETECTADOS ({len(auto_detected)}) ---")
            for mem in auto_detected:
                logger.info(
                    f"  {mem.path[-60:]}"
                    f"  usage={mem.usage_count} eff={mem.effective_count}"
                    f"  len={len(mem.content or '')}b"
                )

        total_actions = len(cold_candidates) + len(delete_candidates)
        if not args.execute:
            logger.info(f"\nTotal de ações: {total_actions}")
            logger.info("Adicione --execute para processar.")
            return

        # === EXECUTAR ===
        cold_count = 0
        delete_count = 0

        for mem in cold_candidates:
            try:
                mem.is_cold = True
                mem.updated_at = agora_utc_naive()
                cold_count += 1
                logger.info(f"  → COLD: {mem.path[-50:]}")
            except Exception as e:
                logger.error(f"  ✗ Erro ao mover para cold: {e}")

        for mem in delete_candidates:
            try:
                db.session.delete(mem)
                delete_count += 1
                logger.info(f"  → DELETE: {mem.path[-50:]}")
            except Exception as e:
                logger.error(f"  ✗ Erro ao deletar: {e}")

        try:
            db.session.commit()
            logger.info(f"\n=== RESULTADO ===")
            logger.info(f"Movidos para cold: {cold_count}")
            logger.info(f"Deletados: {delete_count}")
            logger.info(f"Economia estimada: ~{(cold_count + delete_count) * 200}B/sessão")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro no commit: {e}")


if __name__ == '__main__':
    main()
