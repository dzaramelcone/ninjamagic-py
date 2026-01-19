from dataclasses import fields, is_dataclass

from ninjamagic.component import Noun, Weapon

REGISTRY = {
    "Noun": Noun,
    "Weapon": Weapon,
}

_SKIP_FIELDS = {"match_tokens"}


def dump_item_spec(components: list[object]) -> list[dict]:
    spec: list[dict] = []
    for comp in components:
        kind = type(comp).__name__
        if is_dataclass(comp):
            data = {
                field.name: getattr(comp, field.name)
                for field in fields(comp)
                if field.name not in _SKIP_FIELDS
            }
            spec.append({"kind": kind, **data})
        else:
            spec.append({"kind": kind})
    return spec


def load_item_spec(spec: list[dict]) -> list[object]:
    out: list[object] = []
    for entry in spec:
        kind = entry.get("kind")
        if not kind:
            raise ValueError("item spec missing kind")
        cls = REGISTRY.get(kind)
        if cls is None:
            raise ValueError(f"unknown item component: {kind}")
        if is_dataclass(cls):
            field_names = {field.name for field in fields(cls)}
            data = {key: value for key, value in entry.items() if key in field_names}
            out.append(cls(**data))
        else:
            out.append(cls())
    return out
