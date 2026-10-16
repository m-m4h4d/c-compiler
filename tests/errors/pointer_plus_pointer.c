int main() {
    int a[2];
    int *p = a;
    int *q = p + p; // error
    return 0;
}
