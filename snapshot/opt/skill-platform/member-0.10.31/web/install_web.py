"""Install (or roll back) the 0.10.31 register pages into a web root.

    python3 install_web.py /var/www/image-assistant                      # temu (default)
    python3 install_web.py /var/www/image-assistant --product gemini     # gemini
    python3 install_web.py /var/www/image-assistant --product all
    python3 install_web.py /var/www/image-assistant --rollback           # restore the backups

Only the register page files of the chosen product(s) are touched:
  temu   : membership/temu/register/{index.html,trial-register.js,trial-register.css}
  gemini : membership/gemini/register/{index.html,register.js,register.css}
Backups are written next to each file as <name>.pre-0.10.31 and are never overwritten.
The gemini page only does something once the service has gemini in MYPLANESTORE_DEVICE_LINK_PRODUCTS;
before that it falls back to the normal new-account form.
"""
import shutil
import sys
from pathlib import Path

PRODUCTS = {
    'temu': ('membership/temu/register', ('index.html', 'trial-register.js', 'trial-register.css')),
    'gemini': ('membership/gemini/register', ('index.html', 'register.js', 'register.css')),
}
SOURCE = Path(__file__).resolve().parent
SUFFIX = '.pre-0.10.31'


def chosen(argv):
    if '--product' not in argv:
        return ['temu']
    value = argv[argv.index('--product') + 1]
    return list(PRODUCTS) if value == 'all' else [value]


def main(argv):
    rollback = '--rollback' in argv
    rest = [a for a in argv[1:] if not a.startswith('--') and argv[argv.index(a) - 1] != '--product']
    if len(rest) != 1 or any(p not in PRODUCTS for p in chosen(argv)):
        print(__doc__)
        return 2
    root = Path(rest[0])
    failed = 0
    for product in chosen(argv):
        folder, files = PRODUCTS[product]
        target, source = root / folder, SOURCE / folder
        if not target.is_dir():
            print('%s: not a web root (missing %s)' % (product, target))
            failed = 1
            continue
        if rollback:
            missing = [n for n in files if not (target / (n + SUFFIX)).is_file()]
            if missing:
                print('%s: no backup for %s' % (product, ', '.join(missing)))
                failed = 1
                continue
            for name in files:
                shutil.copy2(target / (name + SUFFIX), target / name)
            print('%s: rolled back %s' % (product, ', '.join(files)))
            continue
        for name in files:
            backup = target / (name + SUFFIX)
            if not backup.exists():
                shutil.copy2(target / name, backup)
        for name in files:
            shutil.copy2(source / name, target / name)
        print('%s: installed 0.10.31 register page into %s (backups: *%s)' % (product, target, SUFFIX))
    return failed


if __name__ == '__main__':
    sys.exit(main(sys.argv))
