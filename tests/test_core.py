import os
import tempfile
import unittest
from pathlib import Path


class CoreTests(unittest.TestCase):
    def test_money_and_invoice_speech(self):
        from voice_agent import invoice_id_to_speech, money_to_speech

        self.assertEqual(
            invoice_id_to_speech("INV-2026-001"),
            "I N V two zero two six zero zero one",
        )
        self.assertEqual(
            money_to_speech(4500.50),
            "four thousand five hundred dollars and fifty cents",
        )

    def test_parse_invoice_text(self):
        from ocr_extractor import parse_invoice_text

        text = """
        Invoice # INV-2026-007
        Billed To: Acme Corporation
        Due Date: June 25, 2026
        Total Amount Due: $4,500.50
        """
        parsed = parse_invoice_text(text)
        self.assertEqual(parsed["invoice_id"], "INV-2026-007")
        self.assertEqual(parsed["customer_name"], "Acme Corporation")
        self.assertEqual(parsed["due_date"], "June 25, 2026")
        self.assertEqual(parsed["amount_due"], 4500.50)

    def test_database_promise_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["AR_DB_PATH"] = str(Path(tmpdir) / "test_ar.db")

            import importlib
            import database

            importlib.reload(database)
            database.init_db(seed=True)
            self.assertTrue(
                database.update_invoice_status(
                    "INV-2026-001", "PROMISED", promise_date="June 30, 2026"
                )
            )
            invoice = database.get_invoice_details("INV-2026-001")
            self.assertEqual(invoice["status"], "PROMISED")
            self.assertEqual(invoice["promise_date"], "June 30, 2026")


if __name__ == "__main__":
    unittest.main()
