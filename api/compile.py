"""Vercel serverless function: POST /api/compile

Request body:  {"source": "<C code>", "optimize": true}
Response body: {"ok": bool, "stages": {"tokens", "ast", "tac", "llvm"}, "error": {...} | null}

A program that fails to compile is still a 200 response with "ok": false;
4xx codes are only for malformed requests.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'compiler'))

from pipeline import run_pipeline  # noqa: E402

MAX_SOURCE_BYTES = 50_000


class handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload, extra_headers=None):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def send_request_error(self, status, message):
        self.send_json(status, {'ok': False, 'stages': {}, 'error': {
            'phase': 'request', 'message': message, 'line': None, 'internal': False}})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            return self.send_request_error(400, 'Invalid Content-Length header.')
        if length > MAX_SOURCE_BYTES:
            return self.send_request_error(413, f'Programs are limited to {MAX_SOURCE_BYTES // 1000} KB.')

        try:
            data = json.loads(self.rfile.read(length) or b'{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.send_request_error(400, 'The request body must be JSON.')
        source = data.get('source') if isinstance(data, dict) else None
        if not isinstance(source, str):
            return self.send_request_error(400, 'The request needs a "source" string with the C program.')

        self.send_json(200, run_pipeline(source, optimize=data.get('optimize', True) is not False))

    def do_GET(self):
        self.send_request_error(405, 'Send the program with a POST request.')
