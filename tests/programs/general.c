int arithmetic() {
    int a = 10;
    int b = 5 + 3; 
    int c = a * b;
    return c;
}

int loops() {
    int sum = 0;
    int i = 0;
    while (i < 10) {
        sum = sum + i;
        i = i + 1;
    }
    
    int j;
    for (j = 0; j < 5; j = j + 1) {
        sum = sum + j;
    }
    
    if (0) {
        sum = 0;
    }
    
    return sum;
}

int add(int x, int y) {
    return x + y;
}

int main() {
    int arr[5];
    arr[0] = 10;
    arr[1] = 20;
    
    int result = add(arr[0], arr[1]);
    return result + arithmetic() + loops();
}
