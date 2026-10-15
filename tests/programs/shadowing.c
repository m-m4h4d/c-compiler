int main() {
    int x = 1;
    int y = 0;
    {
        int x = 2;
        y = y + x;
        {
            int x = 3;
            y = y + x * 10;
        }
        y = y + x * 100;
    }
    return y + x * 1000 - 1000;
}
