class ASTNode:
    line = None # source line, set by the parser

class Program(ASTNode):
    def __init__(self, declarations):
        self.declarations = declarations

class FunctionDecl(ASTNode):
    def __init__(self, return_type, name, params, body):
        self.return_type = return_type
        self.name = name
        self.params = params  # list of (type, name)
        self.body = body

class VarDecl(ASTNode):
    def __init__(self, var_type, name, init_expr=None):
        self.var_type = var_type
        self.name = name
        self.init_expr = init_expr

class ArrayDecl(ASTNode):
    def __init__(self, var_type, name, size):
        self.var_type = var_type
        self.name = name
        self.size = size

class Block(ASTNode):
    def __init__(self, statements):
        self.statements = statements

class IfStmt(ASTNode):
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

class WhileStmt(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class ForStmt(ASTNode):
    def __init__(self, init, condition, increment, body):
        self.init = init
        self.condition = condition
        self.increment = increment
        self.body = body

class ReturnStmt(ASTNode):
    def __init__(self, expr=None):
        self.expr = expr

class BreakStmt(ASTNode):
    pass

class ContinueStmt(ASTNode):
    pass

class AssignStmt(ASTNode):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

class ArrayAssignStmt(ASTNode):
    def __init__(self, name, index_expr, expr):
        self.name = name
        self.index_expr = index_expr
        self.expr = expr

class BinOp(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(ASTNode):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

class Var(ASTNode):
    def __init__(self, name):
        self.name = name

class ArrayAccess(ASTNode):
    def __init__(self, name, index_expr):
        self.name = name
        self.index_expr = index_expr

class Number(ASTNode):
    def __init__(self, value, val_type):
        self.value = value
        self.val_type = val_type # 'int' or 'float'

class FuncCall(ASTNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args

class IncDec(ASTNode):
    def __init__(self, name, op, prefix):
        self.name = name
        self.op = op # '++' or '--'
        self.prefix = prefix # True for ++x (yields new value), False for x++ (yields old value)
