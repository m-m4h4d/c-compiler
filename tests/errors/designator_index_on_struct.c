struct Point {
    int x;
};

int main() {
    struct Point p = {[0] = 1}; // error
    return 0;
}
