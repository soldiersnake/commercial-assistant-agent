# -*- coding: utf-8 -*-
"""limpiar_citas_prueba.py — Archiva las citas de PRUEBA (canceladas,
sin cliente, título con 'test'/'prueba') y las quita del historial
del panel. Se usa una vez; el archivo queda en datos/archivo/citas/.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import memoria  # noqa: E402


def es_prueba(cita: dict) -> bool:
    titulo = (cita.get("titulo") or "").lower()
    return (cita.get("estado") == "cancelada"
            and not cita.get("cliente_id")
            and ("test" in titulo or "prueba" in titulo))


def main() -> int:
    citas = memoria.cargar("citas.json", {"citas": []})
    pruebas = [c for c in citas["citas"] if es_prueba(c)]
    if not pruebas:
        print("[i] No hay citas de prueba que limpiar")
        return 0
    (RAIZ / "datos" / "archivo" / "citas").mkdir(parents=True, exist_ok=True)
    for c in pruebas:
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        memoria.guardar(f"archivo/citas/{c['id']}_{marca}.json", c)
        print(f"[OK] archivada: {c['id']} «{c['titulo']}»")
    citas["citas"] = [c for c in citas["citas"] if not es_prueba(c)]
    memoria.guardar("citas.json", citas)
    print(f"[OK] Historial limpio — quedan {len(citas['citas'])} citas en memoria")
    return 0


if __name__ == "__main__":
    sys.exit(main())
