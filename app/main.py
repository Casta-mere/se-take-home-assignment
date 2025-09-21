from .manager import Manager
import sys

if "__name__" == "__main__":
    M = Manager()
    while(True):
        cmd = input("")
        M.handle_cmd(cmd)