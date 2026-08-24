#!/usr/bin/env python3
"""Servidor estatico apenas para desenvolvimento local.

O site e 100% estatico -- em producao basta servir a pasta site/ (GitHub Pages, por
exemplo). Este arquivo existe so para abrir a pagina durante o desenvolvimento, porque
abrir index.html por file:// bloqueia o fetch dos JSON por CORS.

    uv run site/servidor.py [porta]
"""
import http.server
import os
import socketserver
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8787


class Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path))


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", porta), Silencioso) as httpd:
    print(f"servindo site/ em http://127.0.0.1:{porta}", flush=True)
    httpd.serve_forever()
