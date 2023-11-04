//
// Print size of flock struct
// compile:
//  gcc -Wall flock_sizes.c -o -lc; ./a.out
//
#define _GNU_SOURCE
#include <stdio.h>
#include <fcntl.h>

int main() {
    struct flock flk;

    printf("struct flock element sizes:\n");
    printf(" l_type     : %lu bytes\n", sizeof(flk.l_type));
    printf(" l_whence   : %lu bytes\n", sizeof(flk.l_whence));
    printf(" l_start    : %lu bytes\n", sizeof(flk.l_start));
    printf(" l_len      : %lu bytes\n", sizeof(flk.l_len));
    printf(" l_pid      : %lu bytes\n", sizeof(flk.l_pid));

    printf("\nValues of fcntl command flags:\n");
    printf(" F_GETLK     = %d\n", F_GETLK);
    printf(" F_SETLK     = %d\n", F_SETLK);
    printf(" F_OFD_GETLK = %d\n", F_OFD_GETLK);
    printf(" F_OFD_SETLK = %d\n", F_OFD_SETLK);

    return(0);
}
