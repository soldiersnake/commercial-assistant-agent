# -*- coding: utf-8 -*-
"""tests/test_importador.py — Pruebas de los extractores de contactos."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from importar_clientes import (  # noqa: E402
    extraer_emails, extraer_telefonos, a_texto, limpiar,
)


class Emails(unittest.TestCase):
    def test_simple(self):
        emails, notas = extraer_emails("admisanchez@hotmail.com")
        self.assertEqual(emails, ["admisanchez@hotmail.com"])

    def test_dobles_con_punto_y_coma(self):
        emails, _ = extraer_emails("cpjc99@gmail.com;jcgestionempresas@gmail.com")
        self.assertEqual(emails, ["cpjc99@gmail.com",
                                  "jcgestionempresas@gmail.com"])

    def test_con_notas(self):
        emails, notas = extraer_emails("CONECTA;proveedores@aliciacastillo.es")
        self.assertEqual(emails, ["proveedores@aliciacastillo.es"])
        self.assertTrue(any("conecta" in n.lower() for n in notas))

    def test_sin_email(self):
        emails, notas = extraer_emails('facturas por correo ordinario "no mail"')
        self.assertEqual(emails, [])
        self.assertTrue(any("ordinario" in n.lower() for n in notas))

    def test_correo_postal(self):
        emails, notas = extraer_emails("CORREO POSTAL")
        self.assertEqual(emails, [])
        self.assertTrue(any("postal" in n.lower() for n in notas))

    def test_normalizacion_minusculas(self):
        emails, _ = extraer_emails("Administracion@CFV132.COM")
        self.assertEqual(emails, ["administracion@cfv132.com"])


class Telefonos(unittest.TestCase):
    def test_dos_con_guion(self):
        tels, _ = extraer_telefonos("963849180 -  608980283")
        self.assertEqual(tels, ["963849180", "608980283"])

    def test_espacios_interiores(self):
        tels, _ = extraer_telefonos("96 153 72 13    640179062 CON WASAP")
        self.assertEqual(tels, ["961537213", "640179062"])

    def test_puntos(self):
        tels, _ = extraer_telefonos("96.152.35.75 // 692.05.72.89")
        self.assertEqual(tels, ["961523575", "692057289"])

    def test_barra(self):
        tels, _ = extraer_telefonos("655 904 405 / 96 383 03 22")
        self.assertEqual(tels, ["655904405", "963830322"])

    def test_nombre_en_medio(self):
        tels, _ = extraer_telefonos("963836177 /AMPARO 601013838")
        self.assertEqual(tels, ["963836177", "601013838"])

    def test_cobol_cinco_digitos_no_es_telefono(self):
        tels, _ = extraer_telefonos("CP 46018")
        self.assertEqual(tels, [])


class Utilidades(unittest.TestCase):
    def test_a_texto_float(self):
        self.assertEqual(a_texto(46920.0), "46920")
        self.assertEqual(a_texto("x"), "x")

    def test_limpiar_espacios(self):
        self.assertEqual(limpiar("  a   b  c "), "a b c")


if __name__ == "__main__":
    unittest.main()
