"""Regression checks for the isolated sample workspace."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import database
from database import authenticate, repeat_complaints
from demo_data import DEMO_PASSWORD, seed_demo_data


class DemoWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='servix-demo-test-')
        self.addCleanup(self.temp.cleanup)
        self.db_patch = patch.object(database, 'DB', Path(self.temp.name) / 'demo.db')
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        database.init_db()

    def test_demo_seed_is_isolated_repeatable_and_exercises_duplicates(self):
        seed_demo_data()
        with database.connect() as con:
            con.execute("UPDATE settings SET value='1' WHERE key='demo_seeded'")
        seed_demo_data()  # Upgrade a previously seeded Demo Workspace without duplicating records.
        seed_demo_data()
        with database.connect() as con:
            client_count = con.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
            equipment_count = con.execute('SELECT COUNT(*) FROM equipment').fetchone()[0]
            service_count = con.execute('SELECT COUNT(*) FROM services').fetchone()[0]
            history_count = con.execute('SELECT COUNT(*) FROM history').fetchone()[0]
            update_count = con.execute('SELECT COUNT(*) FROM service_updates').fetchone()[0]
            duplicate = con.execute("""SELECT code FROM clients WHERE
                REPLACE(REPLACE(mobile,' ',''),'-','')=REPLACE(REPLACE(?,' ',''),'-','')
                OR LOWER(email)=LOWER(?)""", ('9000010001', 'bluewave.demo@servix.local')).fetchone()
            equipment = con.execute("SELECT id FROM equipment WHERE serial='DEMO-SN-001'").fetchone()
            service = con.execute("SELECT code,notes FROM services WHERE code='SRV-DEMO-0001'").fetchone()
        self.assertEqual((client_count, equipment_count, service_count), (6, 8, 26))
        self.assertEqual(history_count, 52)
        self.assertEqual(update_count, 2)
        with database.connect() as con:
            self.assertEqual(con.execute("SELECT value FROM settings WHERE key='demo_seeded'").fetchone()[0], '2')
        self.assertEqual(duplicate['code'], 'CLI-DEMO-001')
        self.assertEqual(service['code'], 'SRV-DEMO-0001')
        self.assertIn('DEMO NOTE', service['notes'])
        self.assertEqual(repeat_complaints(equipment['id'], 'intermittent feedback')[0]['code'], 'SRV-DEMO-0001')
        self.assertIsNotNone(authenticate('admin', DEMO_PASSWORD))


if __name__ == '__main__':
    unittest.main()
