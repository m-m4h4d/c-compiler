int main() {
    int x = 0;
    do {
        x++;
    } while (x < 3)
    return x; // error: reported at the token after the missing semicolon
}
