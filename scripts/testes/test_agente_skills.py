#!/usr/bin/env python3
"""
Testes de Validação do Módulo Agente com Skills.

Valida que a implementação segue as melhores práticas da Anthropic:
1. Usa Skills em .claude/skills/ ao invés de Custom Tools MCP
2. Configuração correta de ClaudeAgentOptions
3. Skills têm estrutura correta (SKILL.md + scripts)

Referências:
- https://platform.claude.com/docs/pt-BR/agent-sdk/skills
- https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
- https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

Uso:
    python scripts/testes/test_agente_skills.py
"""

import sys
import os
import unittest

# Adiciona path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestSkillsStructure(unittest.TestCase):
    """Testa estrutura das Skills conforme Anthropic."""

    def test_01_skill_directory_exists(self):
        """Verifica que diretório de skills existe."""
        skill_dir = os.path.join(
            os.path.dirname(__file__), '../../.claude/skills/agente-logistico'
        )
        self.assertTrue(
            os.path.isdir(skill_dir),
            f"Diretório da skill não existe: {skill_dir}"
        )
        print("  ✓ Diretório .claude/skills/agente-logistico/ existe")

    def test_02_skill_md_exists_and_has_frontmatter(self):
        """Verifica que SKILL.md existe e tem frontmatter correto."""
        skill_md = os.path.join(
            os.path.dirname(__file__), '../../.claude/skills/agente-logistico/SKILL.md'
        )

        self.assertTrue(os.path.isfile(skill_md), f"SKILL.md não existe")

        with open(skill_md, 'r') as f:
            content = f.read()

        # Verifica frontmatter YAML
        self.assertIn('---', content, "SKILL.md deve ter frontmatter YAML")
        self.assertIn('name: agente-logistico', content, "SKILL.md deve ter name no frontmatter")
        self.assertIn('description:', content, "SKILL.md deve ter description no frontmatter")

        print("  ✓ SKILL.md tem frontmatter correto (name, description)")

    def test_03_skill_scripts_exist(self):
        """Verifica que scripts da skill existem."""
        scripts_dir = os.path.join(
            os.path.dirname(__file__), '../../.claude/skills/agente-logistico/scripts'
        )

        # Scripts esperados conforme SKILL.md
        expected_scripts = [
            'analisando_disponibilidade.py',
            'consultando_pedidos.py',
            'consultando_estoque.py',
            'calculando_prazo.py',
            'analisando_programacao.py',
            'resolver_entidades.py',
        ]

        for script in expected_scripts:
            script_path = os.path.join(scripts_dir, script)
            self.assertTrue(
                os.path.isfile(script_path),
                f"Script {script} não existe"
            )
            print(f"  ✓ Script existe: {script}")


class TestNoDuplicateTools(unittest.TestCase):
    """Verifica que não há Custom Tools MCP duplicando Skills."""

    def test_01_no_mcp_server_file(self):
        """Verifica que mcp_server.py foi removido."""
        mcp_file = os.path.join(
            os.path.dirname(__file__), '../../app/agente/tools/mcp_server.py'
        )
        self.assertFalse(
            os.path.isfile(mcp_file),
            "mcp_server.py NÃO deve existir (Custom Tools duplicam Skills)"
        )
        print("  ✓ mcp_server.py não existe (correto!)")

    def test_02_no_registry_file(self):
        """Verifica que registry.py foi removido."""
        registry_file = os.path.join(
            os.path.dirname(__file__), '../../app/agente/tools/registry.py'
        )
        self.assertFalse(
            os.path.isfile(registry_file),
            "registry.py NÃO deve existir (desnecessário com Skills)"
        )
        print("  ✓ registry.py não existe (correto!)")

    def test_03_no_carteira_tools_file(self):
        """Verifica que carteira_tools.py foi removido."""
        tools_file = os.path.join(
            os.path.dirname(__file__), '../../app/agente/tools/carteira_tools.py'
        )
        self.assertFalse(
            os.path.isfile(tools_file),
            "carteira_tools.py NÃO deve existir (duplica Skills)"
        )
        print("  ✓ carteira_tools.py não existe (correto!)")


