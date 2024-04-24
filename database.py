import sqlite3

conn = sqlite3.connect('database.db')

cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Sale (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        id_budynek INTEGER NOT NULL,
        pietro INTEGER NOT NULL,
        numer_sali TEXT NOT NULL,
        typ TEXT NOT NULL)
            ''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Konto (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        login text NOT NULL,
        haslo text NOT NULL,
        imie text,
        nazwisko text)
            ''')

cursor.execute('''
        CREATE TABLE IF NOT EXISTS Rezerwacje (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        id_sala INTEGER NOT NULL,
        id_konto INTEGER NOT NULL,
        od DATETIME NOT NULL,
        do DATETIME NOT NULL)
            ''')


cursor.execute('''
        CREATE TABLE IF NOT EXISTS Stanowiska (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        id_sala INTEGER NOT NULL,
        numer_stanowiska INTEGER NOT NULL)
            ''')


cursor.execute('''
        CREATE TABLE IF NOT EXISTS RezerwacjeStanowiska (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        id_konto INTEGER NOT NULL,
        id_stanowiska INTEGER NOT NULL,
        od DATETIME NOT NULL,
               do DATETIME NOT NULL)
            ''')

cursor.execute('''
        CREATE TABLE IF NOT EXISTS Budynki (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        nazwa text NOT NULL
        )
            ''')  



conn.commit()
conn.close()