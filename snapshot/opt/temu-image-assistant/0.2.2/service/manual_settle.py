"""Local server operator only. Check the bank receipt before confirming."""
import argparse
import json
from server import Store

parser = argparse.ArgumentParser()
parser.add_argument("--db", default="/var/lib/temu-image-assistant/trial.db")
sub = parser.add_subparsers(dest="command",required=True)
show = sub.add_parser("list")
show.add_argument("--limit",type=int,default=20)
confirm = sub.add_parser("confirm")
confirm.add_argument("--order",required=True)
confirm.add_argument("--amount-fen",type=int,required=True)
confirm.add_argument("--bank-transaction",required=True)
args = parser.parse_args()
store = Store(args.db)
if args.command == "list":
    with store.connect() as c:
        print(json.dumps([dict(row) for row in c.execute("SELECT id,user_id,plan,amount_fen,status,created FROM member_orders WHERE status IN ('pending','reported') ORDER BY created DESC LIMIT ?",(min(max(args.limit,1),100),))],ensure_ascii=False,indent=2))
else:
    changed = store.membership.confirm_manual(args.order,args.amount_fen,args.bank_transaction)
    print(json.dumps({"credited":changed,"order":args.order}))
