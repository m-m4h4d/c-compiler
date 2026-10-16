int main() {
    int x = 0;
    while (x < 3) {
        x++;
        break
    } // error: reported at the token after the missing semicolon
    return x;
}
