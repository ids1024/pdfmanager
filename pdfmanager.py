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

Entry = collections.namedtuple("Entry", "id path title subject status")
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
        self.conn.execute('''INSERT INTO files
                             (path, title, subject, status)
                             VALUES (?, ?, ?, ?)''',
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
    completions = []

    def __init__(self):
        readline.set_completer(self.complete)
        readline.parse_and_bind("tab: complete")
        self.db = Database('list.db')
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def get_completions(self, tokens):
        if len(tokens) == 1:
            return [i for i in self.commands if i.startswith(tokens[0])]
            pass
        else:
            cmd = tokens[0]
            idx = len(tokens) - 1
            cur = tokens[-1]

            if cmd == 'add' and idx == 1:
                return [i for i in os.listdir() if i.startswith(cur)]
            elif cmd == 'ls' and idx == 1:
                return [i for i in self.db.subjects() if i.startswith(cur)]

        return []

    def complete(self, text, state):
        buf = readline.get_line_buffer()

        if state == 0:
            try:
                tokens = shlex.split(buf)
            except ValueError as e:
                if e.args != ('No closing quotation',):
                    raise e
                try:
                    tokens = shlex.split(buf + '"')
                except ValueError as e:
                    if e.args != ('No closing quotation',):
                        raise e
                    tokens = shlex.split(buf + "'")

            if buf.endswith(' ') or len(tokens) == 0:
                tokens.append('')

            self.completions = [shlex.quote(i) for i in self.get_completions(tokens)]

        try:
            return self.completions[state]
        except IndexError:
            return None

    @command('add')
    def add(self, path, title, subject):
        if not os.path.exists(path):
            print(f"No such file: {path}")
        self.db.insert(path, title, subject, Status.unread)

    @command(['s', 'subjects'])
    def list_subjects(self):
        self.result = Result('subjects', list(self.db.subjects()))
        for x, i in enumerate(self.result.items):
            print(f"[{x}] {i}")

    @command('ls')
    def list_pdfs(self, subject=None):
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

    def get_usage(self, cmd):
        func = self.commands[cmd]
        usage = cmd
        nargs = func.__code__.co_argcount
        ndefs = len(func.__defaults__) if func.__defaults__ else 0
        for x, i in enumerate(func.__code__.co_varnames[1:nargs]):
            if x >= nargs - ndefs - 1:
                usage += f" [<{i}>]"
            else:
                usage += f" <{i}>"
        return usage

    def loop(self):
        while True:
            try:
                line = shlex.split(input('> '))
            except ValueError as e:
                print(e)
                continue
            except EOFError:
                print()
                break

            if len(line) == 0:
                continue

            cmd = line[0]
            if cmd in self.commands:
                func = self.commands[cmd]
                try:
                    func(self, *line[1:])
                except TypeError as e:
                    if len(e.args) != 1 or \
                       not e.args[0].startswith(f"{cmd}()") or \
                       "positional argument" not in e.args[0]:
                        raise e
                    print(f"Usage: {self.get_usage(cmd)}")

            elif cmd.isnumeric():
                self.select(int(cmd))
            elif cmd in ('q', 'quit'):
                break
            else:
                print(f"No such command: '{line[0]}'")

with PDFManager() as pdfmanager:
    pdfmanager.loop()
