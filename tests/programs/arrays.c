int main() {
    int a[10];
    int i;
    for (i = 0; i < 10; i = i + 1) {
        a[i] = i * i;
    }
    int sum = 0;
    for (i = 0; i < 10; i = i + 1) {
        sum = sum + a[i];
    }
    return sum % 256;
}
