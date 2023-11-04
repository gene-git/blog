#!/usr/bin/python
"""
Example fcntl.flock locks

This is what use for file based inter process locking
"""
# pylint: disable=too-many-locals,invalid-name

import os
import fcntl
from dataclasses import dataclass
import time     # for main test
#import pdb

@dataclass
class LockMgr:
    """Class for keeping track of an item in inventory."""
    lockfile: str = None
    fd_w: int = -1
    acquired: bool = False
    msg: str = ''

def acquire_lock(lock_mgr:LockMgr) -> bool:
    """
    Acquire Lock
     - we dont need/want buffered IO stream.
    """
    if lock_mgr.acquired :
        # already locked
        lock_mgr.msg = 'Already locked'
        return True

    create_flags = os.O_RDWR | os.O_CREAT
    mode = 0o644
    try:
        lock_mgr.fd_w = os.open(lock_mgr.lockfile, create_flags, mode=mode)
        fcntl.flock(lock_mgr.fd_w, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_mgr.acquired = True
        lock_mgr.msg = 'Success'

    except (IOError, OSError) as err:
        if lock_mgr.fd_w:
            os.close(lock_mgr.fd_w)
        lock_mgr.fd_w = -1
        lock_mgr.acquired = False
        lock_mgr.msg = f'Failed : {err}'

    return lock_mgr.acquired

def _unlink(file:str):
    """ remove lock file """
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

def clear_lockfile(lock_mgr):
    """ reset the lock file """
    lock_mgr.acquired = False
    try:
        os.unlink(lock_mgr.lockfile)
        if lock_mgr.fd_w >= 0:
            os.close(lock_mgr.fd_w)
    except OSError:
        pass

    lock_mgr.fd_w = -1

def release_lock(lock_mgr:LockMgr) -> bool:
    """
    Release acquired lock
    """
    if not lock_mgr.acquired:
        lock_mgr.msg = 'No lock to release'
        return False

    if lock_mgr.fd_w < 0:
        clear_lockfile(lock_mgr)
        lock_mgr.msg = 'error: Lock acquired but bad lockfile fd'
        return False

    try:
        fcntl.flock(lock_mgr.fd_w, fcntl.LOCK_UN)
        lock_mgr.msg = 'success: lock released'
        okay = True

    except OSError as err:
        # Shouldn't happen : failed somehow - still mark unlocked?
        lock_mgr.msg = f'Error: failed releasing lock : {err}'
        okay = False

    clear_lockfile(lock_mgr)
    lock_mgr.acquired = False

    return okay

#------------------------
# Test Application
#
def print_lock_status(lock_mgr):
    """ print lock_mgr state """

    file = lock_mgr.lockfile

    acq = f'Lock acquired: {lock_mgr.acquired}'
    fdw = f'fd_w: {lock_mgr.fd_w}'
    print(f'{file}: {acq} | {fdw} | {lock_mgr.msg}')

def try_lock(lock_mgr):
    """ try to acquire a lock"""
    wait = 10
    acquired =  acquire_lock(lock_mgr)

    print_lock_status(lock_mgr)
    if acquired:
        time.sleep(wait)

    return acquired

def main():
    """
      - Test lock manager
      - run 2 or more instances
      run with 'ofd' option to test ofd
    """
    #pdb.set_trace()
    lock_mgr = LockMgr()
    lock_mgr.lockfile = '/tmp/test-locky'

    count = 1
    max_tries = 20

    print('Acquiring lock')
    acquired = try_lock(lock_mgr)
    while not acquired and count < max_tries:
        print(' not acquired')
        time.sleep(1)
        count += 1
        acquired = try_lock(lock_mgr)

    print('Releasing lock')
    release_lock(lock_mgr)
    print_lock_status(lock_mgr)

if __name__ == '__main__':
    main()
