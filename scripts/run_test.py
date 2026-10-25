"""Run the built game unattended: muted, behind other windows, scripted input,
against a mirror of the game folder so nothing it saves lands in your copy.

    py -3 scripts/run_test.py --seconds 120 --tag boot      (python3 off Windows)
    py -3 scripts/run_test.py --seq "20000:start,25000:a" --dump 300 -- RECOMP_FPS=5

Everything goes in .pipeline/runs/<tag>/: run.log (stdout and stderr), frames/
(frame dumps, with --dump N every N swaps), saves/ (RECOMP_SAVE_DIR). The
mirror is .pipeline/mirror/: a junction (a symlink off Windows) to Data/, hard
links to default.xbe and the .wad archives, and its own UDATA/TDATA, which
--keep-saves leaves alone
between runs (otherwise they are cleared so every run is a first boot).

Extra NAME=VALUE arguments after -- are added to the environment.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "game"
MIRROR = ROOT / ".pipeline" / "mirror"
RUNS = ROOT / ".pipeline" / "runs"
EXE = ROOT / "build" / "Release" / ("wwe21_recomp.exe" if os.name == "nt" else "wwe21_recomp")

# A script that presses nothing for an hour: a connected pad must never drive
# an unattended run, and a script owns the pad.
IDLE_SEQ = "3600000:back:1"

# Start, every three seconds from the title screen on: through the main
# menu into a Main Event match (Batista v Big Show), clocked from the first
# pad read. The title screen is up ~60 s into a first boot, which copies the
# movies to the cache drive first; the match loads from ~110 s, and its
# first load can take minutes more. --to-level puts this in front of --seq.
LEVEL_SEQ = ",".join("%d:start" % t for t in range(60000, 105001, 3000))


def make_mirror(keep_saves):
    MIRROR.mkdir(parents=True, exist_ok=True)
    for item in GAME.iterdir():
        name = item.name
        if name.upper() in ("UDATA", "TDATA"):
            continue
        dst = MIRROR / name
        if dst.exists() or dst.is_symlink():
            continue
        if item.is_dir():
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(item.resolve())],
                               check=True, stdout=subprocess.DEVNULL)
            else:
                os.symlink(item.resolve(), dst, target_is_directory=True)
        else:
            try:
                os.link(item.resolve(), dst)
            except OSError:
                shutil.copy2(item, dst)
    if not keep_saves:
        for d in ("UDATA", "TDATA"):
            p = MIRROR / d
            # Real folders in the mirror only, never through a junction.
            if p.is_dir() and not p.is_symlink() and not os.path.islink(p):
                shutil.rmtree(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=float, default=90)
    ap.add_argument("--tag", default=time.strftime("run-%H%M%S"))
    ap.add_argument("--seq", default=IDLE_SEQ, help="RECOMP_INPUT_SEQ")
    ap.add_argument("--to-level", action="store_true",
                    help="play the menus into the first level first (LEVEL_SEQ)")
    ap.add_argument("--dump", type=int, default=0,
                    help="dump a frame every N swaps (RECOMP_HLE_D3D8_DUMP)")
    ap.add_argument("--keep-saves", action="store_true")
    ap.add_argument("--exe", default=str(EXE))
    ap.add_argument("env", nargs="*", help="NAME=VALUE after --")
    args = ap.parse_args()

    make_mirror(args.keep_saves)
    out = RUNS / args.tag
    if out.exists():
        shutil.rmtree(out)
    (out / "saves").mkdir(parents=True)
    (out / "user").mkdir()

    env = dict(os.environ)
    env.update({
        "RECOMP_MUTE": "1",
        "RECOMP_WINDOW_BACKGROUND": "1",
        "RECOMP_GAME_DIR": str(MIRROR),
        "RECOMP_SAVE_DIR": str(out / "saves"),
        # Its own settings folder, empty: the player's launcher settings
        # (fullscreen, a frame cap, a resolution scale) never apply to a test
        # run, so every run starts from the defaults plus what it is given.
        "RECOMP_USER_DIR": str(out / "user"),
        "RECOMP_INPUT_SEQ": LEVEL_SEQ + "," + args.seq if args.to_level else args.seq,
    })
    if args.dump:
        (out / "frames").mkdir()
        env.update({
            "RECOMP_HLE_D3D8_DUMP": str(out / "frames" / "f"),
            "RECOMP_HLE_D3D8_DUMP_EVERY": str(args.dump),
            "RECOMP_HLE_D3D8_DUMP_MINDRAWS": "1",
        })
    for kv in args.env:
        k, _, v = kv.partition("=")
        env[k] = v

    # Nothing a test run does may take the focus. The error mode is inherited:
    # a crash ends the process instead of raising Windows Error Reporting's
    # dialog. The show flag is what the game's first ShowWindow gets.
    startupinfo = None
    if os.name == "nt":
        import ctypes
        SEM_FAILCRITICALERRORS, SEM_NOGPFAULTERRORBOX = 0x0001, 0x0002
        k32 = ctypes.windll.kernel32
        k32.SetErrorMode(k32.GetErrorMode() | SEM_FAILCRITICALERRORS
                         | SEM_NOGPFAULTERRORBOX)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 4             # SW_SHOWNOACTIVATE

    log = out / "run.log"
    start = time.time()
    with open(log, "wb") as f:
        p = subprocess.Popen([args.exe], cwd=str(Path(args.exe).parent), env=env,
                             stdout=f, stderr=subprocess.STDOUT,
                             startupinfo=startupinfo)
        try:
            code = p.wait(timeout=args.seconds)
            how = "exited"
        except subprocess.TimeoutExpired:
            p.kill()
            code = p.wait()
            how = "killed at the time limit"
    print(f"RUN_DONE {how} code={code} after {time.time() - start:.0f}s log={log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
