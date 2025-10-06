from enum import StrEnum


class Person(StrEnum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"


PROSE = Story(
    """{{ subj }} {{ be }} {{ a hush-lit wanderer }} beneath a {{ syrupy }} moon;
{{ the city's breath }} threads through {{ refl }}, and {{ subj|lower }} {{ breathe }} it back,
cradling {{ poss }} secret like {{ warm embered glass }}.""",
    psubs={
        Person.FIRST: {
            "subj": "I",
            "obj": "me",
            "poss": "my",
            "refl": "myself",
            "be": "am",
            "breathe": "breathe",
        },
        Person.SECOND: {
            "subj": "You",
            "obj": "you",
            "poss": "your",
            "refl": "yourself",
            "be": "are",
            "breathe": "breathe",
        },
        Person.THIRD: {
            "subj": "She",
            "obj": "her",
            "poss": "her",
            "refl": "herself",
            "be": "is",
            "breathe": "breathes",
        },
    },
    kwsubs={
        "a hush-lit wanderer": [
            "a hush-lit vagabond",
            "a noctilucent stroller",
            "a lamplit peripatetic",
            "a gloaming-bent roamer",
        ],
        "the city's breath": [
            "the city's tide of breath",
            "the boroughs' slow exhale",
            "the metropolis' warm respiration",
            "the avenues' susurrus",
        ],
        "warm embered glass": [
            "banked emberglass",
            "palm-sunk emberlight",
            "auric furnaceglass",
            "lambent emberglass",
        ],
        Scalar("syrupy"): [
            "soft",
            "mellow",
            "honeyed",
            "silken",
            "mellifluous",
            "unctuous",
            "ambrosial",
            "saccharine",
            "nectareous",
            "oleaginous",
            "sucrose-glazed",
            "effulgent",
            "opalescent",
            "iridescent",
            "lambent",
            "incandescent",
            "delitescent",
            "pulchritudinous",
            "crepuscular",
            "susurrous",
            "oneiric",
            "ebullient",
            "refulgent",
        ],
    },
)


def _scalar_sub(word: str, scalar: float) -> str:
    return kwsubs[word][len(kwsubs[word]) * scalar]


first, third = PROSE.render(Person.FIRST, Person.THIRD, syrupy=0.25)
