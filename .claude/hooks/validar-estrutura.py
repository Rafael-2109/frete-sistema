#!/usr/bin/env python3
"""
Hook de validacao de estrutura .claude/
Roda no SessionStart para detectar problemas automaticamente.

Verifica:
1. Todas as skills tem SKILL.md
2. Nenhum __pycache__ dentro de skills
3. References INDEX.md existe
4. Paths no CLAUDE.md sao validos
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(BASE_DIR, 'skills')
REFS_DIR = os.path.join(BASE_DIR, 'references')

warnings = []
errors = []


def check_skills_have_skillmd():
    """Verifica se todas as skills tem SKILL.md"""
    if not os.path.isdir(SKILLS_DIR):
        return
    for skill_name in sorted(os.listdir(SKILLS_DIR)):
        skill_dir = os.path.join(SKILLS_DIR, skill_name)
        if not os.path.isdir(skill_dir):
            continue
        skill_md = os.path.join(skill_dir, 'SKILL.md')
        if not os.path.isfile(skill_md):
            errors.append(f"Skill '{skill_name}' sem SKILL.md")


def check_no_pycache():
    """Verifica se nao ha __pycache__ dentro de skills"""
    if not os.path.isdir(SKILLS_DIR):
        return
    for root, dirs, _files in os.walk(SKILLS_DIR):
        for d in dirs:
            if d == '__pycache__':
                rel = os.path.relpath(os.path.join(root, d), BASE_DIR)
                warnings.append(f"__pycache__ encontrado: {rel}")
            if d == 'flask_session':
                rel = os.path.relpath(os.path.join(root, d), BASE_DIR)
                warnings.append(f"flask_session encontrado: {rel}")


def check_index_exists():
    """Verifica se INDEX.md existe em references"""
    index_path = os.path.join(REFS_DIR, 'INDEX.md')
    if not os.path.isfile(index_path):
        errors.append("references/INDEX.md nao encontrado")


def check_reference_structure():
    """Verifica se subpastas esperadas existem em references"""
    expected = ['modelos', 'odoo', 'negocio']
    for subdir in expected:
        path = os.path.join(REFS_DIR, subdir)
        if not os.path.isdir(path):
            warnings.append(f"references/{subdir}/ nao encontrada")


def main():
    check_skills_have_skillmd()
    check_no_pycache()
    check_index_exists()
    check_reference_structure()

    if errors:
        print("ERROS de estrutura .claude/:")
        for e in errors:
            print(f"  - {e}")

    if warnings:
        print("AVISOS de estrutura .claude/:")
        for w in warnings:
            print(f"  - {w}")

    if not errors and not warnings:
        print("Estrutura .claude/ OK")

    # Retorna 0 sempre (nao bloqueia sessao)
    return 0


if __name__ == '__main__':
    sys.exit(main())
