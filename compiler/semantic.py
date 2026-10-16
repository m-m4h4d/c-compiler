from ast_nodes import *
from optimizer import fold_constant

class SemanticError(Exception):
    def __init__(self, message, line=None):
        # Same "at line N" form as parse errors
        super().__init__(f"{message} at line {line}" if line is not None else message)
        self.line = line

class SymbolTable:
    def __init__(self):
        self.scopes = [{}] # Stack of dictionaries

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        self.scopes.pop()

    def declare(self, name, var_type, is_array=False, size=None, line=None):
        current_scope = self.scopes[-1]
        if name in current_scope:
            raise SemanticError(f"Variable '{name}' already declared in current scope", line)
        current_scope[name] = {'type': var_type, 'is_array': is_array, 'size': size}

    def declare_function(self, name, return_type, params, line=None):
        global_scope = self.scopes[0]
        if name in global_scope:
            raise SemanticError(f"Function '{name}' already declared", line)
        global_scope[name] = {'type': 'function', 'return_type': return_type, 'params': params}

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

# Usual arithmetic conversions: the wider operand type wins
TYPE_RANK = {'int': 0, 'float': 1, 'double': 2}

def wider(left, right):
    return max(left, right, key=TYPE_RANK.get)

class SemanticAnalyzer:
    """Checks scoping and declarations, and the type of every expression.

    Expression visitors return the expression's type: 'int', 'float',
    'double' or 'void' (a call to a void function).
    """
    def __init__(self, ast):
        self.ast = ast
        self.symtab = SymbolTable()
        self.current_function = None
        self.loop_depth = 0
        self.switch_depth = 0 # break also works inside a switch; continue does not

    def analyze(self):
        self.visit(self.ast)

    def visit(self, node):
        if node is None:
            return None
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f'No visit_{type(node).__name__} method')

    def visit_Program(self, node):
        for decl in node.declarations:
            if isinstance(decl, VarDecl) and decl.init_expr and not self.is_constant(decl.init_expr):
                raise SemanticError(f"Initializer of global variable '{decl.name}' must be a constant expression", decl.line)
            self.visit(decl)

    def is_constant(self, node):
        if isinstance(node, Number):
            return True
        if isinstance(node, UnaryOp):
            return self.is_constant(node.expr)
        if isinstance(node, BinOp):
            return self.is_constant(node.left) and self.is_constant(node.right)
        return False

    def visit_statement(self, node):
        # A call whose result is discarded may return void; anywhere else it may not
        if isinstance(node, FuncCall):
            self.visit_FuncCall(node, value_used=False)
        else:
            self.visit(node)

    def visit_FunctionDecl(self, node):
        self.symtab.declare_function(node.name, node.return_type, node.params, node.line)
        self.current_function = node
        self.symtab.enter_scope()
        param_lines = getattr(node, 'param_lines', [node.line] * len(node.params))
        for (p_type, p_name), line in zip(node.params, param_lines):
            self.symtab.declare(p_name, p_type, line=line)
        self.visit(node.body)
        self.symtab.exit_scope()
        self.current_function = None

    def visit_VarDecl(self, node):
        self.symtab.declare(node.name, node.var_type, line=node.line)
        if node.init_expr:
            self.visit(node.init_expr)

    def visit_ArrayDecl(self, node):
        if not isinstance(node.size, int) or node.size <= 0:
            raise SemanticError(f"Size of array '{node.name}' must be a positive integer, not {node.size}", node.line)
        self.symtab.declare(node.name, node.var_type, is_array=True, size=node.size, line=node.line)

    def visit_Block(self, node):
        self.symtab.enter_scope()
        for stmt in node.statements:
            self.visit_statement(stmt)
        self.symtab.exit_scope()

    def visit_IfStmt(self, node):
        self.visit(node.condition)
        self.visit_statement(node.then_branch)
        if node.else_branch:
            self.visit_statement(node.else_branch)

    def visit_WhileStmt(self, node):
        self.visit(node.condition)
        self.visit_loop_body(node.body)

    def visit_DoWhileStmt(self, node):
        # The body's declarations are out of scope again by the time the condition runs
        self.visit_loop_body(node.body)
        self.visit(node.condition)

    def visit_loop_body(self, body):
        self.loop_depth += 1
        self.visit_statement(body)
        self.loop_depth -= 1

    def visit_BreakStmt(self, node):
        if self.loop_depth == 0 and self.switch_depth == 0:
            raise SemanticError("'break' outside of a loop or switch", node.line)

    def visit_ContinueStmt(self, node):
        if self.loop_depth == 0:
            raise SemanticError("'continue' outside of a loop", node.line)

    def visit_SwitchStmt(self, node):
        self.require_int(self.visit(node.expr), "Switch value", node.line)
        seen = {}
        default_line = None
        for case in node.cases:
            if case.value is None:
                if default_line is not None:
                    raise SemanticError(f"Second 'default' label in one switch (the first is on line {default_line})", case.line)
                default_line = case.line
                continue
            self.visit(case.value)
            folded = fold_constant(case.value)
            if folded is None:
                raise SemanticError("Case label must be a constant expression", case.line)
            if folded.val_type != 'int':
                raise SemanticError("Case label must be an integer constant", case.line)
            if folded.value in seen:
                raise SemanticError(f"Duplicate case value {folded.value} (first used on line {seen[folded.value]})", case.line)
            seen[folded.value] = case.line

        # The whole body is one scope, so a declaration in one case is visible in later ones
        self.switch_depth += 1
        self.symtab.enter_scope()
        for case in node.cases:
            for stmt in case.statements:
                self.visit_statement(stmt)
        self.symtab.exit_scope()
        self.switch_depth -= 1

    def visit_ForStmt(self, node):
        self.symtab.enter_scope()
        self.visit_statement(node.init)
        self.visit(node.condition)
        self.visit_statement(node.increment)
        self.visit_loop_body(node.body)
        self.symtab.exit_scope()

    def visit_ReturnStmt(self, node):
        if node.expr:
            if self.current_function.return_type == 'void':
                raise SemanticError(f"Void function '{self.current_function.name}' cannot return a value", node.line)
            self.visit(node.expr)

    def visit_AssignStmt(self, node):
        var_info = self.symtab.lookup(node.name)
        if not var_info:
            raise SemanticError(f"Undeclared variable '{node.name}'", node.line)
        if var_info.get('type') == 'function':
            raise SemanticError(f"'{node.name}' is a function, not a variable", node.line)
        if var_info.get('is_array'):
            raise SemanticError(f"Cannot assign to array '{node.name}' directly", node.line)
        value_type = self.visit(node.expr)
        if node.op == '%':
            self.require_int(var_info['type'], f"Target of '%='", node.line)
            self.require_int(value_type, f"Right side of '%='", node.line)
        return var_info['type']

    def visit_ArrayAssignStmt(self, node):
        var_info = self.symtab.lookup(node.name)
        if not var_info:
            raise SemanticError(f"Undeclared array '{node.name}'", node.line)
        if not var_info.get('is_array'):
            raise SemanticError(f"'{node.name}' is not an array", node.line)
        self.require_int(self.visit(node.index_expr), "Array index", node.line)
        value_type = self.visit(node.expr)
        if node.op == '%':
            self.require_int(var_info['type'], f"Target of '%='", node.line)
            self.require_int(value_type, f"Right side of '%='", node.line)
        return var_info['type']

    def require_int(self, actual, what, line):
        if actual != 'int':
            raise SemanticError(f"{what} must be an integer, not {actual}", line)

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if node.op == '%':
            if left != 'int' or right != 'int':
                raise SemanticError(f"Operands of '%' must be integers, not {left} and {right}", node.line)
            return 'int'
        if node.op in ('+', '-', '*', '/'):
            return wider(left, right)
        return 'int' # comparisons and logical operators yield 0 or 1

    def visit_UnaryOp(self, node):
        operand = self.visit(node.expr)
        return operand if node.op == '-' else 'int'

    def visit_IncDec(self, node):
        var_info = self.symtab.lookup(node.name)
        if not var_info:
            raise SemanticError(f"Undeclared variable '{node.name}'", node.line)
        if var_info.get('type') == 'function' or var_info.get('is_array'):
            raise SemanticError(f"Operand of '{node.op}' must be a scalar variable, got '{node.name}'", node.line)
        return var_info['type']

    def visit_Var(self, node):
        var_info = self.symtab.lookup(node.name)
        if not var_info:
            raise SemanticError(f"Undeclared variable '{node.name}'", node.line)
        if var_info.get('type') == 'function':
            raise SemanticError(f"'{node.name}' is a function, not a variable", node.line)
        if var_info.get('is_array'):
            # In C the array would decay to a pointer, which this subset doesn't have
            raise SemanticError(f"Array '{node.name}' can only be used through an element, such as {node.name}[0]", node.line)
        return var_info['type']

    def visit_ArrayAccess(self, node):
        var_info = self.symtab.lookup(node.name)
        if not var_info:
            raise SemanticError(f"Undeclared array '{node.name}'", node.line)
        if not var_info.get('is_array'):
            raise SemanticError(f"'{node.name}' is not an array", node.line)
        self.require_int(self.visit(node.index_expr), "Array index", node.line)
        return var_info['type']

    def visit_Number(self, node):
        # C floating literals have type double
        return 'int' if node.val_type == 'int' else 'double'

    def visit_FuncCall(self, node, value_used=True):
        func_info = self.symtab.lookup(node.name)
        if not func_info:
            raise SemanticError(f"Undeclared function '{node.name}'", node.line)
        if func_info.get('type') != 'function':
            raise SemanticError(f"'{node.name}' is not a function", node.line)
        if len(node.args) != len(func_info['params']):
            raise SemanticError(f"Function '{node.name}' expects {len(func_info['params'])} arguments, got {len(node.args)}", node.line)
        if value_used and func_info['return_type'] == 'void':
            raise SemanticError(f"Result of void function '{node.name}' used as a value", node.line)
        for arg in node.args:
            self.visit(arg)
        return func_info['return_type']
