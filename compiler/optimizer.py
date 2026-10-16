import copy
import math
from ast_nodes import *

def wrap_i32(value):
    # Match the two's-complement wraparound of the generated i32 arithmetic
    return (value + 2**31) % 2**32 - 2**31

def c_div(lval, rval):
    # C integer division truncates toward zero; Python's // floors
    q = abs(lval) // abs(rval)
    return -q if (lval < 0) != (rval < 0) else q

def c_rem(lval, rval):
    # The remainder takes the sign of the dividend, so (a/b)*b + a%b == a
    return lval - rval * c_div(lval, rval)

def fold_constant(node):
    """The Number a constant expression folds to, or None. Leaves node untouched."""
    folded = Optimizer(None).visit(copy.deepcopy(node))
    return folded if isinstance(folded, Number) else None

class Optimizer:
    def __init__(self, ast):
        self.ast = ast

    def optimize(self):
        return self.visit(self.ast)

    def visit(self, node):
        if node is None:
            return None
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        return node

    def visit_Program(self, node):
        node.declarations = [self.visit(decl) for decl in node.declarations]
        return node

    def visit_FunctionDecl(self, node):
        node.body = self.visit(node.body)
        return node

    def visit_VarDecl(self, node):
        if node.init_expr:
            node.init_expr = self.visit(node.init_expr)
        return node

    def visit_ArrayDecl(self, node):
        return node

    def visit_Block(self, node):
        node.statements = self.optimize_statements(node.statements)
        return node

    def optimize_statements(self, statements):
        optimized_statements = []
        for stmt in statements:
            opt_stmt = self.visit(stmt)
            if opt_stmt:
                optimized_statements.append(opt_stmt)
            # Dead code elimination: nothing after a return, break or continue can run
            if isinstance(opt_stmt, (ReturnStmt, BreakStmt, ContinueStmt)):
                break
        return optimized_statements

    def visit_SwitchStmt(self, node):
        node.expr = self.visit(node.expr)
        for case in node.cases:
            case.value = self.visit(case.value)
            # Each case is cut separately: the next case label is reachable again
            case.statements = self.optimize_statements(case.statements)
        return node

    def visit_IfStmt(self, node):
        node.condition = self.visit(node.condition)
        node.then_branch = self.visit(node.then_branch)
        if node.else_branch:
            node.else_branch = self.visit(node.else_branch)
            
        # Constant Folding + Dead Code Elimination
        if isinstance(node.condition, Number):
            if node.condition.value != 0:
                return node.then_branch
            else:
                return node.else_branch
        return node

    def visit_WhileStmt(self, node):
        node.condition = self.visit(node.condition)
        node.body = self.visit(node.body)
        
        # Dead code elimination if condition is const 0
        if isinstance(node.condition, Number) and node.condition.value == 0:
            return None
        return node

    def visit_DoWhileStmt(self, node):
        # Even with a false condition the body runs once, so the loop is never removed
        node.body = self.visit(node.body)
        node.condition = self.visit(node.condition)
        return node

    def visit_ForStmt(self, node):
        node.init = self.visit(node.init)
        node.condition = self.visit(node.condition)
        node.increment = self.visit(node.increment)
        node.body = self.visit(node.body)
        
        # Dead code elimination
        if isinstance(node.condition, Number) and node.condition.value == 0:
            # Init still runs once; wrap it in a block so a declaration stays scoped to the loop
            return Block([node.init]) if node.init else None
        return node

    def visit_ReturnStmt(self, node):
        if node.expr:
            node.expr = self.visit(node.expr)
        return node

    def visit_AssignStmt(self, node):
        node.expr = self.visit(node.expr)
        return node

    def visit_ArrayAssignStmt(self, node):
        node.index_expr = self.visit(node.index_expr)
        node.expr = self.visit(node.expr)
        return node

    def visit_BinOp(self, node):
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        
        # Constant Folding
        if isinstance(node.left, Number) and isinstance(node.right, Number):
            lval = node.left.value
            rval = node.right.value
            op = node.op
            is_float = node.left.val_type == 'float' or node.right.val_type == 'float'
            
            if op in ('+', '-', '*', '/', '%'):
                if is_float:
                    lval, rval = float(lval), float(rval)
                    if op == '+': result = lval + rval
                    elif op == '-': result = lval - rval
                    elif op == '*': result = lval * rval
                    elif rval == 0.0: return node # leave inf/NaN to run time
                    elif op == '/': result = lval / rval
                    else: result = math.fmod(lval, rval)
                    return Number(result, 'float')
                if op == '+': result = lval + rval
                elif op == '-': result = lval - rval
                elif op == '*': result = lval * rval
                elif rval == 0: return node # don't fold division by zero
                elif op == '/': result = c_div(lval, rval)
                else: result = c_rem(lval, rval)
                return Number(wrap_i32(result), 'int')
            
            # Comparisons and logical operators always produce an int 0 or 1
            if op == '==': result = 1 if lval == rval else 0
            elif op == '!=': result = 1 if lval != rval else 0
            elif op == '<': result = 1 if lval < rval else 0
            elif op == '<=': result = 1 if lval <= rval else 0
            elif op == '>': result = 1 if lval > rval else 0
            elif op == '>=': result = 1 if lval >= rval else 0
            elif op == '&&': result = 1 if lval and rval else 0
            elif op == '||': result = 1 if lval or rval else 0
            else: return node
            return Number(result, 'int')
        return node

    def visit_UnaryOp(self, node):
        node.expr = self.visit(node.expr)
        
        # Constant Folding
        if isinstance(node.expr, Number):
            if node.op == '-':
                if node.expr.val_type == 'int':
                    return Number(wrap_i32(-node.expr.value), 'int')
                return Number(-node.expr.value, node.expr.val_type)
            elif node.op == '!':
                return Number(1 if not node.expr.value else 0, 'int')
        return node

    def visit_Var(self, node):
        return node

    def visit_ArrayAccess(self, node):
        node.index_expr = self.visit(node.index_expr)
        return node

    def visit_Number(self, node):
        return node

    def visit_FuncCall(self, node):
        node.args = [self.visit(arg) for arg in node.args]
        return node
