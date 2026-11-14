"""Private local state permissions. Standard library only; never relax permissions on failure."""
import os
import stat

_WINDOWS = None


def _windows():
    global _WINDOWS
    if _WINDOWS is not None:
        return _WINDOWS
    import ctypes as c
    from ctypes import wintypes as w
    adv = c.WinDLL('advapi32', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    adv.OpenProcessToken.restype = w.BOOL
    adv.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
    adv.GetTokenInformation.restype = w.BOOL
    adv.ConvertSidToStringSidW.argtypes = [c.c_void_p, c.POINTER(w.LPWSTR)]
    adv.ConvertSidToStringSidW.restype = w.BOOL
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.LocalFree.argtypes = [c.c_void_p]
    kernel.LocalFree.restype = c.c_void_p
    token = w.HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token)):
        raise OSError('private identity unavailable')
    try:
        size = w.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, c.byref(size))
        if not size.value or size.value > 65536:
            raise OSError('private identity unavailable')
        buf = c.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, buf, size.value, c.byref(size)):
            raise OSError('private identity unavailable')
        sid_pointer = c.cast(buf, c.POINTER(c.c_void_p))[0]
        text = w.LPWSTR()
        if not adv.ConvertSidToStringSidW(sid_pointer, c.byref(text)):
            raise OSError('private identity unavailable')
        try:
            sid = text.value
        finally:
            kernel.LocalFree(c.cast(text, c.c_void_p))
    finally:
        kernel.CloseHandle(token)
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR, w.DWORD, c.POINTER(c.c_void_p), c.POINTER(w.DWORD)]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = w.BOOL
    adv.GetSecurityDescriptorDacl.argtypes = [c.c_void_p, c.POINTER(w.BOOL), c.POINTER(c.c_void_p), c.POINTER(w.BOOL)]
    adv.GetSecurityDescriptorDacl.restype = w.BOOL
    adv.SetNamedSecurityInfoW.argtypes = [w.LPWSTR, c.c_int, w.DWORD, c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p]
    adv.SetNamedSecurityInfoW.restype = w.DWORD
    _WINDOWS = c, w, adv, kernel, sid
    return _WINDOWS


def _reject_link(path):
    if os.path.islink(path):
        raise OSError('unsafe private state path')
    if os.name == 'nt' and os.path.lexists(path):
        import ctypes as c
        fn = c.WinDLL('kernel32', use_last_error=True).GetFileAttributesW
        fn.argtypes = [c.c_wchar_p]
        fn.restype = c.c_ulong
        attrs = fn(os.path.abspath(path))
        if attrs == 0xffffffff or attrs & 0x400:
            raise OSError('unsafe private state path')


def restrict(path, directory=False):
    _reject_link(path)
    if os.name != 'nt':
        os.chmod(path, 0o700 if directory else 0o600)
        if stat.S_IMODE(os.stat(path).st_mode) != (0o700 if directory else 0o600):
            raise OSError('private permissions unavailable')
        return
    c, w, adv, kernel, sid = _windows()
    descriptor = c.c_void_p()
    # Protected DACL, exactly the current user; child files/directories inherit only this ACE.
    sddl = 'D:P(A;%s;FA;;;%s)' % ('OICI' if directory else '', sid)
    if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, c.byref(descriptor), None):
        raise OSError('private permissions unavailable')
    try:
        present, defaulted, dacl = w.BOOL(), w.BOOL(), c.c_void_p()
        if not adv.GetSecurityDescriptorDacl(descriptor, c.byref(present), c.byref(dacl), c.byref(defaulted)) or not present.value or not dacl:
            raise OSError('private permissions unavailable')
        if adv.SetNamedSecurityInfoW(os.path.abspath(path), 1, 0x80000004, None, None, dacl, None):
            raise OSError('private permissions unavailable')
    finally:
        kernel.LocalFree(descriptor)


def directory(path):
    _reject_link(path)
    existed = os.path.isdir(path)
    if existed and os.name != 'nt':
        mode = stat.S_IMODE(os.stat(path).st_mode)
        # Tighten other-user access, but never add owner write access to a read-only state tree.
        if mode & 0o077:
            os.chmod(path, mode & 0o700)
        if not mode & 0o200 or not mode & 0o100:
            raise OSError('private storage is read only')
    if existed and os.name == 'nt':
        import uuid
        probe = os.path.join(path, 'permission-' + uuid.uuid4().hex + '.tmp')
        # No secret is written before tightening the DACL. An inaccessible existing state tree
        # is skipped rather than using ownership to grant ourselves new write permission.
        descriptor = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        os.unlink(probe)
    os.makedirs(path, mode=0o700, exist_ok=True)
    restrict(path, True)
    return path


def atomic_json(path, value):
    import json
    directory(os.path.dirname(path))
    _reject_link(path)
    tmp = path + '.tmp'
    _reject_link(tmp)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        restrict(tmp)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            fd = None
            json.dump(value, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        restrict(path)
    finally:
        if fd is not None:
            os.close(fd)
