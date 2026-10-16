int read(int *p) {
    return *p;
}

int main() {
    double d = 1.0;
    return read(&d); // error
}
