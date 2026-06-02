from __future__ import annotations
import re
from dataclasses import dataclass, field

DOC_BLOCK = re.compile(r"<!--\s*doc:meta\s*(.*?)-->", re.DOTALL)
YAML_BLOCK = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)
KV = re.compile(r"^\s*([\w-]+)\s*:\s*(.*?)\s*$")
SCRIPT_KV = re.compile(r"^#\s*([\w-]+)\s*:\s*(.*?)\s*$")

@dataclass
class Meta:
    found: bool
    fields: dict = field(default_factory=dict)
    source: str = ""  # "html" | "yaml" | "script" | ""

def _kv_block(text: str, pattern) -> dict:
    out = {}
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out

def parse_doc(content: str) -> Meta:
    m = DOC_BLOCK.search(content)
    if m:
        return Meta(True, _kv_block(m.group(1), KV), "html")
    y = YAML_BLOCK.search(content)
    if y:
        f = _kv_block(y.group(1), KV)
        if "tipo" in f or "name" in f:
            return Meta(True, f, "yaml")
    return Meta(False, {}, "")

def parse_script(content: str) -> Meta:
    f = _kv_block(content, SCRIPT_KV)
    return Meta(bool(f), f, "script") if f else Meta(False, {}, "")
