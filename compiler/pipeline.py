"""Run every compiler phase and collect each one's output as plain data.

Used by the web API, which shows the phases side by side. Unlike
main.compile_c_code it never prints, and a compile error is returned as data
along with the output of the phases that finished before it.
"""
import re

from ast_nodes import ASTNode
from codegen import LLVMGenerator
from lexer import Lexer, LexerError
from optimizer import Optimizer
from parser import Parser, ParseError
from semantic import SemanticAnalyzer, SemanticError
from tac import TACGenerator

COMPILE_ERRORS = (LexerError, ParseError, SemanticError)


def ast_to_data(node):
    """Convert an AST into nested dicts and lists that serialize to JSON."""
    if isinstance(node, ASTNode):
        data = {'node': type(node).__name__}
        for field, value in vars(node).items():
            data[field] = ast_to_data(value)
        return data
    if isinstance(node, (list, tuple)):
        return [ast_to_data(item) for item in node]
    return node


def error_line(message):
    match = re.search(r'line (\d+)', message)
    return int(match.group(1)) if match else None


def run_pipeline(source, optimize=True):
    stages = {}
    phase = 'lexer'
    try:
        lexer = Lexer(source)
        stages['tokens'] = [
            {'type': t.type, 'value': t.value, 'line': t.line, 'column': t.column}
            for t in lexer.tokens
        ]

        phase = 'parser'
        ast = Parser(lexer).parse()
        # Serialize now: the optimizer rewrites the tree in place
        stages['ast'] = ast_to_data(ast)

        phase = 'semantic'
        semantic = SemanticAnalyzer(ast)
        semantic.analyze()

        if optimize:
            phase = 'optimizer'
            ast = Optimizer(ast).optimize()

        phase = 'tac'
        stages['tac'] = "\n".join(TACGenerator(ast).generate()).rstrip()

        phase = 'codegen'
        stages['llvm'] = LLVMGenerator(ast, semantic.symtab).generate()
    except COMPILE_ERRORS as e:
        message = str(e)
        return {'ok': False, 'stages': stages,
                'error': {'phase': phase, 'message': message, 'line': error_line(message), 'internal': False}}
    except RecursionError:
        return {'ok': False, 'stages': stages,
                'error': {'phase': phase, 'message': 'The program is nested too deeply to compile.',
                          'line': None, 'internal': False}}
    except Exception as e:
        # A crash inside the compiler itself, not a problem with the program
        return {'ok': False, 'stages': stages,
                'error': {'phase': phase, 'message': f"{type(e).__name__}: {e}", 'line': None, 'internal': True}}
    return {'ok': True, 'stages': stages, 'error': None}
