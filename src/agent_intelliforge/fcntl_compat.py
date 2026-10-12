"""flock-compatible adapter for generated portable copies; not legacy sources."""
from __future__ import annotations

import os
import errno

LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4, 8


def flock(handle, operation):
    fd = handle if isinstance(handle, int) else handle.fileno()
    if os.name != "nt":
        import fcntl
        return fcntl.flock(fd, operation)
    import msvcrt
    import time
    os.lseek(fd, 0, os.SEEK_SET)
    if operation & LOCK_UN:
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1); return
    if os.fstat(fd).st_size == 0:
        os.write(fd, b"\0"); os.lseek(fd, 0, os.SEEK_SET)
    while True:
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1); return
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK): raise
            if operation & LOCK_NB:
                raise BlockingIOError("Another operation owns the lock") from error
            time.sleep(0.05)
