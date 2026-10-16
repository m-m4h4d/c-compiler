struct Point {
    int x;
};

int main() {
    struct Point p;
    if (p) { // error
        return 1;
    }
    return 0;
}
