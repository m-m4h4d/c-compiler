int main() {
    int x = 1;
    int y = 2;
    switch (x) {
        case y: // error
            return 1;
    }
    return 0;
}
