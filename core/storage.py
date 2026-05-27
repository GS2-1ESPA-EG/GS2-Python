"""
core/storage.py
---------------
Camada de persistência em JSON.

Por que JSON e não SQLite/CSV?
- A disciplina de Computational Thinking exige manipulação de arquivos
  como conceito fundamental, e JSON é o formato que melhor preserva
  estruturas aninhadas (listas dentro de dicionários);
- É legível por humanos (auditoria de missão);
- Cada arquivo é independente: corrupção de um não afeta os outros;
- É compatível com payloads MQTT/NGSI-LD usados pelo Gateway de bordo
  quando o sistema é exportado para sincronização com a terra.

Nota arquitetural: este CLI mantém seu próprio diretório `data/` local.
A sincronização com o sistema principal (App React) e com a terra (FIWARE)
acontece via exportação explícita pelo menu (ver core/sync.py).
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


# ============================================================
# Localização dos arquivos
# ============================================================

# Diretório data/ relativo à raiz do projeto CLI
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BACKUP_DIR = DATA_DIR / "_backups"


# ============================================================
# Exceções customizadas
# ============================================================

class StorageError(Exception):
    """Erro base de persistência."""
    pass


class DataFileCorruptedError(StorageError):
    """Levantado quando o JSON não pode ser decodificado."""
    pass


class DataFileNotFoundError(StorageError):
    """Levantado quando o arquivo esperado não existe."""
    pass


# ============================================================
# Operações de leitura
# ============================================================

def load_json(filename: str, default=None):
    """
    Carrega um arquivo JSON do diretório data/.

    Se o arquivo não existir, retorna o valor `default` (em vez de
    levantar exceção) — isso permite que o CLI rode na primeira execução
    sem precisar de pré-setup manual.

    Se o arquivo existir mas estiver corrompido, levanta
    DataFileCorruptedError para que o chamador decida o que fazer
    (geralmente: tentar restaurar de backup).
    """
    filepath = DATA_DIR / filename

    if not filepath.exists():
        return default if default is not None else []

    try:
        with open(filepath, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except json.JSONDecodeError as e:
        raise DataFileCorruptedError(
            f"Arquivo {filename} está corrompido (linha {e.lineno}, "
            f"coluna {e.colno}): {e.msg}"
        )
    except OSError as e:
        raise StorageError(f"Não foi possível ler {filename}: {e}")


# ============================================================
# Operações de escrita
# ============================================================

def save_json(filename: str, data) -> None:
    """
    Salva um objeto Python como JSON no diretório data/.

    Antes de sobrescrever, faz um backup automático em data/_backups/
    (somente se o arquivo já existir). Isso garante que mesmo em caso
    de queda de energia durante o save, há sempre uma cópia anterior
    recuperável.

    Usa escrita atômica: escreve em arquivo temporário e renomeia.
    Garante que o arquivo original nunca fica em estado parcial.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    filepath = DATA_DIR / filename

    # Backup do arquivo anterior, se existir
    if filepath.exists():
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{filepath.stem}_{timestamp}.json"
        try:
            shutil.copy2(filepath, BACKUP_DIR / backup_name)
        except OSError:
            # Se não conseguir fazer backup, segue mesmo assim
            # (perder backup é menos grave do que perder o save)
            pass

    try:
        # Escrita atômica
        temp_path = filepath.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2, ensure_ascii=False)
        os.replace(temp_path, filepath)
    except OSError as e:
        raise StorageError(f"Não foi possível salvar {filename}: {e}")


# ============================================================
# Utilitário: verificar integridade
# ============================================================

def health_check() -> dict:
    """
    Verifica se todos os arquivos de dados estão acessíveis e válidos.
    Retorna um dicionário com o status de cada arquivo.
    """
    expected_files = [
        "spacecraft.json",
        "compartments.json",
        "items.json",
        "consumption.json",
        "alerts.json",
    ]

    report = {"_data_dir": str(DATA_DIR)}
    for fname in expected_files:
        filepath = DATA_DIR / fname
        if not filepath.exists():
            report[fname] = "ausente (será criado na primeira escrita)"
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as fp:
                json.load(fp)
            size_kb = filepath.stat().st_size / 1024
            report[fname] = f"OK ({size_kb:.1f} KB)"
        except json.JSONDecodeError:
            report[fname] = "CORROMPIDO"
        except OSError as e:
            report[fname] = f"erro de leitura: {e}"

    return report
