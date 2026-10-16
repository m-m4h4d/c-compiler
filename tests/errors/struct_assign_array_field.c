struct Stats {
    int counts[3];
};

int main() {
    struct Stats a;
    struct Stats b;
    a.counts = b.counts; // error
    return 0;
}
