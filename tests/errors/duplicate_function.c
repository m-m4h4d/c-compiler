int helper() {
    return 1;
}

int helper() { // error
    return 2;
}

int main() {
    return helper();
}
