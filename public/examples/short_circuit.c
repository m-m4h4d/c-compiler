// && and || only evaluate their right side when it can change the result,
// so neither division below runs.

int main() {
    int zero = 0;
    int ten = 10;
    int r = 0;
    if (zero != 0 && ten / zero > 1) {
        r = 100;
    }
    if (zero == 0 || ten / zero > 1) {
        r = r + 7;
    }
    return r;
}
