func arithmetic:
begin_func
a = 10
b = 8
t1 = a * b
c = t1
return c
end_func

func loops:
begin_func
sum = 0
i = 0
L1:
t2 = i < 10
if_false t2 goto L2
t3 = sum + i
sum = t3
t4 = i + 1
i = t4
goto L1
L2:
j = 0
L3:
t5 = j < 5
if_false t5 goto L5
t6 = sum + j
sum = t6
L4:
t7 = j + 1
j = t7
goto L3
L5:
return sum
end_func

func add:
begin_func
t8 = x + y
return t8
end_func

func main:
begin_func
alloc_array arr, 5
arr[0] = 10
arr[1] = 20
t9 = arr[0]
t10 = arr[1]
param t9
param t10
t11 = call add, 2
result = t11
t12 = call arithmetic, 0
t13 = result + t12
t14 = call loops, 0
t15 = t13 + t14
return t15
end_func
