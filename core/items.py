"""
core/items.py
-------------
Gestão dos itens do inventário (CRUD completo).

Esse é o módulo mais crítico do CLI — representa o caso de uso UC01
(consultar item), UC02 (buscar), UC04 (localizar) e é base para o UC03
(registrar consumo, no módulo consumption).
"""

from core.storage import load_json, save_json
from core import compartments
from utils.dates import now_iso, days_until


FILENAME = "items.json"

VALID_CATEGORIES = compartments.VALID_CATEGORIES  # mesmas categorias
VALID_CRITICALITIES = ["critical", "high", "medium", "low"]
VALID_UNITS = ["unidades", "litros", "kg", "g", "pacotes", "ampolas"]


# ============================================================
# Leitura
# ============================================================

def list_all() -> list[dict]:
    """Retorna todos os itens cadastrados."""
    data = load_json(FILENAME, default=[])
    return data if isinstance(data, list) else []


def find_by_id(item_id: str) -> dict | None:
    """Busca item pelo ID. Retorna None se não existir."""
    for item in list_all():
        if item["id"] == item_id:
            return item
    return None


def search(term: str) -> list[dict]:
    """
    Busca itens cujo nome ou categoria contenham o termo (case-insensitive).
    """
    term_lower = term.lower().strip()
    if not term_lower:
        return []
    results = []
    for item in list_all():
        if (term_lower in item["name"].lower() or
                term_lower in item.get("category", "").lower() or
                term_lower in item["id"].lower()):
            results.append(item)
    return results


def list_by_compartment(compartment_id: str) -> list[dict]:
    """Lista itens armazenados em um compartimento específico."""
    return [i for i in list_all() if i.get("compartment_id") == compartment_id]


def list_by_category(category: str) -> list[dict]:
    """Lista itens de uma categoria."""
    return [i for i in list_all() if i.get("category") == category]


def list_expiring_soon(days_threshold: int = 30) -> list[dict]:
    """
    Lista itens que vencem em até X dias.
    Inclui também itens já vencidos.
    """
    results = []
    for item in list_all():
        try:
            days = days_until(item["expiry_date"])
            if days <= days_threshold:
                results.append({**item, "_days_until_expiry": days})
        except (KeyError, ValueError):
            continue  # ignora itens sem data válida
    # Ordena: mais urgentes primeiro
    results.sort(key=lambda x: x["_days_until_expiry"])
    return results


def list_low_stock(threshold_ratio: float = 0.3) -> list[dict]:
    """
    Lista itens com estoque abaixo do threshold em relação ao inicial.
    Threshold padrão: 30%.
    """
    results = []
    for item in list_all():
        initial = item.get("quantity_initial", 0)
        current = item.get("quantity", 0)
        if initial > 0 and (current / initial) <= threshold_ratio:
            results.append({
                **item,
                "_stock_ratio": current / initial,
            })
    results.sort(key=lambda x: x["_stock_ratio"])
    return results


# ============================================================
# Escrita
# ============================================================

def save_all(items: list[dict]) -> None:
    save_json(FILENAME, items)


def create(item_id: str, name: str, category: str, compartment_id: str,
           quantity: int, unit: str, expiry_date: str,
           criticality: str = "medium",
           requires_refrigeration: bool = False,
           lot_number: str = "") -> dict:
    """
    Cadastra um novo item.

    Validações:
    - ID único
    - Categoria válida
    - Compartimento existe
    - Quantidade > 0
    - Unidade conhecida
    - Criticality válida
    """
    if find_by_id(item_id):
        raise ValueError(f"Já existe item com ID {item_id}.")

    if category not in VALID_CATEGORIES:
        raise ValueError(f"Categoria inválida: {category}")

    if not compartments.find_by_id(compartment_id):
        raise ValueError(f"Compartimento {compartment_id} não existe.")

    if quantity <= 0:
        raise ValueError("Quantidade deve ser maior que zero.")

    if unit not in VALID_UNITS:
        raise ValueError(f"Unidade inválida: {unit}")

    if criticality not in VALID_CRITICALITIES:
        raise ValueError(f"Criticality inválida: {criticality}")

    item = {
        "id": item_id,
        "name": name,
        "category": category,
        "compartment_id": compartment_id,
        "quantity": quantity,
        "quantity_initial": quantity,
        "unit": unit,
        "expiry_date": expiry_date,
        "criticality": criticality,
        "requires_refrigeration": requires_refrigeration,
        "lot_number": lot_number,
        "created_at": now_iso(),
    }

    items = list_all()
    items.append(item)
    save_all(items)
    return item


def update_quantity(item_id: str, new_quantity: int) -> dict:
    """
    Atualiza a quantidade de um item.
    Usada principalmente após registro de consumo.
    """
    if new_quantity < 0:
        raise ValueError("Quantidade não pode ser negativa.")

    items = list_all()
    for item in items:
        if item["id"] == item_id:
            item["quantity"] = new_quantity
            item["updated_at"] = now_iso()
            save_all(items)
            return item
    raise ValueError(f"Item {item_id} não encontrado.")


def delete(item_id: str) -> bool:
    """Remove um item do inventário."""
    items = list_all()
    new_list = [i for i in items if i["id"] != item_id]
    if len(new_list) == len(items):
        return False
    save_all(new_list)
    return True


# ============================================================
# Estatísticas
# ============================================================

def get_stats() -> dict:
    """Calcula estatísticas agregadas do inventário."""
    items = list_all()
    total_items = len(items)
    total_quantity = sum(i.get("quantity", 0) for i in items)

    by_category = {}
    by_criticality = {}
    for item in items:
        cat = item.get("category", "?")
        crit = item.get("criticality", "medium")
        by_category[cat] = by_category.get(cat, 0) + 1
        by_criticality[crit] = by_criticality.get(crit, 0) + 1

    return {
        "total_items": total_items,
        "total_quantity": total_quantity,
        "by_category": by_category,
        "by_criticality": by_criticality,
        "expiring_soon": len(list_expiring_soon(30)),
        "low_stock": len(list_low_stock(0.3)),
    }
