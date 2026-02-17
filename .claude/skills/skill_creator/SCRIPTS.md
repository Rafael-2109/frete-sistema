# Scripts — Skill Creator (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Nao requer ambiente virtual (scripts nao usam dependencias do projeto Flask).
Excecao: `quick_validate.py` requer `pyyaml`.

---

## 1. init_skill.py

**Proposito:** Cria uma nova skill a partir de template. Gera diretorio com SKILL.md, scripts/, references/ e assets/ com arquivos de exemplo.

```bash
python .claude/skills/skill_creator/scripts/init_skill.py <skill-name> --path <path>
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `<skill-name>` | Nome da skill em hyphen-case (OBRIGATORIO, posicional) | `data-analyzer` |
| `--path` | Diretorio onde criar a skill (OBRIGATORIO) | `--path skills/public` |

**Regras de nome:**
- Apenas letras minusculas, digitos e hifens
- Max 40 caracteres
- Nao pode comecar/terminar com hifen ou ter hifens consecutivos

**Arquivos criados:**
- `{path}/{skill-name}/SKILL.md` — Template com frontmatter YAML + secoes TODO
- `{path}/{skill-name}/scripts/example.py` — Script Python de exemplo (executavel)
- `{path}/{skill-name}/references/api_reference.md` — Doc de referencia de exemplo
- `{path}/{skill-name}/assets/example_asset.txt` — Placeholder de assets

**Output:** Texto livre com status de criacao (nao JSON). Exit code 0 = sucesso, 1 = erro.

---

## 2. package_skill.py

**Proposito:** Empacota uma skill em arquivo `.skill` (formato ZIP) para distribuicao. Executa validacao automatica antes de empacotar.

```bash
python .claude/skills/skill_creator/scripts/package_skill.py <path/to/skill-folder> [output-directory]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `<path/to/skill-folder>` | Caminho do diretorio da skill (OBRIGATORIO, posicional) | `skills/public/my-skill` |
| `[output-directory]` | Diretorio de saida (opcional, default: CWD) | `./dist` |

**Pipeline:**
1. Valida existencia do diretorio e SKILL.md
2. Executa `quick_validate.py` (frontmatter YAML)
3. Cria arquivo ZIP com extensao `.skill`

**Output:** Texto livre com lista de arquivos adicionados. Exit code 0 = sucesso, 1 = erro.

---

## 3. quick_validate.py

**Proposito:** Valida estrutura de uma skill (SKILL.md + frontmatter YAML). Verifica existencia do arquivo, formato do frontmatter, campos obrigatorios e convencoes de nomes.

```bash
python .claude/skills/skill_creator/scripts/quick_validate.py <skill_directory>
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `<skill_directory>` | Caminho do diretorio da skill (OBRIGATORIO, posicional) | `.claude/skills/minha-skill` |

**Validacoes realizadas:**

| Validacao | Descricao |
|-----------|-----------|
| SKILL.md existe | Verifica presenca do arquivo |
| Frontmatter YAML | Verifica `---` delimitadores e YAML valido |
| Campos obrigatorios | `name` e `description` devem existir |
| Propriedades permitidas | Apenas: name, description, license, allowed-tools, metadata |
| Nome hyphen-case | Letras minusculas, digitos e hifens. Max 64 caracteres |
| Descricao limpa | Sem angle brackets (`<>`). Max 1024 caracteres |

**Output:** Mensagem de texto ("Skill is valid!" ou descricao do erro). Exit code 0 = valido, 1 = invalido.

**Dependencia:** `pyyaml` (para `yaml.safe_load`).
