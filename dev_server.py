"""Serve the website locally the way Vercel does: static files from public/
and the compile function at /api/compile.

Usage: python dev_server.py [port]   (default 8000)
"""
import importlib.util
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, 'public')

spec = importlib.util.spec_from_file_location('compile_api', os.path.join(ROOT, 'api', 'compile.py'))
compile_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compile_api)


class DevHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC, **kwargs)

    def is_api(self):
        return self.path.split('?')[0] == '/api/compile'

    def do_POST(self):
        if self.is_api():
            return compile_api.handler.do_POST(self)
        self.send_error(405)

    def do_GET(self):
        if self.is_api():
            return compile_api.handler.do_GET(self)
        # Mirror vercel.json's cleanUrls: /compiler serves compiler.html
        path = self.path.split('?')[0]
        if path != '/' and '.' not in os.path.basename(path):
            if os.path.isfile(os.path.join(PUBLIC, path.lstrip('/') + '.html')):
                self.path = path + '.html'
        return super().do_GET()

    # The API handler's helpers, so its methods work on this class too
    send_json = compile_api.handler.send_json
    send_request_error = compile_api.handler.send_request_error


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(('127.0.0.1', port), DevHandler)
    print(f"Serving on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
