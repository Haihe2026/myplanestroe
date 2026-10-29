import runpy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent/'core'))
import manual_payments
from permanent_plans import order_permanent
sys.path.insert(0,'/opt/skill-platform/member-0.5.0/ops')
sys.path.insert(0,str(Path(__file__).parent))
import monitor
from settlement import Settlement
from legacy_temu_manual import install_operator
install_operator(Settlement)
original_preview=Settlement.preview
def preview(self,product,oid):
    result=original_preview(self,product,oid)
    with self.connection() as connection:
        row=connection.execute('SELECT * FROM member_orders WHERE id=?',(oid,)).fetchone()
        result['permanent']=(result['expires'] is None) if result['status']=='paid' else order_permanent(connection,row)
    return result
Settlement.preview=preview
from enterprise_ops import extend_handler
monitor.handler=extend_handler(monitor.handler,'/var/lib/skill-platform/shared.db')
runpy.run_path('/opt/skill-platform/ops-test-marks-0.10.2/run_ops.py',run_name='__main__')
