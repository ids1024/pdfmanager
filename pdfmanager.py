#!/usr/bin/env python3

import sqlite3
import os
from enum import Enum
import collections
import subprocess
import readline
import shlex

PDF_VIEWER = 'zathura'

class Status(Enum):
    unread = 0
    read = 1

Entry = collections.namedtuple("Entry", "path title subject status")
Result = collections.namedtuple("Result", "type items")

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

    def subjects(self):
        c = self.conn.cursor()
        c.execute('SELECT DISTINCT subject FROM files')
        for i in c:
            yield i[0]

    def close(self):
        self.conn.close()


def command_decorator(commands):
    def command(name):
        def wrapper(func):
            if isinstance(name, str):
                commands[name] = func
            else:
                for i in name:
                    commands[i] = func
            return func
        return wrapper
    return command


class PDFManager:
    commands = {}
    command = command_decorator(commands)

    def __init__(self):
        readline.parse_and_bind('')
        self.db = Database('list.db')
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    @command('add')
    def add(self, *args):
        if len(args) != 3:
            print("add <file> <title> <subject>")
        path, title, subject = args

        if not os.path.exists(path):
            print(f"No such file: {path}")
        db.insert(path, title, subject, Status.unread)

    @command(['s', 'subjects'])
    def list_subjects(self):
        self.result = Result('subjects', list(self.db.subjects()))
        for x, i in enumerate(self.result.items):
            print(f"[{x}] {i}")

    @command('ls')
    def list_pdfs(self, *args):
        subject = None
        if len(args) > 0:
            subject = args[0]

        self.result = Result('pdfs', list(self.db.list(subject)))
        for x, i in enumerate(self.result.items):
            print(f"[{x}] {i.title}")

    def select(self, idx):
        if self.result is None:
            print("No search")
        elif idx < 0 or idx >= len(self.result.items):
            print(f"Index '{idx}' out of bounds")
        else:
            item = self.result.items[idx]
            if self.result.type == 'pdfs':
                subprocess.call([PDF_VIEWER, item.path])
            elif self.result.type == 'subjects':
                self.list_pdfs(item)

    def loop(self):
        while True:
            line = shlex.split(input('> '))

            if len(line) == 0:
                pass
            elif line[0] in self.commands:
                self.commands[line[0]](self, *line[1:])
            elif line[0].isnumeric():
                self.select(int(line[0]))
            elif line[0] in ('q', 'quit'):
                break
            else:
                print(f"No such command: '{line[0]}'")

with PDFManager() as pdfmanager:
    pdfmanager.loop()
