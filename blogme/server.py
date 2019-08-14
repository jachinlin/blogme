# -*- coding: utf-8 -*-

import os
from http.server import HTTPServer
from http.server import SimpleHTTPRequestHandler
from urllib.parse import unquote

from blogme.builder import Builder


class SimpleRequestHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.server.builder.anything_needs_build():
            print('Detected change, building')
            self.server.builder.run()
        SimpleHTTPRequestHandler.do_GET(self)

    def translate_path(self, path: str) -> str:
        print('get', path)
        path = path.split('?', 1)[0].split('#', 1)[0]
        if path.startswith(self.server.builder.prefix_path):
            path = path[len(self.server.builder.prefix_path):]
        path = os.path.normpath(unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = self.server.builder.dest_folder
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path

    def log_request(self, code='-', size='-'):
        pass

    def log_error(self, *args):
        pass

    def log_message(self, format, *args):
        pass


class Server(HTTPServer):

    def __init__(self, host: str, port: int, builder: Builder):
        super().__init__((host, int(port)), SimpleRequestHandler)
        self.builder = builder
