/* 
 * Open and exclusive-lock file - make it rw user and r by others.
 * 
 * Return
 *  -  0
 *     Lock acquired
 *  -  non-zero
 *     Lock not acquired
 *
 * Otherwise, the function returns nonzero errno:
 *     EINVAL: Invalid lock file path
 *     EMFILE: Too many open files
 *     EALREADY: Already locked
 * or one of the open(2)/creat(2) errors.
*/
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <errno.h>
#include <unistd.h>
#include <stdbool.h>

static int set_lock_cmd(bool ofd)
{
    int set_lock = 0;

    if (ofd)
        set_lock =  F_OFD_SETLK;
    else
        set_lock =  F_SETLK;
    return (set_lock);
}
static int get_lock_cmd(bool ofd)
{
    int get_lock = 0;

    if (ofd)
        get_lock =  F_OFD_SETLK;
    else
        get_lock =  F_SETLK;
    return (get_lock);
}

static int acquire_lock(const char *const lockfile, int *const fdptr, bool ofd)
{
    struct flock lock;
    int fd, set_lock;

    if (fdptr)
        *fdptr = -1;

    if (lockfile == NULL || *lockfile == '\0')
        return errno = EINVAL;

    set_lock = set_lock_cmd(ofd) ;

    fd = open(lockfile, O_RDWR | O_CREAT, 0600);

    if (fd < 0) {
        if (errno == EALREADY)
            errno = EIO;
        return errno;
    }

    // Write lock entire file
    lock.l_type = F_WRLCK;
    lock.l_whence = SEEK_SET;
    lock.l_start = 0;
    lock.l_len = 0;

    if (fcntl(fd, set_lock, &lock) == -1) {
        // Failed
        close(fd);
        return errno = EALREADY;
    }

    // All good - lock acquired 
    if (fdptr)
        *fdptr = fd;

    return 0;
}

int main(int argc, char *argv[]) {
    int result;
    char *lfile = "/tmp/test-c_locky" ;
    bool ofd = false;
    int  fd = -1;

    if (argc > 1) {
        printf("OFD turned on") ;
        ofd = true ;
    }

    result = acquire_lock(lfile, &fd, ofd);
    if (result == 0) {
        // Lock Acquired
        printf("Result = 0 | lock acquired | waiting\n") ;
        sleep(10) ;
    } else {
        if (result == EALREADY) {
            // locked by others
            printf("Result != 0 | lock not acquired - held by others\n") ;
        } else {
            // Error trying to create lock
            printf("Error getting lock\n") ;
            printf("%s", strerror(errno)) ;
        }
    }
    return 0;
}

