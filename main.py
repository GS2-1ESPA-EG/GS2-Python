"""
main.py
-------
OrbitStock — Sistema CLI de Bordo (Backup Offline)
Global Solution 2026 · FIAP Engenharia de Software

Entry point principal. Roda o loop de menu até o usuário escolher sair.

Como executar:
    python3 main.py

Para popular com dados de exemplo (Dragon C209):
    python3 seed_data.py
"""

import sys

from ui import menu
from ui import display
from ui.display import Color, colored


# Mapeia opção do menu -> função
MENU_HANDLERS = {
    "1": menu.screen_list_inventory,
    "2": menu.screen_search,
    "3": menu.screen_register_consumption,
    "4": menu.screen_create_item,
    "5": menu.screen_compartments,
    "6": menu.screen_alerts,
    "7": menu.screen_consumption_history,
    "8": menu.screen_stats,
    "9": menu.screen_config,
}


def main() -> int:
    """Loop principal. Retorna o exit code do programa."""
    try:
        while True:
            try:
                choice = menu.main_menu().strip()
            except (KeyboardInterrupt, EOFError):
                print()
                display.info("Saindo do OrbitStock.")
                return 0

            if choice == "0":
                display.info("Encerrando. Telemetria sincronizada com terra "
                             "na próxima janela.")
                return 0

            handler = MENU_HANDLERS.get(choice)
            if handler is None:
                display.error(f"Opção inválida: '{choice}'.")
                display.pause()
                continue

            try:
                handler()
            except KeyboardInterrupt:
                # Ctrl+C em um sub-menu volta ao menu principal
                print()
                display.info("Operação cancelada.")
                display.pause()
            except Exception as e:
                # Captura erros inesperados sem derrubar o programa
                display.error(f"Erro inesperado: {e}")
                display.error("O CLI continua operacional. Reporte ao operador.")
                display.pause()

    except Exception as fatal:
        # Erro irrecuperável
        print(colored(f"\n  ERRO FATAL: {fatal}", Color.RED, bold=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
