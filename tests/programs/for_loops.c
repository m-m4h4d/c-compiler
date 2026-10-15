int main() {
    int sum = 0;
    for (int i = 0; i < 5; i++) {
        sum = sum + i;
    }
    int i = 100; // the loop variable above is out of scope here
    for (int j = 10; j > 0; --j) {
        sum = sum + 1;
    }
    int k = 0;
    for (;;) {
        k++;
        if (k == 7) {
            return sum + i + k;
        }
    }
    return 0;
}
