from lexer import Lexer
from ast_nodes import *

class ParseError(Exception):
    pass

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = None
        self.pos = -1
        self.advance()

    def advance(self):
        self.pos += 1
        if self.pos < len(self.lexer.tokens):
            self.current_token = self.lexer.tokens[self.pos]
        return self.current_token

    def match(self, token_type):
        if self.current_token.type == token_type:
            tok = self.current_token
            self.advance()
            return tok
        else:
            raise ParseError(f"Expected {token_type}, found {self.current_token.type} at line {self.current_token.line}")

    def at(self, node, line):
        node.line = line
        return node

    def parse(self):
        declarations = []
        while self.current_token.type != 'EOF':
            declarations.append(self.parse_declaration())
        return Program(declarations)

    def parse_type(self, allow_void=False):
        """A base type followed by any number of '*': 'int', 'double*', 'int**'."""
        tok = self.current_token
        allowed = ('INT', 'FLOAT', 'DOUBLE', 'VOID') if allow_void else ('INT', 'FLOAT', 'DOUBLE')
        if tok.type not in allowed:
            raise ParseError(f"Expected a type at line {tok.line}")
        self.advance()
        stars = 0
        while self.current_token.type == 'MUL':
            self.advance()
            stars += 1
        if tok.type == 'VOID' and stars:
            raise ParseError(f"void pointers are not supported at line {tok.line}")
        return tok.value + '*' * stars

    def parse_declaration(self):
        # type ID ...
        if self.current_token.type in ('INT', 'FLOAT', 'DOUBLE', 'VOID'):
            line = self.current_token.line
            var_type = self.parse_type(allow_void=True)
            name_tok = self.match('ID')
            name = name_tok.value
            
            # could be function, array or var
            if self.current_token.type == 'LPAREN':
                return self.parse_function_decl(var_type, name, name_tok.line)
            elif var_type == 'void':
                raise ParseError(f"Variable '{name}' declared void at line {line}")
            elif self.current_token.type == 'LBRACKET':
                return self.parse_array_decl(var_type, name, name_tok.line)
            else:
                return self.parse_var_decl(var_type, name, name_tok.line)
        else:
            raise ParseError(f"Expected type specifier at line {self.current_token.line}")

    def parse_function_decl(self, return_type, name, line):
        self.match('LPAREN')
        params = []
        param_lines = []
        if self.current_token.type == 'VOID' and self.lexer.tokens[self.pos + 1].type == 'RPAREN':
            self.match('VOID') # f(void) means no parameters
        elif self.current_token.type != 'RPAREN':
            while True:
                param_lines.append(self.current_token.line)
                params.append(self.parse_param())
                if self.current_token.type != 'COMMA':
                    break
                self.match('COMMA')
        self.match('RPAREN')
        body = self.parse_block()
        func = self.at(FunctionDecl(return_type, name, params, body), line)
        func.param_lines = param_lines # params are (type, name) tuples, so their lines live here
        return func

    def parse_param(self):
        if self.current_token.type not in ('INT', 'FLOAT', 'DOUBLE'):
            raise ParseError(f"Expected type in parameter list at line {self.current_token.line}")
        p_type = self.parse_type()
        name = self.match('ID').value
        if self.current_token.type == 'LBRACKET':
            # As in C, an array parameter `int a[]` or `int a[10]` is a pointer
            self.match('LBRACKET')
            if self.current_token.type == 'NUMBER':
                self.advance()
            self.match('RBRACKET')
            p_type += '*'
        return (p_type, name)

    def parse_array_decl(self, var_type, name, line):
        self.match('LBRACKET')
        size = self.match('NUMBER').value
        self.match('RBRACKET')
        self.match('SEMI')
        return self.at(ArrayDecl(var_type, name, size), line)

    def parse_var_decl(self, var_type, name, line):
        init_expr = None
        if self.current_token.type == 'ASSIGN':
            self.match('ASSIGN')
            init_expr = self.parse_expression()
        self.match('SEMI')
        return self.at(VarDecl(var_type, name, init_expr), line)

    def parse_block(self):
        line = self.match('LBRACE').line
        statements = []
        while self.current_token.type != 'RBRACE' and self.current_token.type != 'EOF':
            statements.append(self.parse_block_item())
        self.match('RBRACE')
        return self.at(Block(statements), line)

    def parse_block_item(self):
        # A declaration or a statement, as allowed directly inside braces
        if self.current_token.type == 'VOID':
            line = self.current_token.line
            self.parse_type(allow_void=True) # rejects void pointers with a clear message
            name = self.match('ID').value
            raise ParseError(f"Variable '{name}' declared void at line {line}")
        if self.current_token.type in ('INT', 'FLOAT', 'DOUBLE'):
            var_type = self.parse_type()
            name_tok = self.match('ID')
            if self.current_token.type == 'LBRACKET':
                return self.parse_array_decl(var_type, name_tok.value, name_tok.line)
            return self.parse_var_decl(var_type, name_tok.value, name_tok.line)
        return self.parse_statement()

    def parse_statement(self):
        if self.current_token.type == 'IF':
            return self.parse_if()
        elif self.current_token.type == 'WHILE':
            return self.parse_while()
        elif self.current_token.type == 'DO':
            return self.parse_do_while()
        elif self.current_token.type == 'SWITCH':
            return self.parse_switch()
        elif self.current_token.type in ('CASE', 'DEFAULT'):
            tok = self.current_token
            raise ParseError(f"'{tok.value}' label is not directly inside a switch at line {tok.line}")
        elif self.current_token.type == 'FOR':
            return self.parse_for()
        elif self.current_token.type == 'RETURN':
            return self.parse_return()
        elif self.current_token.type in ('BREAK', 'CONTINUE'):
            tok = self.current_token
            self.advance()
            self.match('SEMI')
            node = BreakStmt() if tok.type == 'BREAK' else ContinueStmt()
            return self.at(node, tok.line)
        elif self.current_token.type == 'LBRACE':
            return self.parse_block()
        else:
            return self.parse_expr_statement()

    def parse_if(self):
        line = self.match('IF').line
        self.match('LPAREN')
        cond = self.parse_expression()
        self.match('RPAREN')
        then_b = self.parse_statement()
        else_b = None
        if self.current_token.type == 'ELSE':
            self.match('ELSE')
            else_b = self.parse_statement()
        return self.at(IfStmt(cond, then_b, else_b), line)

    def parse_while(self):
        line = self.match('WHILE').line
        self.match('LPAREN')
        cond = self.parse_expression()
        self.match('RPAREN')
        body = self.parse_statement()
        return self.at(WhileStmt(cond, body), line)

    def parse_do_while(self):
        line = self.match('DO').line
        body = self.parse_statement()
        self.match('WHILE')
        self.match('LPAREN')
        cond = self.parse_expression()
        self.match('RPAREN')
        self.match('SEMI')
        return self.at(DoWhileStmt(body, cond), line)

    def parse_switch(self):
        line = self.match('SWITCH').line
        self.match('LPAREN')
        expr = self.parse_expression()
        self.match('RPAREN')
        self.match('LBRACE')
        cases = []
        while self.current_token.type not in ('RBRACE', 'EOF'):
            tok = self.current_token
            if tok.type == 'CASE':
                self.advance()
                value = self.parse_expression()
                self.match('COLON')
                cases.append(self.at(SwitchCase(value, []), tok.line))
            elif tok.type == 'DEFAULT':
                self.advance()
                self.match('COLON')
                cases.append(self.at(SwitchCase(None, []), tok.line))
            elif not cases:
                raise ParseError(f"Expected 'case' or 'default' at the start of the switch at line {tok.line}")
            else:
                cases[-1].statements.append(self.parse_block_item())
        self.match('RBRACE')
        return self.at(SwitchStmt(expr, cases), line)

    def parse_for(self):
        line = self.match('FOR').line
        self.match('LPAREN')
        # Each of the three clauses may be empty
        if self.current_token.type in ('INT', 'FLOAT', 'DOUBLE'):
            var_type = self.parse_type()
            name_tok = self.match('ID')
            init = self.parse_var_decl(var_type, name_tok.value, name_tok.line) # Includes SEMI
        elif self.current_token.type == 'SEMI':
            self.match('SEMI')
            init = None
        else:
            init = self.parse_expr_statement() # Includes SEMI
        cond = None
        if self.current_token.type != 'SEMI':
            cond = self.parse_expression()
        self.match('SEMI')
        inc = None
        if self.current_token.type != 'RPAREN':
            inc = self.parse_assignment_expr()
        self.match('RPAREN')
        body = self.parse_statement()
        return self.at(ForStmt(init, cond, inc, body), line)

    def parse_return(self):
        line = self.match('RETURN').line
        expr = None
        if self.current_token.type != 'SEMI':
            expr = self.parse_expression()
        self.match('SEMI')
        return self.at(ReturnStmt(expr), line)

    def parse_expr_statement(self):
        expr = self.parse_assignment_expr()
        self.match('SEMI')
        return expr

    def parse_assignment_expr(self):
        target = self.parse_expression()
        if self.current_token.type not in ('ASSIGN', 'COMPOUND_ASSIGN'):
            return target
        op_tok = self.current_token
        op = self.match_assignment()
        expr = self.parse_assignment_expr() # right-associative: a = b = c
        if isinstance(target, Var):
            node = AssignStmt(target.name, expr, op)
        elif isinstance(target, ArrayAccess):
            node = ArrayAssignStmt(target.name, target.index_expr, expr, op)
        elif isinstance(target, Deref):
            node = DerefAssignStmt(target.expr, expr, op)
        else:
            raise ParseError(f"The left side of '{op_tok.value}' must be a variable, an array element "
                             f"or a dereferenced pointer at line {op_tok.line}")
        return self.at(node, target.line)

    def match_assignment(self):
        # Returns None for '=', or the arithmetic operator of a compound assignment
        if self.current_token.type == 'COMPOUND_ASSIGN':
            return self.match('COMPOUND_ASSIGN').value[0]
        self.match('ASSIGN')
        return None

    def parse_expression(self):
        return self.parse_logical_or()

    def parse_logical_or(self):
        node = self.parse_logical_and()
        while self.current_token.type == 'OR':
            op_tok = self.match('OR')
            right = self.parse_logical_and()
            node = self.at(BinOp(node, op_tok.value, right), op_tok.line)
        return node

    def parse_logical_and(self):
        node = self.parse_equality()
        while self.current_token.type == 'AND':
            op_tok = self.match('AND')
            right = self.parse_equality()
            node = self.at(BinOp(node, op_tok.value, right), op_tok.line)
        return node

    def parse_equality(self):
        node = self.parse_relational()
        while self.current_token.type in ('EQ', 'NEQ'):
            op_tok = self.current_token
            self.advance()
            right = self.parse_relational()
            node = self.at(BinOp(node, op_tok.value, right), op_tok.line)
        return node

    def parse_relational(self):
        node = self.parse_additive()
        while self.current_token.type in ('LT', 'GT', 'LE', 'GE'):
            op_tok = self.current_token
            self.advance()
            right = self.parse_additive()
            node = self.at(BinOp(node, op_tok.value, right), op_tok.line)
        return node

    def parse_additive(self):
        node = self.parse_multiplicative()
        while self.current_token.type in ('PLUS', 'MINUS'):
            op_tok = self.current_token
            self.advance()
            right = self.parse_multiplicative()
            node = self.at(BinOp(node, op_tok.value, right), op_tok.line)
        return node

    def parse_multiplicative(self):
        node = self.parse_unary()
        while self.current_token.type in ('MUL', 'DIV', 'MOD'):
            op_tok = self.current_token
            self.advance()
            right = self.parse_unary()
            node = self.at(BinOp(node, op_tok.value, right), op_tok.line)
        return node

    def parse_unary(self):
        if self.current_token.type in ('INC', 'DEC'):
            op_tok = self.current_token
            self.advance()
            return self.at(IncDec(self.parse_incdec_target(op_tok.value), op_tok.value, prefix=True), op_tok.line)
        if self.current_token.type in ('MINUS', 'NOT'):
            op_tok = self.current_token
            self.advance()
            expr = self.parse_unary()
            return self.at(UnaryOp(op_tok.value, expr), op_tok.line)
        if self.current_token.type == 'MUL':
            line = self.match('MUL').line
            return self.at(Deref(self.parse_unary()), line)
        if self.current_token.type == 'AMP':
            line = self.match('AMP').line
            return self.at(AddressOf(self.parse_unary()), line)
        return self.parse_primary()

    def parse_incdec_target(self, op):
        tok = self.current_token
        if tok.type != 'ID' or self.lexer.tokens[self.pos + 1].type == 'LBRACKET':
            raise ParseError(f"Operand of '{op}' must be a variable at line {tok.line}")
        self.advance()
        return tok.value

    def parse_primary(self):
        tok = self.current_token
        if tok.type == 'NUMBER':
            self.advance()
            val_type = 'float' if isinstance(tok.value, float) else 'int'
            return self.at(Number(tok.value, val_type), tok.line)
        elif tok.type == 'ID':
            self.advance()
            if self.current_token.type == 'LPAREN':
                # Function call
                self.match('LPAREN')
                args = []
                if self.current_token.type != 'RPAREN':
                    args.append(self.parse_expression())
                    while self.current_token.type == 'COMMA':
                        self.match('COMMA')
                        args.append(self.parse_expression())
                self.match('RPAREN')
                return self.at(FuncCall(tok.value, args), tok.line)
            elif self.current_token.type == 'LBRACKET':
                # Array access
                self.match('LBRACKET')
                idx = self.parse_expression()
                self.match('RBRACKET')
                return self.at(ArrayAccess(tok.value, idx), tok.line)
            elif self.current_token.type in ('INC', 'DEC'):
                op = self.current_token.value
                self.advance()
                return self.at(IncDec(tok.value, op, prefix=False), tok.line)
            else:
                return self.at(Var(tok.value), tok.line)
        elif tok.type == 'LPAREN':
            self.match('LPAREN')
            expr = self.parse_expression()
            self.match('RPAREN')
            return expr
        else:
            raise ParseError(f"Unexpected token {tok.type} at line {tok.line}")
