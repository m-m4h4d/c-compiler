int main() {
    int a = 3;
    int b = 7;
    int r = 0;
    if (a < b) { r = r + 1; }
    if (a <= 3) { r = r + 2; }
    if (b > a) { r = r + 4; }
    if (b >= 8) { r = r + 8; }
    if (a == 3) { r = r + 16; }
    if (a != b) { r = r + 32; }
    return r;
}
