#!/usr/bin/env python3
"""
Cria/atualiza usuario `claude-visual@bot.nacom.com.br` para uso pelo `tests/visual/capture.py`.

Idempotente — pode rodar varias vezes:
  - Cria usuario se nao existe
  - Sempre regenera senha (32 chars random)
  - Atualiza .env com UI_VISUAL_EMAIL e UI_VISUAL_PASSWORD

Permissoes: administrador + todos os flags sistema_* = True (acesso a hora,
carvia, seguranca, motochefe, logistica, lojas, etc — necessario para que
visual capture cubra todas as paginas configuradas em tests/visual/pages.yml).

Seguranca:
  - .env esta em .gitignore (linha 50). Senha NUNCA vai pro repo.
  - CLAUDE.md so referencia o script, nunca a senha.
  - Email fixo (`claude-visual@bot.nacom.com.br`) para idempotencia + facil de identificar
    nos logs como conta de bot, nao humano.

Uso:
  source .venv/bin/activate
  python scripts/seed/create_visual_test_user.py
"""

import secrets
import string
import sys
from pathlib import Path

# Permite import de app/* sem rodar via flask CLI
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db                          # noqa: E402
from app.auth.models import Usuario                     # noqa: E402
from app.utils.timezone import agora_utc_naive          # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
EMAIL = "claude-visual@bot.nacom.com.br"
NOME = "Claude Visual Test (bot)"


def generate_password(length: int = 32) -> str:
    """Senha aleatoria com letras + digitos (sem simbolos para evitar problemas
    de escape em .env e em URLs caso seja usada em algum logger)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def update_env_file(env_path: Path, email: str, password: str) -> None:
    """Atualiza .env (substitui linhas existentes ou adiciona). Preserva resto."""
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    else:
        lines = []

    new_lines = []
    seen_email = False
    seen_password = False
    for line in lines:
        if line.startswith("UI_VISUAL_EMAIL="):
            new_lines.append(f"UI_VISUAL_EMAIL={email}")
            seen_email = True
        elif line.startswith("UI_VISUAL_PASSWORD="):
            new_lines.append(f"UI_VISUAL_PASSWORD={password}")
            seen_password = True
        else:
            new_lines.append(line)
    if not seen_email:
        new_lines.append(f"UI_VISUAL_EMAIL={email}")
    if not seen_password:
        new_lines.append(f"UI_VISUAL_PASSWORD={password}")

    env_path.write_text("\n".join(new_lines) + "\n")


def main():
    senha = generate_password()

    app = create_app()
    with app.app_context():
        usuario = Usuario.query.filter_by(email=EMAIL).first()
        is_new = usuario is None
        if is_new:
            usuario = Usuario(email=EMAIL, nome=NOME)
            db.session.add(usuario)

        # Reaplica todas as flags sempre (idempotente)
        usuario.nome = NOME
        usuario.set_senha(senha)
        usuario.perfil = "administrador"
        usuario.status = "ativo"
        usuario.empresa = "Nacom Goya (visual test bot)"
        usuario.cargo = "Visual Regression Bot"
        usuario.aprovado_em = agora_utc_naive()
        usuario.aprovado_por = "system (visual test seed)"
        usuario.sistema_logistica = True
        usuario.sistema_motochefe = True
        usuario.sistema_carvia = True
        usuario.sistema_seguranca = True
        usuario.sistema_remessa_vortx = True
        usuario.sistema_lojas = True
        usuario.acesso_comissao_carvia = True
        usuario.loja_hora_id = None  # acesso a todas as lojas HORA
        usuario.observacoes = (
            "Conta de bot para tests/visual/capture.py. NAO usar para login humano. "
            "Senha rotaciona a cada execucao do scripts/seed/create_visual_test_user.py."
        )

        db.session.commit()

        action = "criado" if is_new else "atualizado"
        print(f"[seed] usuario {action}: id={usuario.id} email={usuario.email}")
        print(f"[seed]   perfil={usuario.perfil} status={usuario.status}")
        print(f"[seed]   sistemas: logistica/motochefe/carvia/seguranca/remessa_vortx/lojas/comissao_carvia=True")

    update_env_file(ENV_PATH, EMAIL, senha)
    print(f"[seed] credenciais salvas em {ENV_PATH.relative_to(ROOT)}")
    print(f"[seed] vars: UI_VISUAL_EMAIL, UI_VISUAL_PASSWORD")
    print(f"[seed] AVISO: NUNCA commitar .env")


if __name__ == "__main__":
    main()
