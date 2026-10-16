"""End-to-end tests for the compiler.

tests/programs/*.c are valid C. Each one is compiled twice: natively with clang
(the reference) and through our compiler to LLVM IR, which clang then turns into
an executable. The test passes when both executables exit with the same code.

tests/errors/*.c must be rejected by our compiler with an error. A file that
marks a line with a `// error` comment must also have the error reported on
that line.

The examples shown on the website (public/examples/*.c) are checked the same
way as tests/programs.

Usage: python tests/run_tests.py [name-filter]
"""
import contextlib
import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'compiler'))

from lexer import LexerError  # noqa: E402
from main import compile_c_code  # noqa: E402
from parser import ParseError  # noqa: E402
from semantic import SemanticError  # noqa: E402

TIMEOUT = 10


def compile_quietly(source):
    with contextlib.redirect_stdout(io.StringIO()):
        return compile_c_code(source)


def build_and_run(clang_args, workdir, name):
    exe = workdir / name
    build = subprocess.run(['clang', '-w', *clang_args, '-o', str(exe)],
                           capture_output=True, text=True)
    if build.returncode != 0:
        return None, build.stderr.strip()
    run = subprocess.run([str(exe)], capture_output=True, timeout=TIMEOUT)
    return run.returncode, None


def check_program(path, workdir):
    expected, err = build_and_run([str(path)], workdir, 'ref')
    if err:
        return f"reference build failed (is the test valid C?):\n{err}"

    try:
        _, llvm = compile_quietly(path.read_text())
    except Exception as e:
        return f"compiler error: {type(e).__name__}: {e}"

    ll_file = workdir / 'out.ll'
    ll_file.write_text(llvm)
    actual, err = build_and_run([str(ll_file)], workdir, 'ours')
    if err:
        return f"clang rejected generated IR:\n{err}"
    if actual != expected:
        return f"exit code {actual}, expected {expected}"
    return None


def check_error(path, workdir):
    source = path.read_text()
    marked = [n for n, line in enumerate(source.splitlines(), 1) if '// error' in line]
    try:
        compile_quietly(source)
    except (LexerError, ParseError, SemanticError) as e:
        if not marked:
            return None
        reported = re.search(r'line (\d+)', str(e))
        if reported is None:
            return f"error has no line number, expected line {marked[0]}: {e}"
        if int(reported.group(1)) != marked[0]:
            return f"error reported on line {reported.group(1)}, expected line {marked[0]}: {e}"
        return None
    except Exception as e:
        return f"crashed instead of reporting an error: {type(e).__name__}: {e}"
    return "compiled successfully, expected an error"


def main():
    if shutil.which('clang') is None:
        print("clang not found on PATH; it is needed to build and run the tests")
        return 2

    name_filter = sys.argv[1] if len(sys.argv) > 1 else ''
    cases = [(p, check_program) for p in sorted((ROOT / 'programs').glob('*.c'))]
    cases += [(p, check_program) for p in sorted((ROOT.parent / 'public' / 'examples').glob('*.c'))]
    cases += [(p, check_error) for p in sorted((ROOT / 'errors').glob('*.c'))]
    cases = [(p, check) for p, check in cases if name_filter in p.stem]

    failures = 0
    for path, check in cases:
        label = f"{path.parent.name}/{path.name}"
        with tempfile.TemporaryDirectory() as tmp:
            try:
                problem = check(path, Path(tmp))
            except subprocess.TimeoutExpired:
                problem = f"timed out after {TIMEOUT}s"
        if problem:
            failures += 1
            print(f"FAIL {label}\n     " + problem.replace('\n', '\n     '))
        else:
            print(f"ok   {label}")

    print(f"\n{len(cases) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
