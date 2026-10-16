import struct
from ast_nodes import *
from optimizer import fold_constant

# Higher rank wins when two operand types meet in an expression
TYPE_RANK = {'i32': 0, 'float': 1, 'double': 2}

# Pointers use LLVM's typed syntax (i32*, double**), so pointee() is a slice
def is_pointer(llvm_type):
    return llvm_type.endswith('*')

def pointee(llvm_type):
    return llvm_type[:-1]

# Bytes per element, for the distance between two pointers
SIZE_OF = {'i32': 4, 'float': 4, 'double': 8}
def size_of(llvm_type):
    if is_pointer(llvm_type):
        return 8
    if llvm_type in SIZE_OF:
        return SIZE_OF[llvm_type]
    # Structs and arrays: let LLVM compute the size (including padding) as the
    # address of element 1 in an array starting at null
    return f"ptrtoint ({llvm_type}* getelementptr ({llvm_type}, {llvm_type}* null, i32 1) to i64)"

def is_aggregate(llvm_type):
    # Struct (%struct.Name) and array ([N x T]) values
    return not is_pointer(llvm_type) and (llvm_type.startswith('%struct.') or llvm_type.startswith('['))

ICMP_OPS = {'==': 'eq', '!=': 'ne', '<': 'slt', '<=': 'sle', '>': 'sgt', '>=': 'sge'}
FCMP_OPS = {'==': 'oeq', '!=': 'une', '<': 'olt', '<=': 'ole', '>': 'ogt', '>=': 'oge'}
INT_ARITH = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'sdiv', '%': 'srem'}
FLOAT_ARITH = {'+': 'fadd', '-': 'fsub', '*': 'fmul', '/': 'fdiv', '%': 'frem'}

