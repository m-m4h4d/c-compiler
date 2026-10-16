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

# Pointer types are written like C: 'int*', 'double**'
def is_pointer(t):
    return t.endswith('*')

def is_arithmetic(t):
    return t in TYPE_RANK

def pointee(t):
    return t[:-1]

# Struct types are 'struct Name'; only struct fields can have array types such as 'int[4]'
def is_struct(t):
    return t.startswith('struct ') and not is_pointer(t) and not is_array_type(t)

def is_array_type(t):
    return t.endswith(']')

def array_element(t):
    return t[:t.rindex('[')]

def decay(t):
    # An array used as a value becomes a pointer to its first element
    return array_element(t) + '*' if is_array_type(t) else t

class SemanticAnalyzer:
    """Checks scoping and declarations, and the type of every expression.

    Expression visitors return the expression's type: 'int', 'float',
    'double', a pointer such as 'int*', or 'void' (a call to a void function).
    """

    def is_null_constant(self, node):
        # The integer constant 0 converts to any pointer type
        folded = fold_constant(node) if node is not None else None
        return folded is not None and folded.val_type == 'int' and folded.value == 0

    def check_assignable(self, target, value, value_node, what, line):
        """Raise unless a value of type `value` can be stored where `target` is expected."""
        if is_arithmetic(target) and is_arithmetic(value):
            return # implicit conversion, as in C
        if is_struct(target) and value == target:
            return # whole-struct copy
        if is_pointer(target) and (value == target or (value == 'int' and self.is_null_constant(value_node))):
            return
        if is_pointer(target) and is_pointer(value):
            raise SemanticError(f"{what}: incompatible pointer types, {value} and {target}", line)
        raise SemanticError(f"{what}: cannot convert {value} to {target}", line)

    def require_scalar(self, actual, what, line):
        if not (is_arithmetic(actual) or is_pointer(actual)):
            raise SemanticError(f"{what} must be a number or a pointer, not {actual}", line)

    def check_type(self, t, what, line):
        """Raise if a declared type names a struct that hasn't been defined."""
        base = array_element(t) if is_array_type(t) else t
        by_value = not is_pointer(base)
        base = base.rstrip('*')
        if not base.startswith('struct '):
            return
        name = base[len('struct '):]
        if name not in self.structs:
            raise SemanticError(f"{what}: unknown struct '{name}'", line)
        if by_value and self.structs[name] is None:
            # Only reachable from a field of the struct being defined
            raise SemanticError(f"{what}: struct '{name}' cannot contain itself; use a pointer, struct {name} *", line)

    def struct_fields(self, struct_type):
        return self.structs[struct_type[len('struct '):]]['fields']

    def __init__(self, ast):
        self.ast = ast
        self.symtab = SymbolTable()
        self.structs = {} # name -> {'fields': {field: type}}, or None while being defined
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
            self.visit(decl)
            init = decl.init_expr if isinstance(decl, VarDecl) else getattr(decl, 'init', None)
            if init is not None and not self.is_constant_init(init):
                raise SemanticError(f"Initializer of global variable '{decl.name}' must be a constant expression", decl.line)

    def is_constant_init(self, init):
        if isinstance(init, InitList):
            return all(self.is_constant_init(item) for item in init.items)
        return self.is_constant(init)

    # ---- Initializers
    # normalize() checks an initializer against its type and returns it fully
    # braced: one InitList per struct or array, holding one entry per member
    # in order (trailing members that were left out are zero). Later phases
    # only ever see this form, so brace elision is handled here alone.

    def is_aggregate_type(self, t):
        return is_struct(t) or is_array_type(t)

    def members_of(self, t):
        if is_struct(t):
            return [(field_type, f"field '{name}'") for name, field_type in self.struct_fields(t).items()]
        count = int(t[t.rindex('[') + 1:-1])
        return [(array_element(t), f"element {i}") for i in range(count)]

    def normalize(self, t, init, what, line):
        if isinstance(init, InitList):
            if self.is_aggregate_type(t):
                position = [0]
                result = self.fill_aggregate(t, init.items, position, what, init.line)
                if position[0] < len(init.items):
                    extra = init.items[position[0]]
                    raise SemanticError(f"{what}: too many values for {t}", extra.line or init.line)
                return result
            # A scalar may be wrapped in braces, as in int x = {5};
            if len(init.items) != 1 or isinstance(init.items[0], InitList):
                raise SemanticError(f"{what}: {t} takes a single value, not a list of {len(init.items)}", init.line)
            return self.normalize(t, init.items[0], what, line)
        if is_array_type(t):
            raise SemanticError(f"{what}: an array is initialized with a braced list such as {{1, 2}}", line)
        value = self.visit(init)
        self.check_assignable(t, value, init, what, line)
        return init

    def fill_aggregate(self, t, items, position, what, line):
        # `T[]` is an array whose size the initializer decides
        unbounded = t.endswith('[]')
        members = None if unbounded else self.members_of(t)
        result = []
        while position[0] < len(items):
            index = len(result)
            if unbounded:
                member_type, description = t[:-2], f"element {index}"
            elif index < len(members):
                member_type, description = members[index]
            else:
                break # leftover values belong to an enclosing list, or are too many
            item = items[position[0]]
            member_what = f"{what}, {description}"
            if isinstance(item, InitList):
                position[0] += 1
                result.append(self.normalize(member_type, item, member_what, item.line))
            elif self.is_aggregate_type(member_type) and not (is_struct(member_type) and self.visit(item) == member_type):
                # Brace elision: an aggregate member without its own braces takes
                # as many of the following values as it needs
                result.append(self.fill_aggregate(member_type, items, position, member_what, item.line or line))
            else:
                position[0] += 1
                result.append(self.normalize(member_type, item, member_what, item.line or line))
        normalized = InitList(result)
        normalized.line = line
        return normalized

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

    def visit_StructDecl(self, node):
        if node.name in self.structs:
            raise SemanticError(f"struct '{node.name}' is already defined", node.line)
        if not node.fields:
            raise SemanticError(f"struct '{node.name}' needs at least one field", node.line)
        self.structs[node.name] = None # visible, so fields can point to it
        fields = {}
        field_lines = getattr(node, 'field_lines', [node.line] * len(node.fields))
        for (field_type, field_name), line in zip(node.fields, field_lines):
            if field_name in fields:
                raise SemanticError(f"Field '{field_name}' appears twice in struct '{node.name}'", line)
            if is_array_type(field_type):
                size = field_type[field_type.rindex('[') + 1:-1]
                if not size.isdigit() or int(size) <= 0:
                    raise SemanticError(f"Size of field '{field_name}' must be a positive integer, not {size}", line)
            self.check_type(field_type, f"Field '{field_name}'", line)
            fields[field_name] = field_type
        self.structs[node.name] = {'fields': fields}

    def visit_FunctionDecl(self, node):
        self.check_type(node.return_type, f"Return type of '{node.name}'", node.line)
        self.symtab.declare_function(node.name, node.return_type, node.params, node.line)
        self.current_function = node
        self.symtab.enter_scope()
        param_lines = getattr(node, 'param_lines', [node.line] * len(node.params))
        for (p_type, p_name), line in zip(node.params, param_lines):
            self.check_type(p_type, f"Parameter '{p_name}'", line)
            self.symtab.declare(p_name, p_type, line=line)
        self.visit(node.body)
        self.symtab.exit_scope()
        self.current_function = None

    def visit_VarDecl(self, node):
        self.check_type(node.var_type, f"Variable '{node.name}'", node.line)
        self.symtab.declare(node.name, node.var_type, line=node.line)
        if node.init_expr is not None:
            node.init_expr = self.normalize(node.var_type, node.init_expr, f"Initializer of '{node.name}'", node.line)

    def visit_ArrayDecl(self, node):
        if node.size is not None and (not isinstance(node.size, int) or node.size <= 0):
            raise SemanticError(f"Size of array '{node.name}' must be a positive integer, not {node.size}", node.line)
        self.check_type(node.var_type, f"Array '{node.name}'", node.line)
        if node.init is not None:
            array_type = f"{node.var_type}[{'' if node.size is None else node.size}]"
            node.init = self.normalize(array_type, node.init, f"Initializer of '{node.name}'", node.line)
            if node.size is None:
                node.size = len(node.init.items)
                if node.size == 0:
                    raise SemanticError(f"Array '{node.name}' needs at least one element", node.line)
        self.symtab.declare(node.name, node.var_type, is_array=True, size=node.size, line=node.line)

    def visit_Block(self, node):
        self.symtab.enter_scope()
        for stmt in node.statements:
            self.visit_statement(stmt)
        self.symtab.exit_scope()

    def visit_condition(self, node, line):
        if node is not None:
            self.require_scalar(self.visit(node), "A condition", line)

    def visit_IfStmt(self, node):
        self.visit_condition(node.condition, node.line)
        self.visit_statement(node.then_branch)
        if node.else_branch:
            self.visit_statement(node.else_branch)

    def visit_WhileStmt(self, node):
        self.visit_condition(node.condition, node.line)
        self.visit_loop_body(node.body)

    def visit_DoWhileStmt(self, node):
        # The body's declarations are out of scope again by the time the condition runs
        self.visit_loop_body(node.body)
        self.visit_condition(node.condition, node.line)

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
        self.visit_condition(node.condition, node.line)
        self.visit_statement(node.increment)
        self.visit_loop_body(node.body)
        self.symtab.exit_scope()

    def visit_ReturnStmt(self, node):
        if node.expr:
            if self.current_function.return_type == 'void':
                raise SemanticError(f"Void function '{self.current_function.name}' cannot return a value", node.line)
            value = self.visit(node.expr)
            self.check_assignable(self.current_function.return_type, value, node.expr,
                                  f"Return value of '{self.current_function.name}'", node.line)

    def visit_AssignStmt(self, node):
        var_info = self.symtab.lookup(node.name)
        if not var_info:
            raise SemanticError(f"Undeclared variable '{node.name}'", node.line)
        if var_info.get('type') == 'function':
            raise SemanticError(f"'{node.name}' is a function, not a variable", node.line)
        if var_info.get('is_array'):
            raise SemanticError(f"Cannot assign to array '{node.name}' directly", node.line)
        return self.check_assignment(var_info['type'], node, f"Assignment to '{node.name}'")

    def visit_ArrayAssignStmt(self, node):
        element = self.indexed_element_type(node)
        return self.check_assignment(element, node, f"Assignment to an element of '{node.name}'")

    def visit_DerefAssignStmt(self, node):
        pointer = self.visit(node.pointer_expr)
        if not is_pointer(pointer):
            raise SemanticError(f"Cannot dereference {pointer}: only pointers can be used with *", node.line)
        return self.check_assignment(pointee(pointer), node, "Assignment through a pointer")

    def visit_LValueAssignStmt(self, node):
        target = self.lvalue_type(node.target)
        return self.check_assignment(target, node, "Assignment")

    def lvalue_type(self, target):
        # The type stored at an assignable place; whole arrays aren't assignable
        if isinstance(target, Member):
            field_type = self.member_field_type(target)
            if is_array_type(field_type):
                raise SemanticError(f"Cannot assign to array field '{target.field}' directly", target.line)
            return field_type
        return self.visit(target)

    def visit_LValueIncDec(self, node):
        target = self.lvalue_type(node.target)
        if not (is_arithmetic(target) or is_pointer(target)):
            raise SemanticError(f"Operand of '{node.op}' must be a number or a pointer, not {target}", node.line)
        return target

    def member_field_type(self, node):
        """The declared type of base.field or base->field, before arrays decay."""
        base = self.visit(node.base)
        if node.arrow:
            if not (is_pointer(base) and is_struct(pointee(base))):
                hint = "; use '.' on a struct" if is_struct(base) else ""
                raise SemanticError(f"'->' needs a pointer to a struct, not {base}{hint}", node.line)
            struct_type = pointee(base)
        else:
            if not is_struct(base):
                hint = "; use '->' on a pointer to a struct" if is_pointer(base) and is_struct(pointee(base)) else ""
                raise SemanticError(f"'.' needs a struct, not {base}{hint}", node.line)
            struct_type = base
        fields = self.struct_fields(struct_type)
        if node.field not in fields:
            raise SemanticError(f"{struct_type} has no field '{node.field}'", node.line)
        return fields[node.field]

    def visit_Member(self, node):
        return decay(self.member_field_type(node))

    def visit_Index(self, node):
        base = self.visit(node.base)
        if not is_pointer(base):
            raise SemanticError(f"Only arrays and pointers can be indexed, not {base}", node.line)
        self.require_int(self.visit(node.index_expr), "Array index", node.line)
        return pointee(base)

    def check_assignment(self, target, node, what):
        value = self.visit(node.expr)
        if node.op is None:
            self.check_assignable(target, value, node.expr, what, node.line)
        elif is_pointer(target):
            # p += n and p -= n step the pointer; nothing else applies to pointers
            if node.op not in ('+', '-') or value != 'int':
                raise SemanticError(f"{what}: '{node.op}=' on a pointer needs '+=' or '-=' with an int", node.line)
        else:
            if not is_arithmetic(target) or is_pointer(value) or not is_arithmetic(value):
                raise SemanticError(f"{what}: cannot use {value} with '{node.op}=' on {target}", node.line)
            if node.op == '%':
                self.require_int(target, "Target of '%='", node.line)
                self.require_int(value, "Right side of '%='", node.line)
        return target

    def require_int(self, actual, what, line):
        if actual != 'int':
            raise SemanticError(f"{what} must be an integer, not {actual}", line)

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op
        invalid = SemanticError(f"Invalid operands to '{op}': {left} and {right}", node.line)

        if op in ('&&', '||'):
            self.require_scalar(left, f"Left operand of '{op}'", node.line)
            self.require_scalar(right, f"Right operand of '{op}'", node.line)
            return 'int'

        if is_pointer(left) or is_pointer(right):
            if op == '+' and is_pointer(left) and right == 'int':
                return left
            if op == '+' and left == 'int' and is_pointer(right):
                return right
            if op == '-' and is_pointer(left) and right == 'int':
                return left
            if op == '-' and left == right:
                return 'int' # elements between two pointers
            if op in ('==', '!=', '<', '<=', '>', '>='):
                if left == right:
                    return 'int'
                # A pointer compares with the null constant 0
                if op in ('==', '!=') and (self.is_null_constant(node.left) or self.is_null_constant(node.right)):
                    return 'int'
            raise invalid

        if not (is_arithmetic(left) and is_arithmetic(right)):
            raise invalid
        if op == '%':
            if left != 'int' or right != 'int':
                raise SemanticError(f"Operands of '%' must be integers, not {left} and {right}", node.line)
            return 'int'
        if op in ('+', '-', '*', '/'):
            return wider(left, right)
        return 'int' # comparisons yield 0 or 1

    def visit_UnaryOp(self, node):
        operand = self.visit(node.expr)
        if node.op == '-':
            if not is_arithmetic(operand):
                raise SemanticError(f"Cannot negate {operand}", node.line)
            return operand
        self.require_scalar(operand, "Operand of '!'", node.line)
        return 'int'

    def visit_Deref(self, node):
        operand = self.visit(node.expr)
        if not is_pointer(operand):
            raise SemanticError(f"Cannot dereference {operand}: only pointers can be used with *", node.line)
        return pointee(operand)

    def visit_AddressOf(self, node):
        target = node.expr
        if isinstance(target, Var):
            var_info = self.symtab.lookup(target.name)
            if var_info and var_info.get('is_array'):
                raise SemanticError(f"Taking the address of array '{target.name}' isn't supported; "
                                    f"'{target.name}' on its own already points to its first element", node.line)
        elif isinstance(target, Member):
            field_type = self.member_field_type(target)
            if is_array_type(field_type):
                raise SemanticError(f"Taking the address of array field '{target.field}' isn't supported; "
                                    f"'{target.field}' on its own already points to its first element", node.line)
            return field_type + '*'
        elif not isinstance(target, (ArrayAccess, Deref, Index)):
            raise SemanticError("Can only take the address of a variable, an array element, a struct member "
                                "or *pointer", node.line)
        return self.visit(target) + '*'

    def visit_IncDec(self, node):
        var_info = self.symtab.lookup(node.name)
        if not var_info:
            raise SemanticError(f"Undeclared variable '{node.name}'", node.line)
        if var_info.get('type') == 'function' or var_info.get('is_array') or is_struct(var_info['type']):
            raise SemanticError(f"Operand of '{node.op}' must be a scalar variable, got '{node.name}'", node.line)
        return var_info['type']

    def visit_Var(self, node):
        var_info = self.symtab.lookup(node.name)
        if not var_info:
            raise SemanticError(f"Undeclared variable '{node.name}'", node.line)
        if var_info.get('type') == 'function':
            raise SemanticError(f"'{node.name}' is a function, not a variable", node.line)
        if var_info.get('is_array'):
            return var_info['type'] + '*' # as in C, the array decays to a pointer to its first element
        return var_info['type']

    def visit_ArrayAccess(self, node):
        return self.indexed_element_type(node)

    def indexed_element_type(self, node):
        # name[index] works on arrays and on pointers
        var_info = self.symtab.lookup(node.name)
        if not var_info:
            raise SemanticError(f"Undeclared array '{node.name}'", node.line)
        if var_info.get('type') == 'function' or not (var_info.get('is_array') or is_pointer(var_info['type'])):
            raise SemanticError(f"'{node.name}' is not an array or pointer", node.line)
        self.require_int(self.visit(node.index_expr), "Array index", node.line)
        return var_info['type'] if var_info.get('is_array') else pointee(var_info['type'])

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
        for i, (arg, (param_type, param_name)) in enumerate(zip(node.args, func_info['params']), 1):
            value = self.visit(arg)
            self.check_assignable(param_type, value, arg, f"Argument {i} of '{node.name}' ('{param_name}')", node.line)
        return func_info['return_type']
