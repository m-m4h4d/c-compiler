// Counts the primes below 50. The inner loop breaks as soon as it finds a
// divisor, and the outer loop uses continue to skip even numbers.
// The program exits with status 15.

int main() {
    int count = 1; // 2 is the only even prime
    for (int n = 3; n < 50; n++) {
        if (n % 2 == 0) {
            continue;
        }
        int is_prime = 1;
        for (int d = 3; d * d <= n; d += 2) {
            if (n % d == 0) {
                is_prime = 0;
                break;
            }
        }
        count += is_prime;
    }
    return count;
}
