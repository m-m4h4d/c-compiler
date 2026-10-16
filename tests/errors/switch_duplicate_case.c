int main() {
    int x = 1;
    switch (x) {
        case 1:
            return 1;
        case 1: // error
            return 2;
    }
    return 0;
}
