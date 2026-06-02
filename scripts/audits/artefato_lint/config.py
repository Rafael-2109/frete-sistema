from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "scripts" / "audits" / "artefato_lint.config.json"

@dataclass
class Config:
    raw: dict
    @property
    def managed_doc_globs(self): return self.raw["managed_doc_globs"]
    @property
    def operational_script_globs(self): return self.raw["operational_script_globs"]
    @property
    def ignore_globs(self): return self.raw["ignore_globs"]
    @property
    def toc_min_lines(self): return self.raw["toc_min_lines"]
    @property
    def hub_max_prose_lines(self): return self.raw["hub_max_prose_lines"]
    @property
    def dup_textual_block(self): return self.raw["dup_textual_block"]
    @property
    def dup_textual_report(self): return self.raw["dup_textual_report"]
    @property
    def dup_semantic_block(self): return self.raw["dup_semantic_block"]
    @property
    def banned_hedge(self): return self.raw["banned_hedge"]
    @property
    def banned_time_sensitive(self): return self.raw["banned_time_sensitive"]
    @property
    def forbidden_markers_reference(self): return self.raw["forbidden_markers_reference"]
    @property
    def required_sections(self): return self.raw["required_sections"]
    @property
    def valid_tipos(self): return self.raw["valid_tipos"]
    @property
    def valid_camadas(self): return self.raw["valid_camadas"]
    @property
    def id_hardcoded_regex(self): return self.raw["id_hardcoded_regex"]
    @property
    def schemas_tables_dir(self): return self.raw["schemas_tables_dir"]

def load(path: Path = CONFIG_PATH) -> "Config":
    return Config(json.loads(Path(path).read_text(encoding="utf-8")))
