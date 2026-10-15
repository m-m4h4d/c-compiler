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

    def parse(self):
        declarations = []
        while self.current_token.type != 'EOF':
            declarations.append(self.parse_declaration())
        return Program(declarations)

    def parse_declaration(self):
        # type ID ...
        if self.current_token.type in ('INT', 'FLOAT', 'DOUBLE', 'VOID'):
            var_type = self.current_token.value
            line = self.current_token.line
            self.advance()
            name = self.match('ID').value
            
            # could be function, array or var
            if self.current_token.type == 'LPAREN':
                return self.parse_function_decl(var_type, name)
            elif var_type == 'void':
                raise ParseError(f"Variable '{name}' declared void at line {line}")
            elif self.current_token.type == 'LBRACKET':
                return self.parse_array_decl(var_type, name)
            else:
                return self.parse_var_decl(var_type, name)
        else:
            raise ParseError(f"Expected type specifier at line {self.current_token.line}")

    def parse_function_decl(self, return_type, name):
        self.match('LPAREN')
        params = []
        if self.current_token.type == 'VOID' and self.lexer.tokens[self.pos + 1].type == 'RPAREN':
            self.match('VOID') # f(void) means no parameters
        elif self.current_token.type != 'RPAREN':
            params.append(self.parse_param())
            while self.current_token.type == 'COMMA':
                self.match('COMMA')
                params.append(self.parse_param())
        self.match('RPAREN')
        body = self.parse_block()
        return FunctionDecl(return_type, name, params, body)

    def parse_param(self):
        if self.current_token.type in ('INT', 'FLOAT', 'DOUBLE'):
            p_type = self.current_token.value
            self.advance()
            name = self.match('ID').value
            return (p_type, name)
        raise ParseError(f"Expected type in parameter list at line {self.current_token.line}")

    def parse_array_decl(self, var_type, name):
        self.match('LBRACKET')
        size = self.match('NUMBER').value
        self.match('RBRACKET')
        self.match('SEMI')
        return ArrayDecl(var_type, name, size)

    def parse_var_decl(self, var_type, name):
        init_expr = None
        if self.current_token.type == 'ASSIGN':
            self.match('ASSIGN')
            init_expr = self.parse_expression()
        self.match('SEMI')
        return VarDecl(var_type, name, init_expr)

    def parse_block(self):
        self.match('LBRACE')
        statements = []
        while self.current_token.type != 'RBRACE' and self.current_token.type != 'EOF':
            if self.current_token.type in ('INT', 'FLOAT', 'DOUBLE'):
                # variable declaration inside block
                var_type = self.current_token.value
                self.advance()
                name = self.match('ID').value
                if self.current_token.type == 'LBRACKET':
                    statements.append(self.parse_array_decl(var_type, name))
                else:
                    statements.append(self.parse_var_decl(var_type, name))
            else:
                statements.append(self.parse_statement())
        self.match('RBRACE')
        return Block(statements)

    def parse_statement(self):
        if self.current_token.type == 'IF':
            return self.parse_if()
        elif self.current_token.type == 'WHILE':
            return self.parse_while()
        elif self.current_token.type == 'FOR':
            return self.parse_for()
        elif self.current_token.type == 'RETURN':
            return self.parse_return()
        elif self.current_token.type == 'LBRACE':
            return self.parse_block()
        else:
            return self.parse_expr_statement()

    def parse_if(self):
        self.match('IF')
        self.match('LPAREN')
        cond = self.parse_expression()
        self.match('RPAREN')
        then_b = self.parse_statement()
        else_b = None
        if self.current_token.type == 'ELSE':
            self.match('ELSE')
            else_b = self.parse_statement()
        return IfStmt(cond, then_b, else_b)

    def parse_while(self):
        self.match('WHILE')
        self.match('LPAREN')
        cond = self.parse_expression()
        self.match('RPAREN')
        body = self.parse_statement()
        return WhileStmt(cond, body)

    def parse_for(self):
        self.match('FOR')
        self.match('LPAREN')
        # Each of the three clauses may be empty
        if self.current_token.type in ('INT', 'FLOAT', 'DOUBLE'):
            var_type = self.current_token.value
            self.advance()
            name = self.match('ID').value
            init = self.parse_var_decl(var_type, name) # Includes SEMI
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
        return ForStmt(init, cond, inc, body)

    def parse_return(self):
        self.match('RETURN')
        expr = None
        if self.current_token.type != 'SEMI':
            expr = self.parse_expression()
        self.match('SEMI')
        return ReturnStmt(expr)

    def parse_expr_statement(self):
        expr = self.parse_assignment_expr()
        self.match('SEMI')
        return expr

    def parse_assignment_expr(self):
        if self.current_token.type == 'ID':
            # Could be assignment, array assignment, or function call
            next_tok = self.lexer.tokens[self.pos + 1]
            if next_tok.type == 'ASSIGN':
                name = self.match('ID').value
                self.match('ASSIGN')
                expr = self.parse_assignment_expr()
                return AssignStmt(name, expr)
            elif next_tok.type == 'LBRACKET':
                # Quick check if it's an assignment to array
                # Find matching bracket
                temp_pos = self.pos + 2
                brackets = 1
                while temp_pos < len(self.lexer.tokens) and brackets > 0:
                    if self.lexer.tokens[temp_pos].type == 'LBRACKET': brackets += 1
                    elif self.lexer.tokens[temp_pos].type == 'RBRACKET': brackets -= 1
                    temp_pos += 1
                if temp_pos < len(self.lexer.tokens) and self.lexer.tokens[temp_pos].type == 'ASSIGN':
                    name = self.match('ID').value
                    self.match('LBRACKET')
                    idx = self.parse_expression()
                    self.match('RBRACKET')
                    self.match('ASSIGN')
                    expr = self.parse_assignment_expr()
                    return ArrayAssignStmt(name, idx, expr)
        return self.parse_expression()

    def parse_expression(self):
        return self.parse_logical_or()

    def parse_logical_or(self):
        node = self.parse_logical_and()
        while self.current_token.type == 'OR':
            op = self.match('OR').value
            right = self.parse_logical_and()
            node = BinOp(node, op, right)
        return node

    def parse_logical_and(self):
        node = self.parse_equality()
        while self.current_token.type == 'AND':
            op = self.match('AND').value
            right = self.parse_equality()
            node = BinOp(node, op, right)
        return node

    def parse_equality(self):
        node = self.parse_relational()
        while self.current_token.type in ('EQ', 'NEQ'):
            op = self.current_token.value
            self.advance()
            right = self.parse_relational()
            node = BinOp(node, op, right)
        return node

    def parse_relational(self):
        node = self.parse_additive()
        while self.current_token.type in ('LT', 'GT', 'LE', 'GE'):
            op = self.current_token.value
            self.advance()
            right = self.parse_additive()
            node = BinOp(node, op, right)
        return node

    def parse_additive(self):
        node = self.parse_multiplicative()
        while self.current_token.type in ('PLUS', 'MINUS'):
            op = self.current_token.value
            self.advance()
            right = self.parse_multiplicative()
            node = BinOp(node, op, right)
        return node

    def parse_multiplicative(self):
        node = self.parse_unary()
        while self.current_token.type in ('MUL', 'DIV', 'MOD'):
            op = self.current_token.value
            self.advance()
            right = self.parse_unary()
            node = BinOp(node, op, right)
        return node

    def parse_unary(self):
        if self.current_token.type in ('INC', 'DEC'):
            op = self.current_token.value
            self.advance()
            return IncDec(self.parse_incdec_target(op), op, prefix=True)
        if self.current_token.type in ('MINUS', 'NOT'):
            op = self.current_token.value
            self.advance()
            expr = self.parse_unary()
            return UnaryOp(op, expr)
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
            return Number(tok.value, val_type)
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
                return FuncCall(tok.value, args)
            elif self.current_token.type == 'LBRACKET':
                # Array access
                self.match('LBRACKET')
                idx = self.parse_expression()
                self.match('RBRACKET')
                return ArrayAccess(tok.value, idx)
            elif self.current_token.type in ('INC', 'DEC'):
                op = self.current_token.value
                self.advance()
                return IncDec(tok.value, op, prefix=False)
            else:
                return Var(tok.value)
        elif tok.type == 'LPAREN':
            self.match('LPAREN')
            expr = self.parse_expression()
            self.match('RPAREN')
            return expr
        else:
            raise ParseError(f"Unexpected token {tok.type} at line {tok.line}")
