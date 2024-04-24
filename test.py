import unittest
from flask import g, session
from app import app
import sqlite3

class UsunRekordTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.db = sqlite3.connect('database.db')

    def tearDown(self):
        self.db.close()

    def login(self, user_id):
        with self.app.session_transaction() as sess:
            sess['user_id'] = user_id

    def test_delete_record_not_logged(self):
        response = self.app.post('/usun_rekord/1')
        self.assertEqual(response.status_code, 302)

    def test_delete_record_non_existent(self):
        self.login(1)
        response = self.app.post('/usun_rekord/1')
        self.assertEqual(response.status_code, 302)

    def test_delete_record_existing(self):
        self.login(1)
        cursor = self.db.cursor()
        cursor.execute('''INSERT INTO Rezerwacje 
                       (id, id_sala, id_konto, od, do, typ) VALUES (?, ?, ?, ?, ?, ?)''',
                       (1, 1, 1, '2025-11-09 15:00:00', '2025-11-09 16:00:00', 'Badawczy'))
        self.db.commit()
        response = self.app.post('/usun_rekord/1')
        self.assertEqual(response.status_code, 302)
        cursor.execute('SELECT * FROM Rezerwacje WHERE id = ?', (1,))
        self.assertIsNone(cursor.fetchone())

if __name__ == '__main__':
    unittest.main()