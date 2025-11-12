#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include <complex.h>

void oqs_quartic_solver(double coeff[5], complex double roots[4]);

double uniform_random(double min, double max) {
    return min + (max - min) * ((double)rand() / RAND_MAX);
}

void time_single_solves(int n_runs, int warmup, double *mean, double *std) {
    double *coeffs_storage = malloc(n_runs * 5 * sizeof(double));
    double *times = malloc(n_runs * sizeof(double));
    complex double roots[4];
    double coeff[5];
    struct timespec start, end;

    srand(42);

    for (int i = 0; i < n_runs; i++) {
        for (int j = 0; j < 5; j++) {
            coeffs_storage[i * 5 + j] = uniform_random(-10.0, 10.0);
        }
    }

    for (int i = 0; i < warmup; i++) {
        for (int j = 0; j < 5; j++) {
            coeff[j] = coeffs_storage[(i % n_runs) * 5 + j];
        }
        oqs_quartic_solver(coeff, roots);
    }

    for (int i = 0; i < n_runs; i++) {
        coeff[0] = coeffs_storage[i * 5 + 4];
        coeff[1] = coeffs_storage[i * 5 + 3];
        coeff[2] = coeffs_storage[i * 5 + 2];
        coeff[3] = coeffs_storage[i * 5 + 1];
        coeff[4] = coeffs_storage[i * 5 + 0];

        clock_gettime(CLOCK_MONOTONIC, &start);
        oqs_quartic_solver(coeff, roots);
        clock_gettime(CLOCK_MONOTONIC, &end);

        times[i] = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    }

    *mean = 0.0;
    for (int i = 0; i < n_runs; i++) {
        *mean += times[i];
    }
    *mean /= n_runs;

    *std = 0.0;
    for (int i = 0; i < n_runs; i++) {
        double diff = times[i] - *mean;
        *std += diff * diff;
    }
    *std = sqrt(*std / n_runs);

    free(coeffs_storage);
    free(times);
}

int main() {
    int n_polys = 10000;
    int warmup = 100;
    double mean, std;

    time_single_solves(n_polys, warmup, &mean, &std);

    printf("C (direct):  %8.4f μs ± %6.4f μs\n", mean * 1e6, std * 1e6);

    return 0;
}