class TestClientConfiguration(unittest.TestCase):
    """Testa configuração do AgentClient conforme Anthropic."""

    def test_01_client_has_skill_in_allowed_tools(self):
        """Verifica que 'Skill' está em allowed_tools."""
        client_file = os.path.join(
            os.path.dirname(__file__), '../../app/agente/sdk/client.py'
        )

        with open(client_file, 'r') as f:
            content = f.read()

        # Verifica que Skill está configurado
        self.assertIn('"Skill"', content, "client.py deve ter 'Skill' em allowed_tools")
        print("  ✓ 'Skill' está em allowed_tools")

    def test_02_client_has_setting_sources(self):
        """Verifica que setting_sources está configurado."""
        client_file = os.path.join(
            os.path.dirname(__file__), '../../app/agente/sdk/client.py'
        )

        with open(client_file, 'r') as f:
            content = f.read()

        # Verifica setting_sources
        self.assertIn('setting_sources', content, "client.py deve configurar setting_sources")
        self.assertIn('["project"]', content, "setting_sources deve incluir 'project'")
        print("  ✓ setting_sources=['project'] configurado")

    def test_03_client_does_not_import_mcp_server(self):
        """Verifica que client.py NÃO importa mcp_server."""
        client_file = os.path.join(
            os.path.dirname(__file__), '../../app/agente/sdk/client.py'
        )

        with open(client_file, 'r') as f:
            content = f.read()

        # Verifica que NÃO há import do mcp_server
        self.assertNotIn('from ..tools.mcp_server', content, "client.py NÃO deve importar mcp_server")
        self.assertNotIn('get_mcp_server', content, "client.py NÃO deve usar get_mcp_server")
        self.assertNotIn('TOOLS_DISPONIVEIS', content, "client.py NÃO deve usar TOOLS_DISPONIVEIS")
        print("  ✓ Não importa mcp_server (correto!)")


class TestSettings(unittest.TestCase):
    """Testa configurações do agente."""

    def test_01_settings_has_correct_tools(self):
        """Verifica que settings tem tools corretas para Skills."""
        settings_file = os.path.join(
            os.path.dirname(__file__), '../../app/agente/config/settings.py'
        )

        with open(settings_file, 'r') as f:
            content = f.read()

        # Verifica tools corretas
        self.assertIn("'Skill'", content, "settings deve ter 'Skill' em tools_enabled")
        self.assertIn("'Bash'", content, "settings deve ter 'Bash' em tools_enabled")

        # Verifica que NÃO tem tools MCP antigas
        self.assertNotIn("'consultar_pedidos'", content.replace('# ', '#'),
                        "settings NÃO deve ter tools MCP antigas")
        print("  ✓ Settings tem tools corretas para Skills")


def run_tests():
    """Executa todos os testes."""
    print("\n" + "="*70)
    print("🧪 VALIDAÇÃO: Módulo Agente com Skills (Anthropic Best Practices)")
    print("="*70 + "\n")

    # Carrega testes
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Adiciona classes de teste
    suite.addTests(loader.loadTestsFromTestCase(TestSkillsStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestNoDuplicateTools))
    suite.addTests(loader.loadTestsFromTestCase(TestClientConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestSettings))

    # Executa
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO DA VALIDAÇÃO")
    print("="*70)
    print(f"Testes executados: {result.testsRun}")
    print(f"Falhas: {len(result.failures)}")
    print(f"Erros: {len(result.errors)}")
    print(f"Conformidade: {'✅ APROVADO' if result.wasSuccessful() else '❌ REPROVADO'}")
    print("="*70)

    if result.wasSuccessful():
        print("\n✅ Implementação segue as melhores práticas da Anthropic!")
        print("   - Skills em .claude/skills/agente-logistico/")
        print("   - Sem Custom Tools MCP duplicadas")
        print("   - ClaudeAgentOptions configurado corretamente")
    else:
        print("\n❌ Problemas encontrados. Verifique os erros acima.")

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
