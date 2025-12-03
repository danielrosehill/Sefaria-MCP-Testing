"""
Sefaria Explorer Personas

Different AI personalities for exploring Jewish texts, each with their own
perspective and specialty.
"""

from .ashkenazi_rabbi import SYSTEM_PROMPT as ASHKENAZI_PROMPT, PERSONA_NAME as ASHKENAZI_NAME, PERSONA_DESCRIPTION as ASHKENAZI_DESC
from .sephardi_rabbi import SYSTEM_PROMPT as SEPHARDI_PROMPT, PERSONA_NAME as SEPHARDI_NAME, PERSONA_DESCRIPTION as SEPHARDI_DESC
from .generalist import SYSTEM_PROMPT as GENERALIST_PROMPT, PERSONA_NAME as GENERALIST_NAME, PERSONA_DESCRIPTION as GENERALIST_DESC
from .halacha_specialist import SYSTEM_PROMPT as HALACHA_PROMPT, PERSONA_NAME as HALACHA_NAME, PERSONA_DESCRIPTION as HALACHA_DESC
from .tanakh_source_finder import SYSTEM_PROMPT as TANAKH_PROMPT, PERSONA_NAME as TANAKH_NAME, PERSONA_DESCRIPTION as TANAKH_DESC

PERSONAS = {
    "ashkenazi": {
        "name": ASHKENAZI_NAME,
        "description": ASHKENAZI_DESC,
        "system_prompt": ASHKENAZI_PROMPT,
        "icon": "ashkenazi"
    },
    "sephardi": {
        "name": SEPHARDI_NAME,
        "description": SEPHARDI_DESC,
        "system_prompt": SEPHARDI_PROMPT,
        "icon": "sephardi"
    },
    "generalist": {
        "name": GENERALIST_NAME,
        "description": GENERALIST_DESC,
        "system_prompt": GENERALIST_PROMPT,
        "icon": "books"
    },
    "halacha": {
        "name": HALACHA_NAME,
        "description": HALACHA_DESC,
        "system_prompt": HALACHA_PROMPT,
        "icon": "gavel"
    },
    "tanakh": {
        "name": TANAKH_NAME,
        "description": TANAKH_DESC,
        "system_prompt": TANAKH_PROMPT,
        "icon": "scroll"
    }
}

DEFAULT_PERSONA = "generalist"

def get_persona(persona_key: str) -> dict:
    """Get a persona by key, defaulting to generalist if not found."""
    return PERSONAS.get(persona_key, PERSONAS[DEFAULT_PERSONA])

def list_personas() -> list:
    """Return a list of all available persona keys."""
    return list(PERSONAS.keys())
