# -*- coding: utf-8 -*-
"""verificar_excel.py — Comprobación rápida del Excel generado."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from openpyxl import load_workbook

wb = load_workbook("excel/gestion_clientes.xlsx")
print("Hojas:", wb.sheetnames)

cli = wb["Clientes"]
print("Clientes:", cli.max_row - 1, "filas x", cli.max_column, "cols")
print("  fila 2:", [cli.cell(2, c).value for c in (1, 3, 6, 8, 9)])

seg = wb["Seguimientos"]
print("Seguimientos:", seg.max_row - 1, "filas")
print("  fila 2:", [seg.cell(2, c).value for c in (1, 2, 4, 7, 9, 12)])

pre = wb["Presupuestos"]
print("Presupuestos:", pre.max_row - 1, "filas")
print("  fila 2:", [pre.cell(2, c).value for c in (1, 5, 9, 11)])

res = wb["Resumen"]
for r in range(1, res.max_row + 1):
    a = res.cell(r, 1).value
    b = res.cell(r, 2).value
    if a or b:
        print(f"  {a}  {b if b is not None else ''}")
