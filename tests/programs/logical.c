int bump(int v) {
    return v;
}

int main() {
    int zero = 0;
    int one = 1;
    int arr[2];
    int r = 0;
    arr[0] = 0;
    arr[1] = 0;
    if (zero && bump(1)) { r = r + 1; }
    if (one || bump(0)) { r = r + 2; }
    if (one && one) { r = r + 4; }
    if (zero || zero) { r = r + 8; }
    if (!zero) { r = r + 16; }
    if (!(one && zero) || zero) { r = r + 32; }
    return r + (one && 5) + (zero || 7);
}
