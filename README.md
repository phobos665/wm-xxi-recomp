# wm-xxi-recomp

WWE WrestleMania 21 for the original Xbox, recompiled into a native program on
the [DirectXbox-Recomp](https://github.com/phobos665/DirectXbox-Recomp) toolkit
(`xboxrecomp/` here). You build it from your own copy of the game: the build
translates the game's code to C on your machine and compiles it. This
repository contains no game code or data.

## State

Early bring-up. The intro movies, title screen, menus and a Main Event match
(entrances and the match itself) run and draw, wrestlers included, at the
console's 30 fps and speed. Not yet played through properly.

- **30 fps, as on the console.** The game steps its logic once a frame, so it
  is held to the 30 it asks for; at 60 it ran at double speed.
- **60 on screen:** frame interpolation (`RECOMP_FRAME_INTERP=2`, or the
  launcher's Frame interpolation row) draws a frame between each two the game
  draws. Skinned limbs are not blended yet.
- **Widescreen (Hor+)**, `RECOMP_WIDESCREEN=1`: the camera is widened, the 2D
  stays 4:3 in the middle. Early.

Known problems:

- The first load into a match can stall for minutes while the game copies its
  sound banks and entrance movies into its cache drive.
- On a second boot the game may say it is unable to load options; A resets them.

| | |
| --- | --- |
| Release | Europe (PAL), title `545100F9` |
| XDK | 5849, D3D8 (not LTCG) |
| `default.xbe` SHA-1 | `08600f8692b80f77acef219c0696df9de3554956` |

## Build

What you need is the same as for the toolkit; see its
`docs/GETTING_STARTED.md` (on SteamOS, build inside the Freedesktop SDK
Flatpak).

```sh
git clone --recursive https://github.com/phobos665/wm-xxi-recomp.git
cd wm-xxi-recomp
```

Put the extracted disc in a folder called `game` (or make `game` a link to
it), so that `game/default.xbe` exists with the `.wad` archives beside it. To
extract an ISO:

```sh
python3 -m tools.xiso unpack "WWE Wrestlemania XXI (Europe).iso" -o ../game   # from xboxrecomp/
```

On Linux, fetch the shader compiler once: `bash xboxrecomp/tools/linux/fetch_dxc.sh`.
Then:

```sh
py -3 scripts/build.py      # Windows
python3 scripts/build.py    # Linux
```

The program ends up in `build/Release/` as `wwe21_recomp`, with
`wwe21_recomp_launcher` beside it for the settings window.

`py -3 scripts/build.py --relift` translates the game again, needed whenever
the toolkit, `config/` or `src/recomp_manual.c` changes.

The toolkit is pinned to its `feat/wwe21-renderer` branch, which carries the
renderer fixes this game needs until they reach its `main`.

`config/xdk_symbols.json` and `config/seeds.json` list addresses inside the PAL `default.xbe`; another
release needs its own.
