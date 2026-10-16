struct Point {
    int x;
};

int main() {
    struct Point p;
    return p->x; // error
}