class LLVMGenerator:
    def __init__(self, ast, symtab):
        self.ast = ast
        self.symtab = symtab
        self.code = []
        self.reg_count = 0
        self.label_count = 0
        self.scopes = [] # stack of dicts mapping var name to {'ptr', 'type', ...}
        self.globals = {}
        self.functions = {} # name -> {'ret': llvm type, 'params': [llvm types]}
        self.structs = {} # name -> {field: (index, llvm type)}
        self.allocas = [] # stack slots for the current function, placed in its entry block
        self.slot_count = 0
        self.current_ret_type = None
        self.current_label = None
        self.terminated = False # True once the current basic block has a terminator
        self.loops = [] # (continue label, break label) for each enclosing loop

    def new_reg(self):
        self.reg_count += 1
        return f"%{self.reg_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def new_slot(self, name, alloc_type):
        # Named rather than numbered: numbered values must appear in order, but
        # these are hoisted above code that was generated before them
        self.slot_count += 1
        ptr = f"%{name}.addr{self.slot_count}"
        self.allocas.append(f"  {ptr} = alloca {alloc_type}")
        return ptr

    def emit(self, instruction):
        self.code.append(instruction)

    def emit_inst(self, instruction):
        # Code after a terminator is unreachable, but LLVM still needs it inside a block
        if self.terminated:
            self.emit_label(self.new_label())
        self.emit(f"  {instruction}")

    def emit_label(self, label):
        self.emit(f"{label}:")
        self.current_label = label
        self.terminated = False

    def emit_terminator(self, instruction):
        # A block can hold only one terminator; anything after the first is dead
        if self.terminated:
            return
        self.emit(f"  {instruction}")
        self.terminated = True

    def map_type(self, c_type):
        if c_type.endswith(']'):
            # An array field such as 'int[4]' becomes [4 x i32]
            open_bracket = c_type.rindex('[')
            return f"[{c_type[open_bracket + 1:-1]} x {self.map_type(c_type[:open_bracket])}]"
        stars = len(c_type) - len(c_type.rstrip('*')) # 'int**' maps to 'i32**'
        base = c_type[:len(c_type) - stars]
        if base.startswith('struct '):
            llvm_base = f"%struct.{base[len('struct '):]}"
        else:
            llvm_base = {'int': 'i32', 'float': 'float', 'double': 'double', 'void': 'void'}.get(base, 'i32')
        return llvm_base + '*' * stars

    def default_value(self, llvm_type):
        if is_pointer(llvm_type):
            return 'null'
        if is_aggregate(llvm_type):
            return 'zeroinitializer'
        return '0' if llvm_type == 'i32' else '0.0'

    def float_constant(self, value, llvm_type):
        # LLVM wants float and double constants as the hex bits of a double; a
        # float constant must also be exactly representable in single precision
        if llvm_type == 'float':
            value = struct.unpack('>f', struct.pack('>f', value))[0]
        return f"0x{struct.pack('>d', value).hex().upper()}"

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        self.scopes.pop()

    def declare(self, name, info):
        self.scopes[-1][name] = info

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise KeyError(f"Codegen: unknown variable '{name}'")

    def convert(self, val, from_type, to_type):
        if from_type == to_type:
            return val
        if is_pointer(to_type):
            # Semantic analysis only lets the integer constant 0 reach a pointer
            return 'null'
        res = self.new_reg()
        if from_type == 'i32':
            self.emit_inst(f"{res} = sitofp i32 {val} to {to_type}")
        elif to_type == 'i32':
            self.emit_inst(f"{res} = fptosi {from_type} {val} to i32")
        elif TYPE_RANK[to_type] > TYPE_RANK[from_type]:
            self.emit_inst(f"{res} = fpext {from_type} {val} to {to_type}")
        else:
            self.emit_inst(f"{res} = fptrunc {from_type} {val} to {to_type}")
        return res

    def to_i1(self, val, val_type):
        res = self.new_reg()
        if is_pointer(val_type):
            self.emit_inst(f"{res} = icmp ne {val_type} {val}, null")
        elif val_type == 'i32':
            self.emit_inst(f"{res} = icmp ne i32 {val}, 0")
        else:
            self.emit_inst(f"{res} = fcmp une {val_type} {val}, 0.0")
        return res

    def i1_to_i32(self, val):
        res = self.new_reg()
        self.emit_inst(f"{res} = zext i1 {val} to i32")
        return res

    def generate(self):
        self.emit("; LLVM IR Generated by Custom Compiler")
        self.emit("declare i32 @printf(i8*, ...)")
        self.visit(self.ast)
        return "\n".join(self.code) + "\n"

    def visit(self, node):
        if node is None:
            return None
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        return None

    def visit_Program(self, node):
        # Struct layouts come first: every later declaration may refer to them
        for decl in node.declarations:
            if isinstance(decl, StructDecl):
                fields = [(name, self.map_type(c_type)) for c_type, name in decl.fields]
                self.structs[decl.name] = {name: (i, llvm_type) for i, (name, llvm_type) in enumerate(fields)}
                self.emit(f"%struct.{decl.name} = type {{ {', '.join(t for _, t in fields)} }}")
        # Collect signatures first so calls know their argument and return types
        for decl in node.declarations:
            if isinstance(decl, FunctionDecl):
                self.functions[decl.name] = {
                    'ret': self.map_type(decl.return_type),
                    'params': [self.map_type(p_type) for p_type, _ in decl.params],
                }
        for decl in node.declarations:
            if isinstance(decl, VarDecl):
                self.emit_global_var(decl)
            elif isinstance(decl, ArrayDecl):
                self.emit_global_array(decl)
            else:
                self.visit(decl)

    def emit_global_var(self, node):
        llvm_type = self.map_type(node.var_type)
        self.emit(f"@{node.name} = global {llvm_type} {self.constant_init(llvm_type, node.init_expr)}")
        self.globals[node.name] = {'ptr': f"@{node.name}", 'type': llvm_type}

    def emit_global_array(self, node):
        llvm_type = self.map_type(node.var_type)
        array_type = f"[{node.size} x {llvm_type}]"
        self.emit(f"@{node.name} = global {array_type} {self.constant_init(array_type, node.init)}")
        self.globals[node.name] = {'ptr': f"@{node.name}", 'type': llvm_type, 'array_type': array_type}

    def members(self, llvm_type):
        """The member types of a struct or array type, in order."""
        if llvm_type.startswith('%struct.'):
            fields = self.structs[llvm_type[len('%struct.'):]].values()
            return [field_type for _, field_type in sorted(fields)]
        count, element = llvm_type[1:-1].split(' x ', 1)
        return [element] * int(count)

    def constant_init(self, llvm_type, init):
        """An LLVM constant for a global's initializer; semantic analysis has made it fully braced."""
        if init is None:
            return self.default_value(llvm_type)
        if isinstance(init, InitList):
            members = self.members(llvm_type)
            items = init.items + [None] * (len(members) - len(init.items)) # left out means zero
            parts = ', '.join(f"{t} {self.constant_init(t, item)}" for t, item in zip(members, items))
            return f"{{ {parts} }}" if llvm_type.startswith('%struct.') else f"[{parts}]"
        folded = fold_constant(init)
        if folded is None:
            raise ValueError("Codegen: a global initializer did not fold to a constant")
        if is_pointer(llvm_type):
            return 'null' # the only constant a pointer can start from
        if llvm_type == 'i32':
            return str(int(folded.value)) # C converts by truncating toward zero
        return self.float_constant(float(folded.value), llvm_type)

    def init_at(self, ptr, llvm_type, init):
        # Store an initializer into memory that has already been zeroed
        if not isinstance(init, InitList):
            val, val_type = self.visit(init)
            self.store(ptr, llvm_type, val, val_type)
            return
        for index, (member_type, item) in enumerate(zip(self.members(llvm_type), init.items)):
            member_ptr = self.new_reg()
            self.emit_inst(f"{member_ptr} = getelementptr {llvm_type}, {llvm_type}* {ptr}, i32 0, i32 {index}")
            self.init_at(member_ptr, member_type, item)

    def visit_FunctionDecl(self, node):
        ret_type = self.map_type(node.return_type)
        params = []
        for p_type, p_name in node.params:
            params.append(f"{self.map_type(p_type)} %{p_name}_arg")

        param_str = ", ".join(params)
        self.emit(f"\ndefine {ret_type} @{node.name}({param_str}) {{")
        self.reg_count = 0
        self.slot_count = 0
        self.allocas = []
        self.current_ret_type = ret_type
        self.emit_label("entry")
        alloca_index = len(self.code)
        self.scopes = [self.globals]
        self.enter_scope()

        # Allocate local variables for parameters
        for p_type, p_name in node.params:
            llvm_type = self.map_type(p_type)
            ptr = self.new_slot(p_name, llvm_type)
            self.emit_inst(f"store {llvm_type} %{p_name}_arg, {llvm_type}* {ptr}")
            self.declare(p_name, {'ptr': ptr, 'type': llvm_type})

        self.visit(node.body)
        self.exit_scope()

        # Add default return if the body can fall off the end
        self.emit_default_return()
        self.emit("}")
        # Allocating every slot once in the entry block keeps loops from growing the stack
        self.code[alloca_index:alloca_index] = self.allocas

    def emit_default_return(self):
        if self.current_ret_type == 'void':
            self.emit_terminator("ret void")
        else:
            self.emit_terminator(f"ret {self.current_ret_type} {self.default_value(self.current_ret_type)}")

    def visit_Block(self, node):
        self.enter_scope()
        for stmt in node.statements:
            self.visit(stmt)
        self.exit_scope()

    def visit_VarDecl(self, node):
        llvm_type = self.map_type(node.var_type)
        if isinstance(node.init_expr, InitList):
            ptr = self.new_slot(node.name, llvm_type)
            self.initialize_aggregate(ptr, llvm_type, node.init_expr)
            self.declare(node.name, {'ptr': ptr, 'type': llvm_type})
            return
        # Evaluate the initializer before declaring, so `int x = x;` in a nested
        # scope reads the outer x
        init = self.visit(node.init_expr) if node.init_expr else None
        ptr = self.new_slot(node.name, llvm_type)
        self.declare(node.name, {'ptr': ptr, 'type': llvm_type})

        if init:
            val = self.convert(init[0], init[1], llvm_type)
            self.emit_inst(f"store {llvm_type} {val}, {llvm_type}* {ptr}")

    def visit_ArrayDecl(self, node):
        llvm_type = self.map_type(node.var_type)
        array_type = f"[{node.size} x {llvm_type}]"
        ptr = self.new_slot(node.name, array_type)
        if node.init is not None:
            self.initialize_aggregate(ptr, array_type, node.init)
        self.declare(node.name, {'ptr': ptr, 'type': llvm_type, 'array_type': array_type})

    def initialize_aggregate(self, ptr, llvm_type, init):
        # Zero everything first, so members the list leaves out are 0, as in C.
        # This runs each time the declaration does, e.g. on every loop iteration.
        self.emit_inst(f"store {llvm_type} zeroinitializer, {llvm_type}* {ptr}")
        self.init_at(ptr, llvm_type, init)

    def element_type(self, var_info):
        # name[i] reads an array's element type, or what a pointer points to
        return var_info['type'] if 'array_type' in var_info else pointee(var_info['type'])

    def element_ptr(self, var_info, idx_val):
        if 'array_type' in var_info:
            ptr = self.new_reg()
            array_type = var_info['array_type']
            self.emit_inst(f"{ptr} = getelementptr {array_type}, {array_type}* {var_info['ptr']}, i32 0, i32 {idx_val}")
            return ptr
        # Indexing a pointer variable: load the pointer, then step from it.
        # Registers are numbered in emission order, so the load's comes first.
        base = self.new_reg()
        self.emit_inst(f"{base} = load {var_info['type']}, {var_info['type']}* {var_info['ptr']}")
        return self.pointer_offset(base, var_info['type'], idx_val)

    def pointer_offset(self, ptr, ptr_type, offset):
        res = self.new_reg()
        self.emit_inst(f"{res} = getelementptr {pointee(ptr_type)}, {ptr_type} {ptr}, i32 {offset}")
        return res

    def visit_AssignStmt(self, node):
        val, val_type = self.visit(node.expr)
        var_info = self.lookup(node.name)
        return self.store(var_info['ptr'], var_info['type'], val, val_type, node.op)

    def visit_ArrayAssignStmt(self, node):
        idx_val, idx_type = self.visit(node.index_expr)
        idx_val = self.convert(idx_val, idx_type, 'i32')
        val, val_type = self.visit(node.expr)
        var_info = self.lookup(node.name)
        # The element's address is computed once, even for a compound assignment
        ptr = self.element_ptr(var_info, idx_val)
        return self.store(ptr, self.element_type(var_info), val, val_type, node.op)

    def visit_DerefAssignStmt(self, node):
        ptr, ptr_type = self.visit(node.pointer_expr)
        val, val_type = self.visit(node.expr)
        return self.store(ptr, pointee(ptr_type), val, val_type, node.op)

    def store(self, ptr, llvm_type, val, val_type, op=None):
        if op:
            # x op= e is x = x op e, converted back to x's type
            old = self.new_reg()
            self.emit_inst(f"{old} = load {llvm_type}, {llvm_type}* {ptr}")
            val, val_type = self.binary_op(op, old, llvm_type, val, val_type)
        val = self.convert(val, val_type, llvm_type)
        self.emit_inst(f"store {llvm_type} {val}, {llvm_type}* {ptr}")
        return val, llvm_type

    def visit_ReturnStmt(self, node):
        if node.expr:
            val, val_type = self.visit(node.expr)
            val = self.convert(val, val_type, self.current_ret_type)
            self.emit_terminator(f"ret {self.current_ret_type} {val}")
        else:
            self.emit_default_return() # `return;` in a non-void function returns 0

    def visit_IfStmt(self, node):
        cond_val, cond_type = self.visit(node.condition)
        cond_i1 = self.to_i1(cond_val, cond_type)

        then_label = self.new_label()
        else_label = self.new_label()
        end_label = self.new_label()

        if node.else_branch:
            self.emit_terminator(f"br i1 {cond_i1}, label %{then_label}, label %{else_label}")
        else:
            self.emit_terminator(f"br i1 {cond_i1}, label %{then_label}, label %{end_label}")

        self.emit_label(then_label)
        self.visit(node.then_branch)
        self.emit_terminator(f"br label %{end_label}")

        if node.else_branch:
            self.emit_label(else_label)
            self.visit(node.else_branch)
            self.emit_terminator(f"br label %{end_label}")

        self.emit_label(end_label)

    def visit_WhileStmt(self, node):
        cond_label = self.new_label()
        body_label = self.new_label()
        end_label = self.new_label()

        self.emit_terminator(f"br label %{cond_label}")
        self.emit_label(cond_label)

        cond_val, cond_type = self.visit(node.condition)
        cond_i1 = self.to_i1(cond_val, cond_type)
        self.emit_terminator(f"br i1 {cond_i1}, label %{body_label}, label %{end_label}")

        self.emit_label(body_label)
        self.visit_loop_body(node.body, cond_label, end_label)
        self.emit_terminator(f"br label %{cond_label}")

        self.emit_label(end_label)

    def visit_DoWhileStmt(self, node):
        body_label = self.new_label()
        cond_label = self.new_label()
        end_label = self.new_label()

        # The body runs before the condition is first checked
        self.emit_terminator(f"br label %{body_label}")
        self.emit_label(body_label)
        self.visit_loop_body(node.body, cond_label, end_label)
        self.emit_terminator(f"br label %{cond_label}")

        self.emit_label(cond_label)
        cond_val, cond_type = self.visit(node.condition)
        cond_i1 = self.to_i1(cond_val, cond_type)
        self.emit_terminator(f"br i1 {cond_i1}, label %{body_label}, label %{end_label}")

        self.emit_label(end_label)

    def visit_SwitchStmt(self, node):
        value, value_type = self.visit(node.expr)
        value = self.convert(value, value_type, 'i32')
        end_label = self.new_label()
        case_labels = [self.new_label() for _ in node.cases]
        default_label = end_label
        arms = []
        for case, label in zip(node.cases, case_labels):
            if case.value is None:
                default_label = label
            else:
                arms.append(f"i32 {fold_constant(case.value).value}, label %{label}")
        self.emit_terminator(f"switch i32 {value}, label %{default_label} [ {' '.join(arms)} ]")

        # break leaves the switch; continue still belongs to the enclosing loop
        enclosing_continue = self.loops[-1][0] if self.loops else None
        self.loops.append((enclosing_continue, end_label))
        self.enter_scope() # one scope for the whole body, as in C
        for case, label in zip(node.cases, case_labels):
            self.emit_terminator(f"br label %{label}") # fall through from the case above
            self.emit_label(label)
            for stmt in case.statements:
                self.visit(stmt)
        self.emit_terminator(f"br label %{end_label}")
        self.exit_scope()
        self.loops.pop()
        self.emit_label(end_label)

    def visit_loop_body(self, body, continue_label, break_label):
        self.loops.append((continue_label, break_label))
        self.visit(body)
        self.loops.pop()

    def visit_BreakStmt(self, node):
        self.emit_terminator(f"br label %{self.loops[-1][1]}")

    def visit_ContinueStmt(self, node):
        self.emit_terminator(f"br label %{self.loops[-1][0]}")

    def visit_ForStmt(self, node):
        self.enter_scope() # a declaration in the init clause is local to the loop
        self.visit(node.init)

        cond_label = self.new_label()
        body_label = self.new_label()
        next_label = self.new_label()
        end_label = self.new_label()

        self.emit_terminator(f"br label %{cond_label}")
        self.emit_label(cond_label)

        if node.condition is None: # an empty condition loops forever
            self.emit_terminator(f"br label %{body_label}")
        else:
            cond_val, cond_type = self.visit(node.condition)
            cond_i1 = self.to_i1(cond_val, cond_type)
            self.emit_terminator(f"br i1 {cond_i1}, label %{body_label}, label %{end_label}")

        self.emit_label(body_label)
        # continue jumps to the increment, not straight back to the condition
        self.visit_loop_body(node.body, next_label, end_label)
        self.emit_terminator(f"br label %{next_label}")
        self.emit_label(next_label)
        self.visit(node.increment)
        self.emit_terminator(f"br label %{cond_label}")

        self.emit_label(end_label)
        self.exit_scope()

    def visit_logical(self, node):
        # Short-circuit: the right operand is only evaluated when it can change the result
        left_val, left_type = self.visit(node.left)
        left_i1 = self.to_i1(left_val, left_type)
        left_block = self.current_label

        rhs_label = self.new_label()
        end_label = self.new_label()
        if node.op == '&&':
            self.emit_terminator(f"br i1 {left_i1}, label %{rhs_label}, label %{end_label}")
            short_val = 'false'
        else:
            self.emit_terminator(f"br i1 {left_i1}, label %{end_label}, label %{rhs_label}")
            short_val = 'true'

        self.emit_label(rhs_label)
        right_val, right_type = self.visit(node.right)
        right_i1 = self.to_i1(right_val, right_type)
        right_block = self.current_label
        self.emit_terminator(f"br label %{end_label}")

        self.emit_label(end_label)
        phi = self.new_reg()
        self.emit_inst(f"{phi} = phi i1 [ {short_val}, %{left_block} ], [ {right_i1}, %{right_block} ]")
        return self.i1_to_i32(phi), 'i32'

    def visit_BinOp(self, node):
        if node.op in ('&&', '||'):
            return self.visit_logical(node)

        left_val, left_type = self.visit(node.left)
        right_val, right_type = self.visit(node.right)
        return self.binary_op(node.op, left_val, left_type, right_val, right_type)

    def binary_op(self, op, left_val, left_type, right_val, right_type):
        if is_pointer(left_type) or is_pointer(right_type):
            return self.pointer_op(op, left_val, left_type, right_val, right_type)
        op_type = max(left_type, right_type, key=TYPE_RANK.get)
        left_val = self.convert(left_val, left_type, op_type)
        right_val = self.convert(right_val, right_type, op_type)

        if op in ICMP_OPS:
            cmp = self.new_reg()
            if op_type == 'i32':
                self.emit_inst(f"{cmp} = icmp {ICMP_OPS[op]} i32 {left_val}, {right_val}")
            else:
                self.emit_inst(f"{cmp} = fcmp {FCMP_OPS[op]} {op_type} {left_val}, {right_val}")
            return self.i1_to_i32(cmp), 'i32'

        res = self.new_reg()
        arith = INT_ARITH if op_type == 'i32' else FLOAT_ARITH
        self.emit_inst(f"{res} = {arith[op]} {op_type} {left_val}, {right_val}")
        return res, op_type

    def pointer_op(self, op, left_val, left_type, right_val, right_type):
        # Semantic analysis has already allowed only C's pointer operations
        if op in ICMP_OPS:
            ptr_type = left_type if is_pointer(left_type) else right_type
            if not is_pointer(left_type):
                left_val = 'null' # comparing with the null constant 0
            if not is_pointer(right_type):
                right_val = 'null'
            # Pointers compare as unsigned addresses
            pred = {'==': 'eq', '!=': 'ne', '<': 'ult', '<=': 'ule', '>': 'ugt', '>=': 'uge'}[op]
            cmp = self.new_reg()
            self.emit_inst(f"{cmp} = icmp {pred} {ptr_type} {left_val}, {right_val}")
            return self.i1_to_i32(cmp), 'i32'

        if op == '-' and is_pointer(left_type) and is_pointer(right_type):
            # The number of elements between two pointers
            left_int, right_int, bytes_apart, count = (self.new_reg() for _ in range(4))
            self.emit_inst(f"{left_int} = ptrtoint {left_type} {left_val} to i64")
            self.emit_inst(f"{right_int} = ptrtoint {right_type} {right_val} to i64")
            self.emit_inst(f"{bytes_apart} = sub i64 {left_int}, {right_int}")
            self.emit_inst(f"{count} = sdiv exact i64 {bytes_apart}, {size_of(pointee(left_type))}")
            res = self.new_reg()
            self.emit_inst(f"{res} = trunc i64 {count} to i32")
            return res, 'i32'

        # pointer + int, int + pointer, pointer - int: step by whole elements
        if is_pointer(right_type):
            left_val, left_type, right_val, right_type = right_val, right_type, left_val, left_type
        offset = right_val
        if op == '-':
            offset = self.new_reg()
            self.emit_inst(f"{offset} = sub i32 0, {right_val}")
        return self.pointer_offset(left_val, left_type, offset), left_type

    def visit_Deref(self, node):
        ptr, ptr_type = self.visit(node.expr)
        res = self.new_reg()
        self.emit_inst(f"{res} = load {pointee(ptr_type)}, {ptr_type} {ptr}")
        return res, pointee(ptr_type)

    def visit_AddressOf(self, node):
        ptr, llvm_type = self.lvalue_address(node.expr)
        return ptr, llvm_type + '*'

    def lvalue_address(self, node):
        """Where an assignable expression lives: (pointer, type of the value there)."""
        if isinstance(node, Var):
            var_info = self.lookup(node.name)
            return var_info['ptr'], var_info.get('array_type', var_info['type'])
        if isinstance(node, ArrayAccess):
            idx_val, idx_type = self.visit(node.index_expr)
            idx_val = self.convert(idx_val, idx_type, 'i32')
            var_info = self.lookup(node.name)
            return self.element_ptr(var_info, idx_val), self.element_type(var_info)
        if isinstance(node, Deref):
            ptr, ptr_type = self.visit(node.expr)
            return ptr, pointee(ptr_type)
        if isinstance(node, Member):
            if node.arrow:
                base_ptr, base_ptr_type = self.visit(node.base)
                struct_type = pointee(base_ptr_type)
            else:
                base_ptr, struct_type = self.address_or_temporary(node.base)
            index, field_type = self.structs[struct_type[len('%struct.'):]][node.field]
            ptr = self.new_reg()
            self.emit_inst(f"{ptr} = getelementptr {struct_type}, {struct_type}* {base_ptr}, i32 0, i32 {index}")
            return ptr, field_type
        if isinstance(node, Index):
            base_ptr, base_type = self.visit(node.base) # arrays have already decayed to a pointer
            idx_val, idx_type = self.visit(node.index_expr)
            idx_val = self.convert(idx_val, idx_type, 'i32')
            return self.pointer_offset(base_ptr, base_type, idx_val), pointee(base_type)
        raise TypeError(f"Codegen: {type(node).__name__} is not assignable")

    def address_or_temporary(self, node):
        # A struct value that isn't stored anywhere yet, such as make().x, gets a stack slot
        if isinstance(node, (Var, ArrayAccess, Deref, Member, Index)):
            return self.lvalue_address(node)
        val, llvm_type = self.visit(node)
        slot = self.new_slot('tmp', llvm_type)
        self.emit_inst(f"store {llvm_type} {val}, {llvm_type}* {slot}")
        return slot, llvm_type

    def load_place(self, ptr, llvm_type):
        if llvm_type.startswith('['):
            # An array decays to a pointer to its first element
            first = self.new_reg()
            element = llvm_type[llvm_type.index(' x ') + 3:-1]
            self.emit_inst(f"{first} = getelementptr {llvm_type}, {llvm_type}* {ptr}, i32 0, i32 0")
            return first, element + '*'
        res = self.new_reg()
        self.emit_inst(f"{res} = load {llvm_type}, {llvm_type}* {ptr}")
        return res, llvm_type

    def visit_Member(self, node):
        return self.load_place(*self.lvalue_address(node))

    def visit_Index(self, node):
        return self.load_place(*self.lvalue_address(node))

    def visit_LValueAssignStmt(self, node):
        ptr, llvm_type = self.lvalue_address(node.target)
        val, val_type = self.visit(node.expr)
        return self.store(ptr, llvm_type, val, val_type, node.op)

    def visit_LValueIncDec(self, node):
        ptr, llvm_type = self.lvalue_address(node.target)
        return self.incdec_at(ptr, llvm_type, node.op, node.prefix)

    def visit_UnaryOp(self, node):
        val, val_type = self.visit(node.expr)
        if node.op == '-':
            res = self.new_reg()
            if val_type == 'i32':
                self.emit_inst(f"{res} = sub i32 0, {val}")
            else:
                self.emit_inst(f"{res} = fneg {val_type} {val}")
            return res, val_type
        elif node.op == '!':
            nonzero = self.to_i1(val, val_type)
            res = self.new_reg()
            self.emit_inst(f"{res} = xor i1 {nonzero}, true")
            return self.i1_to_i32(res), 'i32'
        raise NotImplementedError(f"Codegen: unsupported unary operator '{node.op}'")

    def visit_IncDec(self, node):
        var_info = self.lookup(node.name)
        return self.incdec_at(var_info['ptr'], var_info['type'], node.op, node.prefix)

    def incdec_at(self, ptr, llvm_type, op, prefix):
        old = self.new_reg()
        self.emit_inst(f"{old} = load {llvm_type}, {llvm_type}* {ptr}")
        if is_pointer(llvm_type):
            new = self.pointer_offset(old, llvm_type, 1 if op == '++' else -1)
        else:
            new = self.new_reg()
            if llvm_type == 'i32':
                arith = 'add' if op == '++' else 'sub'
                self.emit_inst(f"{new} = {arith} i32 {old}, 1")
            else:
                arith = 'fadd' if op == '++' else 'fsub'
                self.emit_inst(f"{new} = {arith} {llvm_type} {old}, 1.0")
        self.emit_inst(f"store {llvm_type} {new}, {llvm_type}* {ptr}")
        return (new if prefix else old), llvm_type

    def visit_Var(self, node):
        var_info = self.lookup(node.name)
        if 'array_type' in var_info:
            # The array decays to a pointer to its first element
            return self.element_ptr(var_info, 0), var_info['type'] + '*'
        res = self.new_reg()
        self.emit_inst(f"{res} = load {var_info['type']}, {var_info['type']}* {var_info['ptr']}")
        return res, var_info['type']

    def visit_ArrayAccess(self, node):
        idx_val, idx_type = self.visit(node.index_expr)
        idx_val = self.convert(idx_val, idx_type, 'i32')
        var_info = self.lookup(node.name)
        ptr = self.element_ptr(var_info, idx_val)
        element = self.element_type(var_info)
        res = self.new_reg()
        self.emit_inst(f"{res} = load {element}, {element}* {ptr}")
        return res, element

    def visit_Number(self, node):
        if node.val_type == 'float':
            # C floating literals are doubles
            return self.float_constant(float(node.value), 'double'), 'double'
        return str(node.value), 'i32'

    def visit_FuncCall(self, node):
        sig = self.functions.get(node.name, {'ret': 'i32', 'params': None})
        arg_strs = []
        for i, arg in enumerate(node.args):
            val, v_type = self.visit(arg)
            if sig['params'] is not None:
                val = self.convert(val, v_type, sig['params'][i])
                v_type = sig['params'][i]
            arg_strs.append(f"{v_type} {val}")
        arg_str = ", ".join(arg_strs)

        if sig['ret'] == 'void':
            self.emit_inst(f"call void @{node.name}({arg_str})")
            return None, 'void'
        res = self.new_reg()
        self.emit_inst(f"{res} = call {sig['ret']} @{node.name}({arg_str})")
        return res, sig['ret']
