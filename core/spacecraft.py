"""
core/spacecraft.py
------------------
Gestão da Cápsula Dragon (entidade única — uma instalação = uma cápsula).
"""

from core.storage import load_json, save_json
from utils.dates import now_iso


FILENAME = "spacecraft.json"


def get_spacecraft() -> dict:
    """
    Retorna o registro da cápsula atual.
    Se ainda não houver registro, retorna um dicionário vazio.
    """
    data = load_json(FILENAME, default={})
    return data if isinstance(data, dict) else {}


def save_spacecraft(spacecraft: dict) -> None:
    """Salva o registro da cápsula."""
    save_json(FILENAME, spacecraft)


def create_spacecraft(spacecraft_id: str, mission_name: str,
                      crew_size: int, status: str = "in_transit") -> dict:
    """
    Cadastra a cápsula pela primeira vez.
    """
    spacecraft = {
        "id": spacecraft_id,
        "mission_name": mission_name,
        "mission_start": now_iso(),
        "crew_size": crew_size,
        "status": status,
        "created_at": now_iso(),
    }
    save_spacecraft(spacecraft)
    return spacecraft


def update_spacecraft(**fields) -> dict:
    """
    Atualiza campos específicos da cápsula.
    Levanta ValueError se a cápsula ainda não foi cadastrada.
    """
    spacecraft = get_spacecraft()
    if not spacecraft:
        raise ValueError(
            "Cápsula ainda não cadastrada. Use create_spacecraft primeiro."
        )

    # Campos imutáveis (não podem ser sobrescritos por update)
    immutable = {"id", "created_at", "mission_start"}

    for key, value in fields.items():
        if key in immutable:
            continue
        spacecraft[key] = value

    spacecraft["updated_at"] = now_iso()
    save_spacecraft(spacecraft)
    return spacecraft


# Valores válidos para status
VALID_STATUSES = ["in_transit", "docked", "returning", "pre_launch"]
