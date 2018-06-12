#!/usr/bin/env python3

import sqlite3
import os
from enum import Enum
import sys
import collections
import subprocess

PDF_VIEWER = 'zathura'

class Status(Enum):
    unread = 0
    read = 1

Entry = collections.namedtuple("Entry", "path title subject status")

class Database:
    def __init__(self, path):
        create = not os.path.exists(path)
        self.conn = sqlite3.connect(path)
        if create:
            self.conn.execute('''CREATE TABLE files
                              ( path text,
                                title text,
                                subject text,
                                status integer,
                                CONSTRAINT path_unique UNIQUE (path)
                              )''')

    def insert(self, path, title, subject, status):
        self.conn.execute("INSERT INTO files VALUES (?, ?, ?, ?)",
                          (path, title, subject, status.value))
        self.conn.commit()

    def list(self, subject=None):
        c = self.conn.cursor()
        if subject is None:
            c.execute('SELECT * FROM files')
        else:
            c.execute('SELECT * FROM files WHERE subject=?', (subject,))
        for i in c:
            yield Entry(*i)

    def close(self):
        self.conn.close()


db = Database('list.db')
items = None

while True:
    line = input('> ').split()

    if len(line) == 0:
        pass
    elif line[0] == 'add':
        if len(line) != 4:
            print("add <file> <title> <subject>")
        path, title, subject = line[1:]
        if not os.path.exists(path):
            print(f"No such file: {path}")
        db.insert(path, title, subject, Status.unread)
    elif line[0] == 'ls':
        subject = None
        if len(line) > 1:
            subject = line[1]
        items = list(db.list(subject))
        for x,i in enumerate(items):
            print(f"[{x}] {i.title}")
    elif line[0] in ('q', 'quit'):
        sys.exit()
    elif line[0].isnumeric():
        idx = int(line[0])
        if items is None:
            print("No search")
        elif idx < 0 or idx >= len(items):
            print(f"Index '{idx}' out of bounds")
        else:
            subprocess.call([PDF_VIEWER, items[idx].path])
    else:
        print(f"No such command: '{line[0]}'")

db.close()
