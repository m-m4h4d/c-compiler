import re

class Token:
    def __init__(self, type, value, line, column):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, '{self.value}', line={self.line})"

class LexerError(Exception):
    pass

class Lexer:
    keywords = {
        'int': 'INT',
        'float': 'FLOAT',
        'double': 'DOUBLE',
        'void': 'VOID',
        'if': 'IF',
        'else': 'ELSE',
        'while': 'WHILE',
        'for': 'FOR',
        'return': 'RETURN',
        'break': 'BREAK',
        'continue': 'CONTINUE'
    }

    token_specification = [
        ('COMMENT',  r'//[^\n]*|/\*[\s\S]*?\*/'), # Line and block comments
        ('UNTERMINATED_COMMENT', r'/\*'),  # Block comment with no closing */
        ('INVALID_ID', r'\d+[A-Za-z_][A-Za-z0-9_]*'), # Identifiers starting with a number (invalid)
        ('NUMBER',   r'\d+(\.\d*)?'),      # Integer or decimal number
        ('ID',       r'[A-Za-z_][A-Za-z0-9_]*'), # Identifiers
        ('EQ',       r'=='),
        ('NEQ',      r'!='),
        ('LE',       r'<='),
        ('GE',       r'>='),
        ('AND',      r'&&'),
        ('OR',       r'\|\|'),
        ('INC',      r'\+\+'),
        ('DEC',      r'--'),
        ('ASSIGN',   r'='),
        ('LT',       r'<'),
        ('GT',       r'>'),
        ('NOT',      r'!'),
        ('PLUS',     r'\+'),
        ('MINUS',    r'-'),
        ('MUL',      r'\*'),
        ('DIV',      r'/'),
        ('MOD',      r'%'),
        ('LPAREN',   r'\('),
        ('RPAREN',   r'\)'),
        ('LBRACE',   r'\{'),
        ('RBRACE',   r'\}'),
        ('LBRACKET', r'\['),
        ('RBRACKET', r'\]'),
        ('SEMI',     r';'),
        ('COMMA',    r','),
        ('SKIP',     r'[ \t]+'),           # Skip over spaces and tabs
        ('NEWLINE',  r'\n'),               # Line endings
        ('MISMATCH', r'.'),                # Any other character
    ]

    def __init__(self, code):
        self.code = code
        self.tokens = []
        self.tokenize()

    def tokenize(self):
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in self.token_specification)
        line_num = 1
        line_start = 0
        
        for mo in re.finditer(tok_regex, self.code):
            kind = mo.lastgroup
            value = mo.group()
            column = mo.start() - line_start
            
            if kind == 'INVALID_ID':
                raise LexerError(f"Invalid identifier '{value}' on line {line_num}")
            elif kind == 'NUMBER':
                # Check if float or int
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
                self.tokens.append(Token(kind, value, line_num, column))
            elif kind == 'ID':
                kind = self.keywords.get(value, 'ID')
                self.tokens.append(Token(kind, value, line_num, column))
            elif kind == 'NEWLINE':
                line_start = mo.end()
                line_num += 1
            elif kind == 'SKIP':
                pass
            elif kind == 'COMMENT':
                # Block comments can span lines; keep line numbers accurate
                newlines = value.count('\n')
                if newlines:
                    line_num += newlines
                    line_start = mo.start() + value.rfind('\n') + 1
            elif kind == 'UNTERMINATED_COMMENT':
                raise LexerError(f"Unterminated comment starting on line {line_num}")
            elif kind == 'MISMATCH':
                raise LexerError(f'{value!r} unexpected on line {line_num}')
            else:
                self.tokens.append(Token(kind, value, line_num, column))
        self.tokens.append(Token('EOF', '', line_num, len(self.code) - line_start))
