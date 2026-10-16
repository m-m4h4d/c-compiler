// Declares an array on every iteration. If each declaration allocated new
// stack space, 10 million iterations would overflow the stack.
int main() {
    int total = 0;
    for (int i = 0; i < 10000000; i++) {
        int scratch[4];
        scratch[0] = i % 3;
        total = total + scratch[0];
    }
    return total % 256;
}
