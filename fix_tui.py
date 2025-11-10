import subprocess, os, time

def run(cmd):
    print(f"\n$ {cmd}")
    subprocess.run(cmd, shell=True)

while True:
    print("""
┌───────────────────────── THE13TH Repair Console ─────────────────────────┐
1) Run full fix_all.py
2) Restart server
3) Rebuild DB schema
4) Pin ENV hash
5) View logs
6) Git push repair commit
7) Tail live logs
0) Exit
└──────────────────────────────────────────────────────────────────────────┘
""")
    c = input("Option: ")
    if c == "1": run("python3 fix_all.py")
    elif c == "2": run("pkill -f uvicorn; uvicorn main:app --reload &")
    elif c == "3": run("python3 fix_all.py")
    elif c == "4": run("python3 fix_all.py")
    elif c == "5": run("tail -n 200 uvicorn_fix.log")
    elif c == "6": run("git add . && git commit -m 'auto repair' && git push")
    elif c == "7": run("tail -f uvicorn_fix.log")
    elif c == "0": print("👋 Goodbye"); break
