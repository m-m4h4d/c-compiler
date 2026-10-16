struct Point {
    int x;
};

int main() {
    struct Point p;
    struct Point *pp = &p;
    return pp.x; // error
}
