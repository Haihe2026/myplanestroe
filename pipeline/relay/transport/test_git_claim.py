"""Exercise documented git claim competition on isolated local repositories."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from relay import load_config


class GitClaimTests(unittest.TestCase):
    def git(self, cwd, *args, check=True):
        p=subprocess.run([load_config()["git"],"-C",str(cwd),*args],capture_output=True,text=True)
        if check and p.returncode:self.fail(p.stderr)
        return p

    def setup_pair(self, root):
        remote=root/"remote.git";remote.mkdir();self.git(remote,"init","--bare","--initial-branch=main")
        a=root/"a";self.git(root,"clone",str(remote),str(a))
        for path in [a]:
            self.git(path,"config","user.name","Synthetic Relay Test");self.git(path,"config","user.email","relay-test@example.invalid")
        (a/"README").write_text("synthetic")
        self.git(a,"add","README");self.git(a,"commit","-m","seed");self.git(a,"push","origin","HEAD:main")
        b=root/"b";self.git(root,"clone",str(remote),str(b))
        self.git(b,"config","user.name","Synthetic Relay Test");self.git(b,"config","user.email","relay-test@example.invalid")
        return remote,a,b

    def add_claim(self,path,claim):
        receipt=path/"receipts"/"test.json";receipt.parent.mkdir(exist_ok=True)
        with open(receipt,"x") as f:json.dump({"claim_id":claim},f)
        self.git(path,"add","receipts/test.json");self.git(path,"commit","-m","claim")

    def test_same_notification_second_push_loses(self):
        with tempfile.TemporaryDirectory() as directory:
            remote,a,b=self.setup_pair(Path(directory))
            self.add_claim(a,"a");self.add_claim(b,"b")
            self.git(a,"push","origin","HEAD:main")
            self.assertNotEqual(self.git(b,"push","origin","HEAD:main",check=False).returncode,0)
            self.git(b,"fetch","origin","main")
            self.assertEqual(json.loads(self.git(b,"show","origin/main:receipts/test.json").stdout)["claim_id"],"a")

    def test_unrelated_push_rejection_is_not_someone_else_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            remote,a,b=self.setup_pair(Path(directory))
            (a/"other.txt").write_text("unrelated update")
            self.git(a,"add","other.txt");self.git(a,"commit","-m","other");self.git(a,"push","origin","HEAD:main")
            self.add_claim(b,"b")
            self.assertNotEqual(self.git(b,"push","origin","HEAD:main",check=False).returncode,0)
            self.git(b,"fetch","origin","main")
            self.assertEqual(self.git(b,"ls-tree","-r","--name-only","origin/main","receipts/test.json").stdout.strip(),"")


if __name__=="__main__":unittest.main(verbosity=2)
