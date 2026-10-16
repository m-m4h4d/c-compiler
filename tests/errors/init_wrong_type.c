struct Point {
    int x;
};

int main() {
    int *p = 0;
    struct Point q = {p}; // error
    return 0;
}
