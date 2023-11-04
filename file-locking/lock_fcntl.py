#!/usr/bin/python
"""
Example fcntl.fcntl locks

  NB python implementation requires dealing directly with C structures which
  vary from machine to machine and may well vary over time.

  It would be far better to compile the sizes of struct directly
  and make available.

  See /usr/include/bits/fcntl.h for struct flock sizes.
  As of now we have:
  {type, whence, start, len, pid)
    2      2       8     8    4
"""
# pylint: disable=too-many-locals,invalid-name

import os
import sys
import fcntl
import struct
import time

def _lock_cmds(ofd:bool) -> (int, int):
    """
    Return set/get flags
    if ofd is True use open file descriptor locking constants.
    """
    if ofd:
        set_lock = fcntl.F_OFD_SETLK
        get_lock = fcntl.F_OFD_SETLK
    else:
        set_lock = fcntl.F_SETLK
        get_lock = fcntl.F_GETLK

    return (get_lock, set_lock)

def _cstruct_flock_fmt():
    """
    return the python struct format of C struct flock
    """
    return 'hhqql'

def acquire_lock(filepath:str, ofd=False) -> (bool, int, str):
    """
    Lock file
    """
    mypid = os.getpid()
    fd = -1

    if not filepath:
        return (False, fd, 'error: Bad lockfile path')

    create_flags = os.O_RDWR | os.O_CREAT
    mode = 0o644
    try:
        fd = os.open(filepath, create_flags, mode=mode)

    except (PermissionError, OSError):
        # unable to create file.
        return (False, fd, 'error: Unable to create lockfile')

    if fd < 0:
        return (False, fd, 'error: open lockfile failed')

    #
    # acquire lock
    #
    l_type = fcntl.F_WRLCK
    l_whence = os.SEEK_SET
    l_start = 0
    l_len = 0
    l_pid = 0 #mypid

    # pack the C struct
    lfmt = _cstruct_flock_fmt()
    lockdata = struct.pack(lfmt, l_type, l_whence, l_start, l_len, l_pid)

    (_get_lock, set_lock) = _lock_cmds(ofd)
    print(f' set_lock flag = {set_lock}')

    try:
        retdata = fcntl.fcntl(fd, set_lock, lockdata)
    except (BlockingIOError,OSError) as err:
        print(f' got error {err}')
        return (False, -1, 'locked: already locked')

    retdata = struct.unpack(lfmt, retdata)
    cmd_ret = retdata[0]
    _pid_ret = retdata[4] # only useful when not OFD
    print(f'lock cmd_ret : {cmd_ret} pid : {_pid_ret}')

    #if cmd_ret == set_lock :
    return (True, fd, 'acquired: all good')
    #return (False, -1, 'unlocked: ? really')

def _unlink(file:str):
    """ remove file """
    if not file:
        return
    try:
        os.unlink(file)
    except OSError:
        pass

def _close(fd:int):
    """ close fd """
    if fd < 0:
        return
    try:
        os.close(fd)
    except OSError:
        pass

def release_lock(fd:int, filepath:str, ofd=False ) -> bool:
    """
    unlock
    """
    if fd < 0:
        _unlink(filepath)
        return (False, 'error: Bad lockfile path')
    #
    # drop lock
    #
    l_type = fcntl.F_UNLCK
    l_whence = os.SEEK_SET
    l_start = 0
    l_len = 0
    l_pid = 0

    # pack the C struct
    lfmt = _cstruct_flock_fmt()
    lockdata = struct.pack(lfmt, l_type, l_whence, l_start, l_len, l_pid)

    (_get_lock, set_lock) = _lock_cmds(ofd)

    try:
        retdata = fcntl.fcntl(fd, set_lock, lockdata)
    except (BlockingIOError,OSError):
        _close(fd)
        _unlink(filepath)
        return (False, 'unlock: error')

    retdata = struct.unpack(lfmt, retdata)
    cmd_ret = retdata[0]
    print(f'unlock cmd_ret : {cmd_ret}')
    _close(fd)
    _unlink(filepath)
    return (True, 'unlock: success')

#------------------------
# Test Application
#
def try_lock(lockfile, ofd):
    """ try to acquire a lock"""
    wait = 10
    (acquired, fd, msg) =  acquire_lock(lockfile, ofd)
    print(f' Lock acquired = {acquired} | fd = {fd} | {msg}')
    if acquired:
        time.sleep(wait)
    return (acquired, fd)

def main():
    """
      - Test lock manager
      - run 2 or more instances
      run with 'ofd' option to test ofd
    """
    ofd = False
    if len(sys.argv) > 1 and sys.argv[1] == 'ofd':
        ofd = True

    count = 1
    max_tries = 20

    lockfile = '/tmp/test-locky'

    print('Acquiring lock')
    (acquired, fd) = try_lock(lockfile, ofd)
    while not acquired and count < max_tries:
        print(' not acquired')
        time.sleep(1)
        count += 1
        (acquired, fd) = try_lock(lockfile, ofd)

    print('Releasing lock')
    (okay, msg) = release_lock(fd, lockfile, ofd)
    print(f' Status={okay} | {msg}')

if __name__ == '__main__':
    main()
