// Line comment at the top of the file
int main() {
    int x = 1; // trailing comment
    /* block comment */ x = x + 1;
    /*
     * multi-line block comment
     * x = 100;
     */
    int y = 10 /* inline */ / 2;
    // y = 0;
    return x + y;
}
