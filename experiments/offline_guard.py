"""Deny outbound network syscalls in Linux-only private OCR experiments.

Public model downloads happen separately. This restrictive filter applies only
to the experiment process and all its threads; it never changes host policy.
Fail closed if the filter cannot be installed.
"""
import ctypes
import ctypes.util
import errno
import os
import sys


def block_network():
    if sys.platform != 'linux':
        raise RuntimeError('This strict experiment guard requires Linux')
    path = ctypes.util.find_library('seccomp')
    if not path:
        raise RuntimeError('libseccomp is required before processing private input')
    lib = ctypes.CDLL(path, use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_attr_set.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32]
    lib.seccomp_attr_set.restype = ctypes.c_int
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                   ctypes.c_int, ctypes.c_uint]
    lib.seccomp_rule_add.restype = ctypes.c_int
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_load.restype = ctypes.c_int
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    if not context:
        raise RuntimeError('Could not allocate offline syscall filter')
    try:
        # SCMP_FLTATR_CTL_TSYNC: cover threads imported libraries may have started.
        if lib.seccomp_attr_set(context, 4, 1) != 0:
            raise RuntimeError('Cannot synchronize offline filter across threads')
        for name in (b'connect', b'sendto', b'sendmsg', b'sendmmsg', b'io_uring_setup'):
            number = lib.seccomp_syscall_resolve_name(name)
            if number < 0 or lib.seccomp_rule_add(context,
                    0x00050000 | errno.EPERM, number, 0) != 0:
                raise RuntimeError('Cannot add offline rule for ' + name.decode())
        if lib.seccomp_load(context) != 0:
            raise RuntimeError('Cannot enforce offline processing')
    finally:
        lib.seccomp_release(context)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
