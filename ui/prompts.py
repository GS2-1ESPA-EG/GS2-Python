"""
ui/prompts.py
-------------
Funções de input com validação. Cada função abaixo retorna um tipo
garantido e bem-formado, ou levanta KeyboardInterrupt se o operador
cancelar (Ctrl+C).

Usar essas funções (em vez de input() puro) protege o resto do código
de receber lixo do operador — toda a validação fica concentrada aqui.
"""

from datetime import datetime
from ui.display import colored, Color, error


# ============================================================
# Strings
# ============================================================

def ask_text(label: str, required: bool = True, default: str = None) -> str:
    """
    Pede um texto ao operador.
    Se default for fornecido, pode ser usado pressionando ENTER vazio.
    """
    hint = f" [{default}]" if default else ""
    prompt = colored(f"  {label}{hint}: ", Color.CYAN)

    while True:
        value = input(prompt).strip()
        if not value:
            if default is not None:
                return default
            if not required:
                return ""
            error("Esse campo é obrigatório.")
            continue
        return value


def ask_choice(label: str, options: list[str], default: str = None) -> str:
    """
    Pede ao operador para escolher uma opção de uma lista.
    Mostra as opções e aceita tanto o índice quanto o valor literal.
    """
    print(colored(f"  {label}", Color.CYAN))
    for i, opt in enumerate(options, 1):
        marker = " (padrão)" if opt == default else ""
        print(colored(f"    [{i}] {opt}{marker}", Color.WHITE))

    while True:
        raw = input(colored("  > ", Color.CYAN)).strip()

        # ENTER vazio = padrão
        if not raw and default is not None:
            return default

        # Tenta como índice
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
            error(f"Índice inválido. Use 1 a {len(options)}.")
            continue

        # Tenta como valor literal (case-insensitive)
        for opt in options:
            if opt.lower() == raw.lower():
                return opt

        error("Opção inválida. Digite o número ou o nome exato.")


# ============================================================
# Números
# ============================================================

def ask_int(label: str, min_value: int = None, max_value: int = None,
            default: int = None) -> int:
    """Pede um inteiro, validando faixa."""
    hint = f" [{default}]" if default is not None else ""
    prompt = colored(f"  {label}{hint}: ", Color.CYAN)

    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            value = int(raw)
        except ValueError:
            error("Digite um número inteiro válido.")
            continue
        if min_value is not None and value < min_value:
            error(f"Valor mínimo permitido é {min_value}.")
            continue
        if max_value is not None and value > max_value:
            error(f"Valor máximo permitido é {max_value}.")
            continue
        return value


def ask_float(label: str, min_value: float = None, max_value: float = None,
              default: float = None) -> float:
    """Pede um float, validando faixa. Aceita vírgula ou ponto."""
    hint = f" [{default}]" if default is not None else ""
    prompt = colored(f"  {label}{hint}: ", Color.CYAN)

    while True:
        raw = input(prompt).strip().replace(",", ".")
        if not raw and default is not None:
            return default
        try:
            value = float(raw)
        except ValueError:
            error("Digite um número válido (ex.: 25.5).")
            continue
        if min_value is not None and value < min_value:
            error(f"Valor mínimo permitido é {min_value}.")
            continue
        if max_value is not None and value > max_value:
            error(f"Valor máximo permitido é {max_value}.")
            continue
        return value


# ============================================================
# Datas
# ============================================================

def ask_date(label: str, default: str = None) -> str:
    """
    Pede uma data no formato DD/MM/YYYY.
    Retorna no formato ISO 8601 (YYYY-MM-DD).
    """
    hint = f" [{default}]" if default else " (DD/MM/YYYY)"
    prompt = colored(f"  {label}{hint}: ", Color.CYAN)

    while True:
        raw = input(prompt).strip()
        if not raw and default:
            return default
        try:
            dt = datetime.strptime(raw, "%d/%m/%Y")
            return dt.date().isoformat()
        except ValueError:
            error("Data inválida. Use o formato DD/MM/YYYY (ex.: 31/12/2026).")


# ============================================================
# Booleano (S/N)
# ============================================================

def ask_yes_no(label: str, default: bool = False) -> bool:
    """Pergunta sim/não. ENTER vazio = default."""
    suffix = "[S/n]" if default else "[s/N]"
    prompt = colored(f"  {label} {suffix}: ", Color.CYAN)

    while True:
        raw = input(prompt).strip().lower()
        if not raw:
            return default
        if raw in ("s", "sim", "y", "yes"):
            return True
        if raw in ("n", "nao", "não", "no"):
            return False
        error("Responda S (sim) ou N (não).")


# ============================================================
# Confirmação destrutiva
# ============================================================

def confirm_destructive(action: str) -> bool:
    """
    Confirmação explícita para ações destrutivas (deletar, sobrescrever).
    Exige digitar a palavra CONFIRMAR para prosseguir.
    """
    print(colored(f"  ⚠ {action}", Color.YELLOW, bold=True))
    print(colored('  Digite "CONFIRMAR" para prosseguir, ou ENTER para cancelar:', Color.DIM))
    raw = input(colored("  > ", Color.CYAN)).strip()
    return raw.upper() == "CONFIRMAR"
