from ast_nodes import *

class TACGenerator:
    def __init__(self, ast):
        self.ast = ast
        self.code = []
        self.temp_count = 0
        self.label_count = 0
        self.loops = [] # (continue label, break label) for each enclosing loop

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, instruction):
        self.code.append(instruction)

    def generate(self):
        self.visit(self.ast)
        return self.code

    def visit(self, node):
        if node is None:
            return None
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        return None

    def visit_Program(self, node):
        for decl in node.declarations:
            if isinstance(decl, VarDecl):
                init = f" = {self.visit(decl.init_expr)}" if decl.init_expr else ""
                self.emit(f"global {decl.name}{init}")
            elif isinstance(decl, ArrayDecl):
                self.emit(f"global_array {decl.name}, {decl.size}")
            else:
                self.visit(decl)

    def visit_FunctionDecl(self, node):
        self.emit(f"func {node.name}:")
        self.emit(f"begin_func")
        self.visit(node.body)
        self.emit(f"end_func")
        self.emit("") # blank line for readability

    def visit_VarDecl(self, node):
        if node.init_expr:
            val = self.visit(node.init_expr)
            self.emit(f"{node.name} = {val}")

    def visit_ArrayDecl(self, node):
        self.emit(f"alloc_array {node.name}, {node.size}")

    def visit_Block(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_IfStmt(self, node):
        cond_val = self.visit(node.condition)
        label_else = self.new_label()
        label_end = self.new_label()
        
        self.emit(f"if_false {cond_val} goto {label_else}")
        self.visit(node.then_branch)
        self.emit(f"goto {label_end}")
        self.emit(f"{label_else}:")
        if node.else_branch:
            self.visit(node.else_branch)
        self.emit(f"{label_end}:")

    def visit_WhileStmt(self, node):
        label_start = self.new_label()
        label_end = self.new_label()
        
        self.emit(f"{label_start}:")
        cond_val = self.visit(node.condition)
        self.emit(f"if_false {cond_val} goto {label_end}")
        self.visit_loop_body(node.body, label_start, label_end)
        self.emit(f"goto {label_start}")
        self.emit(f"{label_end}:")

    def visit_ForStmt(self, node):
        self.visit(node.init)
        label_start = self.new_label()
        label_next = self.new_label()
        label_end = self.new_label()
        
        self.emit(f"{label_start}:")
        if node.condition is not None: # an empty condition loops forever
            cond_val = self.visit(node.condition)
            self.emit(f"if_false {cond_val} goto {label_end}")
        # continue jumps to the increment, not straight back to the condition
        self.visit_loop_body(node.body, label_next, label_end)
        self.emit(f"{label_next}:")
        self.visit(node.increment)
        self.emit(f"goto {label_start}")
        self.emit(f"{label_end}:")

    def visit_loop_body(self, body, continue_label, break_label):
        self.loops.append((continue_label, break_label))
        self.visit(body)
        self.loops.pop()

    def visit_BreakStmt(self, node):
        self.emit(f"goto {self.loops[-1][1]}")

    def visit_ContinueStmt(self, node):
        self.emit(f"goto {self.loops[-1][0]}")

    def visit_ReturnStmt(self, node):
        if node.expr:
            val = self.visit(node.expr)
            self.emit(f"return {val}")
        else:
            self.emit(f"return")

    def visit_AssignStmt(self, node):
        val = self.visit(node.expr)
        if node.op:
            temp = self.new_temp()
            self.emit(f"{temp} = {node.name} {node.op} {val}")
            val = temp
        self.emit(f"{node.name} = {val}")
        return node.name

    def visit_ArrayAssignStmt(self, node):
        # The index is evaluated once, even for a compound assignment
        idx_val = self.visit(node.index_expr)
        val = self.visit(node.expr)
        if node.op:
            old = self.new_temp()
            self.emit(f"{old} = {node.name}[{idx_val}]")
            temp = self.new_temp()
            self.emit(f"{temp} = {old} {node.op} {val}")
            val = temp
        self.emit(f"{node.name}[{idx_val}] = {val}")

    def visit_BinOp(self, node):
        left_val = self.visit(node.left)
        right_val = self.visit(node.right)
        temp = self.new_temp()
        self.emit(f"{temp} = {left_val} {node.op} {right_val}")
        return temp

    def visit_UnaryOp(self, node):
        val = self.visit(node.expr)
        temp = self.new_temp()
        self.emit(f"{temp} = {node.op} {val}")
        return temp

    def visit_IncDec(self, node):
        arith = '+' if node.op == '++' else '-'
        if node.prefix:
            self.emit(f"{node.name} = {node.name} {arith} 1")
            return node.name
        old = self.new_temp()
        self.emit(f"{old} = {node.name}")
        self.emit(f"{node.name} = {node.name} {arith} 1")
        return old

    def visit_Var(self, node):
        return node.name

    def visit_ArrayAccess(self, node):
        idx_val = self.visit(node.index_expr)
        temp = self.new_temp()
        self.emit(f"{temp} = {node.name}[{idx_val}]")
        return temp

    def visit_Number(self, node):
        return str(node.value)

    def visit_FuncCall(self, node):
        args_vals = []
        for arg in node.args:
            args_vals.append(self.visit(arg))
        for arg_val in args_vals:
            self.emit(f"param {arg_val}")
        temp = self.new_temp()
        self.emit(f"{temp} = call {node.name}, {len(args_vals)}")
        return temp
