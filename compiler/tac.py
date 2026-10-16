from ast_nodes import *
from optimizer import fold_constant

class TACGenerator:
    def __init__(self, ast):
        self.ast = ast
        self.code = []
        self.temp_count = 0
        self.label_count = 0
        self.loops = [] # (continue label, break label) for each enclosing loop
        self.struct_fields = {} # struct name -> [(type, field)], for spelling out initializers

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
            if isinstance(decl, StructDecl):
                self.struct_fields[decl.name] = decl.fields
                fields = ', '.join(f"{c_type} {name}" for c_type, name in decl.fields)
                self.emit(f"struct {decl.name} {{ {fields} }}")
            elif isinstance(decl, VarDecl):
                init = f" = {self.render_constant(decl.init_expr)}" if decl.init_expr else ""
                self.emit(f"global {decl.name}{init}")
            elif isinstance(decl, ArrayDecl):
                init = f" = {self.render_constant(decl.init)}" if decl.init else ""
                self.emit(f"global_array {decl.name}, {decl.size}{init}")
            else:
                self.visit(decl)

    def visit_FunctionDecl(self, node):
        self.emit(f"func {node.name}:")
        self.emit(f"begin_func")
        self.visit(node.body)
        self.emit(f"end_func")
        self.emit("") # blank line for readability

    def render_constant(self, init):
        if init is None:
            return '0' # a member left at zero
        if isinstance(init, InitList):
            return '{' + ', '.join(self.render_constant(item) for item in init.items) + '}'
        return self.visit(init)

    def visit_VarDecl(self, node):
        if isinstance(node.init_expr, InitList):
            self.emit(f"clear {node.name}") # members the list leaves out are zero
            self.emit_init(node.name, node.var_type, node.init_expr)
        elif node.init_expr:
            val = self.visit(node.init_expr)
            self.emit(f"{node.name} = {val}")

    def visit_ArrayDecl(self, node):
        self.emit(f"alloc_array {node.name}, {node.size}")
        if node.init is not None:
            self.emit(f"clear {node.name}")
            self.emit_init(node.name, f"{node.var_type}[{node.size}]", node.init)

    def emit_init(self, target, c_type, init):
        # One assignment per value in a (fully braced) initializer
        if not isinstance(init, InitList):
            self.emit(f"{target} = {self.visit(init)}")
            return
        if c_type.endswith(']'):
            element = c_type[:c_type.rindex('[')]
            members = [(element, f"{target}[{i}]") for i in range(len(init.items))]
        else:
            fields = self.struct_fields[c_type[len('struct '):]]
            members = [(field_type, f"{target}.{name}") for field_type, name in fields]
        for (member_type, member_target), item in zip(members, init.items):
            if item is not None: # None is a member left at zero
                self.emit_init(member_target, member_type, item)

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

    def visit_DoWhileStmt(self, node):
        label_start = self.new_label()
        label_cond = self.new_label()
        label_end = self.new_label()

        self.emit(f"{label_start}:")
        # continue goes to the condition, which decides whether to loop again
        self.visit_loop_body(node.body, label_cond, label_end)
        self.emit(f"{label_cond}:")
        cond_val = self.visit(node.condition)
        self.emit(f"if_false {cond_val} goto {label_end}")
        self.emit(f"goto {label_start}")
        self.emit(f"{label_end}:")

    def visit_SwitchStmt(self, node):
        value = self.visit(node.expr)
        label_end = self.new_label()
        case_labels = [self.new_label() for _ in node.cases]
        default_label = label_end
        for case, label in zip(node.cases, case_labels):
            if case.value is None:
                default_label = label
            else:
                self.emit(f"if {value} == {fold_constant(case.value).value} goto {label}")
        self.emit(f"goto {default_label}")

        # break leaves the switch; continue still belongs to the enclosing loop
        enclosing_continue = self.loops[-1][0] if self.loops else None
        self.loops.append((enclosing_continue, label_end))
        for case, label in zip(node.cases, case_labels):
            self.emit(f"{label}:") # falls through from the case above
            for stmt in case.statements:
                self.visit(stmt)
        self.loops.pop()
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

    def visit_DerefAssignStmt(self, node):
        ptr = self.visit(node.pointer_expr)
        val = self.visit(node.expr)
        if node.op:
            old = self.new_temp()
            self.emit(f"{old} = *{ptr}")
            temp = self.new_temp()
            self.emit(f"{temp} = {old} {node.op} {val}")
            val = temp
        self.emit(f"*{ptr} = {val}")

    def visit_Deref(self, node):
        ptr = self.visit(node.expr)
        temp = self.new_temp()
        self.emit(f"{temp} = *{ptr}")
        return temp

    def visit_AddressOf(self, node):
        target = node.expr
        temp = self.new_temp()
        if isinstance(target, Var):
            self.emit(f"{temp} = &{target.name}")
        elif isinstance(target, Deref):
            return self.visit(target.expr) # &*p is p
        else:
            self.emit(f"{temp} = &{self.place(target)}")
        return temp

    def place(self, node):
        """Text for an assignable place, evaluating any index or pointer inside it."""
        if isinstance(node, Var):
            return node.name
        if isinstance(node, ArrayAccess):
            return f"{node.name}[{self.visit(node.index_expr)}]"
        if isinstance(node, Deref):
            return f"*{self.visit(node.expr)}"
        if isinstance(node, Member):
            if node.arrow:
                return f"{self.visit(node.base)}->{node.field}"
            base = self.place(node.base) if isinstance(node.base, (Var, ArrayAccess, Deref, Member, Index)) else self.visit(node.base)
            return f"{base}.{node.field}"
        base = self.visit(node.base)
        return f"{base}[{self.visit(node.index_expr)}]"

    def visit_Member(self, node):
        temp = self.new_temp()
        self.emit(f"{temp} = {self.place(node)}")
        return temp

    visit_Index = visit_Member

    def visit_LValueAssignStmt(self, node):
        target = self.place(node.target)
        val = self.visit(node.expr)
        if node.op:
            old = self.new_temp()
            self.emit(f"{old} = {target}")
            temp = self.new_temp()
            self.emit(f"{temp} = {old} {node.op} {val}")
            val = temp
        self.emit(f"{target} = {val}")

    def visit_LValueIncDec(self, node):
        target = self.place(node.target)
        old = self.new_temp()
        self.emit(f"{old} = {target}")
        self.emit(f"{target} = {old} {'+' if node.op == '++' else '-'} 1")
        if node.prefix:
            new = self.new_temp()
            self.emit(f"{new} = {target}")
            return new
        return old

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
