"""Regression checks for transaction handling and Windows file locks."""
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import database


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory(prefix='servix-db-')
        self.path = Path(self.folder.name) / 'test.db'
        self.db_patch = patch.object(database, 'DB', self.path)
        self.db_patch.start()
        self.addCleanup(self.folder.cleanup)
        self.addCleanup(self.db_patch.stop)
        with database.connect() as con:
            con.execute('CREATE TABLE records (name TEXT NOT NULL)')

    def test_success_commits_and_closes_connection(self):
        with database.connect() as con:
            con.execute('INSERT INTO records VALUES (?)', ('saved',))
        with self.assertRaises(sqlite3.ProgrammingError):
            con.execute('SELECT 1')
        with database.connect() as check:
            self.assertEqual(check.execute('SELECT name FROM records').fetchone()['name'], 'saved')
        # This fails on Windows if any connection still holds the database open.
        self.path.rename(self.path.with_suffix('.moved'))

    def test_failure_rolls_back_and_closes_connection(self):
        with self.assertRaisesRegex(ValueError, 'cancel operation'):
            with database.connect() as con:
                con.execute('INSERT INTO records VALUES (?)', ('discarded',))
                raise ValueError('cancel operation')
        with self.assertRaises(sqlite3.ProgrammingError):
            con.execute('SELECT 1')
        with database.connect() as check:
            self.assertEqual(check.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)
        self.path.unlink()


if __name__ == '__main__':
    unittest.main()
