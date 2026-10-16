struct A {
    int x;
};

struct B {
    int x;
};

int main() {
    struct A a;
    struct B b = a; // error
    return 0;
}
