"""Tests for the website: the static pages and the /api/compile function.

Runs dev_server.py's handler (which wraps the same api/compile.py that Vercel
deploys) on a free local port. Needs no clang.

Usage: python tests/test_web.py
"""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dev_server  # noqa: E402


def request(base, path, body=None, method=None):
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def compile_source(base, source, **options):
    status, body = request(base, '/api/compile', {'source': source, **options})
    return status, json.loads(body)


def run_checks(base):
    checks = []

    def check(name, condition):
        checks.append((name, bool(condition)))

    for path in ('/', '/compiler', '/styles.css', '/compiler.js'):
        status, _ = request(base, path)
        check(f"GET {path} serves the page", status == 200)

    examples = sorted((ROOT / 'public' / 'examples').glob('*.c'))
    html = (ROOT / 'public' / 'compiler.html').read_text()
    for example in examples:
        check(f"compiler page offers {example.name}", f'value="{example.name}"' in html)
        status, result = compile_source(base, example.read_text())
        check(f"example {example.name} compiles", status == 200 and result['ok'])

    status, result = compile_source(base, 'int main() {\n    int b = 5 + 3;\n    return b;\n}\n')
    stages = result['stages']
    check("a valid program returns every stage", status == 200 and result['ok']
          and set(stages) == {'tokens', 'ast', 'tac', 'llvm'})
    check("tokens carry positions", stages['tokens'][0] == {'type': 'INT', 'value': 'int', 'line': 1, 'column': 0})
    check("the AST is the parsed tree, before folding",
          stages['ast']['declarations'][0]['body']['statements'][0]['init_expr']['node'] == 'BinOp')
    check("TAC is folded by default", 'b = 8' in stages['tac'])
    check("LLVM IR is returned", 'define i32 @main()' in stages['llvm'])

    _, result = compile_source(base, 'int main() {\n    int b = 5 + 3;\n    return b;\n}\n', optimize=False)
    check("optimize=false skips folding", '5 + 3' in result['stages']['tac'])

    _, result = compile_source(base, 'int main() {\n    int x = 3\n    return x;\n}\n')
    check("a parse error reports phase and line", not result['ok']
          and result['error']['phase'] == 'parser' and result['error']['line'] == 3)
    check("a parse error keeps the tokens", 'tokens' in result['stages'] and 'ast' not in result['stages'])

    _, result = compile_source(base, 'int main() { return y; }')
    check("a semantic error keeps the AST", result['error']['phase'] == 'semantic'
          and 'ast' in result['stages'] and 'tac' not in result['stages'])

    _, result = compile_source(base, 'int main() { return ' + '(' * 5000 + '1' + ')' * 5000 + '; }')
    check("deep nesting is an error, not a crash", not result['ok'] and not result['error']['internal'])

    status, _ = request(base, '/api/compile', b'not json')
    check("malformed JSON is a 400", status == 400)
    status, _ = request(base, '/api/compile', {'code': 'int main() {}'})
    check("a missing source field is a 400", status == 400)
    status, _ = request(base, '/api/compile', {'source': 'x' * 60_000})
    check("oversized programs are a 413", status == 413)
    status, _ = request(base, '/api/compile')
    check("GET on the API is a 405", status == 405)

    return checks


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), dev_server.DevHandler)
    server.RequestHandlerClass.log_message = lambda *args: None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        checks = run_checks(f"http://127.0.0.1:{server.server_address[1]}")
    finally:
        server.shutdown()

    for name, passed in checks:
        print(f"{'ok  ' if passed else 'FAIL'} {name}")
    failures = sum(not passed for _, passed in checks)
    print(f"\n{len(checks) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
