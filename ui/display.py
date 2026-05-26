"""
ui/display.py
-------------
Funções de exibição no terminal: cores ANSI, tabelas formatadas, banners.

Não usa bibliotecas externas (rich, colorama) para manter o CLI 100%
auto-contido — alinhado ao princípio de bordo: zero dependências externas
em caso de falha de comunicação.
"""

import os
import shutil


# ============================================================
# Cores ANSI
# ============================================================

class Color:
    """Códigos ANSI para cores e estilos no terminal."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Cores de texto
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Cores de fundo
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def colored(text: str, color: str, bold: bool = False) -> str:
    """Aplica cor (e opcionalmente negrito) a um texto."""
    prefix = Color.BOLD if bold else ""
    return f"{prefix}{color}{text}{Color.RESET}"


# ============================================================
# Helpers de severidade (usados em alertas, validade, estoque)
# ============================================================

def color_by_criticality(criticality: str) -> str:
    """Retorna a cor adequada para um nível de criticidade."""
    mapping = {
        "critical": Color.RED,
        "high": Color.YELLOW,
        "medium": Color.CYAN,
        "low": Color.WHITE,
    }
    return mapping.get(criticality, Color.WHITE)


def color_by_severity(severity: str) -> str:
    """Retorna a cor adequada para a severidade de um alerta."""
    mapping = {
        "critical": Color.RED,
        "warning": Color.YELLOW,
        "info": Color.CYAN,
    }
    return mapping.get(severity, Color.WHITE)


def stock_status(quantity: int, initial: int) -> tuple[str, str]:
    """
    Retorna (símbolo, cor) representando o estado do estoque.
    Útil para barras visuais de quantidade.
    """
    if initial == 0:
        return "?", Color.DIM
    ratio = quantity / initial
    if ratio >= 0.6:
        return "OK", Color.GREEN
    elif ratio >= 0.3:
        return "ATENÇÃO", Color.YELLOW
    else:
        return "BAIXO", Color.RED


# ============================================================
# Banners e separadores
# ============================================================

def terminal_width() -> int:
    """Largura atual do terminal (com fallback para 80)."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def clear_screen() -> None:
    """Limpa a tela do terminal (multiplataforma)."""
    os.system("cls" if os.name == "nt" else "clear")


def hr(char: str = "─") -> str:
    """Linha horizontal do tamanho do terminal."""
    return char * terminal_width()


def banner(title: str, subtitle: str = "") -> None:
    """Imprime um banner destacado no topo da tela."""
    width = terminal_width()
    print()
    print(colored("═" * width, Color.BLUE))
    print(colored(f"  {title}", Color.CYAN, bold=True))
    if subtitle:
        print(colored(f"  {subtitle}", Color.DIM))
    print(colored("═" * width, Color.BLUE))
    print()


def section(title: str) -> None:
    """Cabeçalho de seção dentro de uma tela."""
    print()
    print(colored(f"  ▸ {title}", Color.CYAN, bold=True))
    print(colored("  " + "─" * (len(title) + 4), Color.DIM))


# ============================================================
# Tabelas
# ============================================================

def print_table(headers: list[str], rows: list[list[str]],
                col_widths: list[int] = None) -> None:
    """
    Imprime uma tabela ASCII com cabeçalho e linhas.

    Se col_widths não for fornecido, calcula automaticamente baseado
    no conteúdo mais largo de cada coluna.
    """
    if not rows:
        print(colored("  (sem registros)", Color.DIM))
        return

    # Calcula larguras se não fornecidas
    if col_widths is None:
        col_widths = []
        for i in range(len(headers)):
            max_w = len(strip_ansi(headers[i]))
            for row in rows:
                if i < len(row):
                    max_w = max(max_w, len(strip_ansi(str(row[i]))))
            col_widths.append(max_w + 2)

    # Linha de cima
    top = "┌" + "┬".join("─" * w for w in col_widths) + "┐"
    sep = "├" + "┼".join("─" * w for w in col_widths) + "┤"
    bot = "└" + "┴".join("─" * w for w in col_widths) + "┘"

    print(colored(top, Color.DIM))

    # Cabeçalho
    header_cells = []
    for i, h in enumerate(headers):
        padding = col_widths[i] - len(strip_ansi(h)) - 1
        header_cells.append(" " + colored(h, Color.CYAN, bold=True) + " " * padding)
    print(colored("│", Color.DIM) +
          colored("│", Color.DIM).join(header_cells) +
          colored("│", Color.DIM))

    print(colored(sep, Color.DIM))

    # Linhas
    for row in rows:
        cells = []
        for i, val in enumerate(row):
            val_str = str(val) if i < len(row) else ""
            padding = col_widths[i] - len(strip_ansi(val_str)) - 1
            if padding < 0:
                # Trunca se muito longo
                visible_len = col_widths[i] - 2
                val_str = val_str[:visible_len - 1] + "…"
                padding = 1
            cells.append(" " + val_str + " " * padding)
        print(colored("│", Color.DIM) +
              colored("│", Color.DIM).join(cells) +
              colored("│", Color.DIM))

    print(colored(bot, Color.DIM))


def strip_ansi(text: str) -> int:
    """Remove códigos ANSI para cálculo correto de largura visível."""
    import re
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)


# ============================================================
# Feedback de operações
# ============================================================

def success(msg: str) -> None:
    print(colored(f"  ✓ {msg}", Color.GREEN, bold=True))


def error(msg: str) -> None:
    print(colored(f"  ✗ {msg}", Color.RED, bold=True))


def warning(msg: str) -> None:
    print(colored(f"  ⚠ {msg}", Color.YELLOW, bold=True))


def info(msg: str) -> None:
    print(colored(f"  ℹ {msg}", Color.CYAN))


def pause() -> None:
    """Pausa esperando ENTER. Usado entre telas."""
    print()
    input(colored("  Pressione ENTER para continuar...", Color.DIM))
