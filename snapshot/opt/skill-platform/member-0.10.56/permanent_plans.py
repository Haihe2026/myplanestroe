"""Single active image catalog. No legacy pricing mode."""
import json
from pathlib import Path
CONFIG=json.loads(Path(__file__).with_name('image-plans.json').read_text(encoding='utf8'))
UNIT_PRICE_FEN=CONFIG['unit_price_fen']
if type(UNIT_PRICE_FEN)is not int or UNIT_PRICE_FEN<=0:raise ValueError('Invalid image unit price')
def catalog(items,per_image):
 result={}
 for item in items:
  bonus=item.get('bonus_images',0)
  if type(bonus)is not int or bonus<0:raise ValueError('Invalid image bonus')
  amount=item['price_fen'];images=amount//UNIT_PRICE_FEN+bonus if per_image else item['images']
  if type(amount)is not int or amount<=0 or type(images)is not int or images<=0 or (per_image and amount%UNIT_PRICE_FEN):raise ValueError('Invalid image plan')
  result[item['id']]=dict(name=item['name'],price_fen=amount,images=images,pricing_basis='per_image' if per_image else 'promotional_bundle')
 return result
SHARED_PLANS=catalog(CONFIG['shared'],True)
TEMU_PLANS=catalog(CONFIG['temu'],False)
PLANS=SHARED_PLANS.copy()
LEGACY_TEMU_PLANS={}
def permanent(plan):return plan in SHARED_PLANS or plan in TEMU_PLANS
def snapshot_permanent(order):return permanent(order['plan'])
def order_permanent(connection,row):return permanent(row['plan'])
