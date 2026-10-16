// Searching an array: break as soon as the value is found
int find(int target) {
    int values[6];
    for (int i = 0; i < 6; i++) {
        values[i] = i * i;
    }
    int found = -1;
    for (int i = 0; i < 6; i++) {
        if (values[i] == target) {
            found = i;
            break;
        }
    }
    return found;
}

int main() {
    return find(16) * 10 + find(9) + (find(7) == -1) * 100;
}
