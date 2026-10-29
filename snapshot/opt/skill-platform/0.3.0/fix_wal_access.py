"""SQLite read-only connections still need shared-memory sidecars in WAL mode."""
from pathlib import Path
import subprocess
p=Path('/etc/systemd/system/skill-monitor.service')
text=p.read_text()
if 'ReadWritePaths=' not in text:
    p.write_text(text.replace('ProtectHome=true\n','ProtectHome=true\nReadWritePaths=/var/lib/skill-monitor /var/lib/image-assistant /var/lib/temu-image-assistant\n'))
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','skill-monitor'],check=True)
