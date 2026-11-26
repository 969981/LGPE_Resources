"""LGPE 1.0.2 verified image lookup; resource naming is not a native selector proof."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json, re

POKE = re.compile(r"poke_icon_(\d{3})_(\d{2})([smfn])_([a-z])")
ITEM = re.compile(r"item_(\d{4})")
TYPE = re.compile(r"typeIcon_(text_)?(\d{2})_([a-z]+)_00")
LANGS = ("jpn","eng","fre","ger","ita","kor","sch","spa","tch")
def resource_key(name):
    return name[:-2] if name.endswith(("^j","^u")) else name

@dataclass(frozen=True)
class ImageResource:
    group: str
    name: str
    key: str
    source: str
    bntx_sha256: str
    brti_index: int
    rgba_sha256: str
    width: int
    height: int
    format_code: int
    pixel_evidence: str = "PNG_ROUNDTRIP_OK"

class LGPEPokemonImageResolver:
    def __init__(self, resources):
        self._index = {}
        for r in resources:
            m=POKE.fullmatch(r.key)
            if not m: raise ValueError(r.key)
            species,form,sex,palette=m.groups()
            k=(int(species),int(form),sex,palette)
            if k in self._index: raise ValueError("duplicate Pokemon key")
            self._index[k]=r
    def resolve(self, species, form, gender_symbol, palette_symbol="n"):
        """Exact resource key only. Caller must explicitly choose resource symbols."""
        return self._index.get((species,form,gender_symbol,palette_symbol))
    def candidates(self, species, form=None):
        return tuple(r for (s,f,g,p),r in sorted(self._index.items()) if s==species and (form is None or f==form))

class LGPEItemImageResolver:
    def __init__(self, resources):
        self._index={}
        self.dummy=None
        for r in resources:
            if r.key=="item_dummy":
                if self.dummy is not None: raise ValueError("duplicate dummy")
                self.dummy=r
                continue
            m=ITEM.fullmatch(r.key)
            if not m: raise ValueError(r.key)
            n=int(m[1])
            if n in self._index: raise ValueError("duplicate item")
            self._index[n]=r
    def resolve(self, resource_id):
        return self._index.get(resource_id)

class LGPETypeImageResolver:
    def __init__(self, resources):
        self._index={}
        for r in resources:
            m=TYPE.fullmatch(r.key)
            if not m or r.group not in LANGS: raise ValueError(r.key)
            k=(r.group,int(m[2]),bool(m[1]))
            if k in self._index: raise ValueError("duplicate type")
            self._index[k]=r
    def resolve(self, icon_index, language, text=False):
        return self._index.get((language,icon_index,text))

class LGPEImageResourceCore:
    def __init__(self, report):
        self.resources=[]
        if len(report["cases"])!=11: raise ValueError("incomplete report")
        counts={"pokemon":221,"item":180,**dict.fromkeys(LANGS,36)}
        seen=set()
        for c in report["cases"]:
            group=c["group"]
            if group in seen or c["status"]!="PASS" or not c.get("name_match") or len(c["textures"])!=counts.get(group): raise ValueError("invalid case")
            seen.add(group)
            for t in c["textures"]:
                if t["status"]!="PNG_ROUNDTRIP_OK": raise ValueError("unverified image")
                if t["format_code"] in (0x2001,0x2006) and not t.get("bc7_pillow_exact"): raise ValueError("BC7 parity failure")
                self.resources.append(ImageResource(group,t["name"],resource_key(t["name"]),c["source"],c["bntx_sha256"],t["index"],t["rgba_sha256"],t["width"],t["height"],t["format_code"]))
        self.pokemon=LGPEPokemonImageResolver(r for r in self.resources if r.group=="pokemon")
        self.item=LGPEItemImageResolver(r for r in self.resources if r.group=="item")
        self.type=LGPETypeImageResolver(r for r in self.resources if r.group in LANGS)
    @classmethod
    def from_path(cls,path):
        return cls(json.loads(Path(path).read_text(encoding="utf8")))
