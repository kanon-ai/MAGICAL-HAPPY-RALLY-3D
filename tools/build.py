"""Build the independent 4 MiB ASCII16 public-road cockpit cartridge.

SDCC and Pasmo are used from existing installations; no BIOS is copied.
Override their locations with SDCC and PASMO if moving this project.
"""
from pathlib import Path
import argparse
import errno
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BANK_BYTES = 8192
ROM_BYTES = 4194304
COURSE_OFFSET = 16 * BANK_BYTES
COURSE_RECORD_BYTES = 256


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom-name", default="MAGICAL_HAPPY_RALLY_3D.rom", help="Alternate ROM filename inside outputs for tests while PLAY is open")
    parser.add_argument("--pack-only", action="store_true", help="Reuse generated assets but always recompile C")
    parser.add_argument("--reference", action="store_true", help="Build C-command reference for pixel regression checks")
    parser.add_argument("--test-render-delay", action="store_true", help="TEST ONLY: add 400ms polling delay per rendered frame")
    parser.add_argument("--check-tools", action="store_true", help="Check local tool locations without building")
    args = parser.parse_args()
    if args.test_render_delay and args.rom_name == "PUBLIC_ROAD_COCKPIT.rom":
        parser.error("--test-render-delay requires a separate --rom-name; never replace the playable ROM")
    sdcc = Path(os.environ.get("SDCC") or shutil.which("sdcc") or "sdcc")
    pasmo = Path(os.environ.get("PASMO") or shutil.which("pasmo") or "pasmo")
    for label, path in (("SDCC", sdcc), ("PASMO", pasmo)):
        if not path.is_file():
            raise SystemExit(f"{label} not found: {path}. Set the {label} environment variable.")
    if args.check_tools:
        print(json.dumps({"python": sys.executable, "sdcc": str(sdcc), "pasmo": str(pasmo)}, indent=2))
        return
    build = ROOT / ("work/build-reference" if args.reference else "work/build")
    out = ROOT / ("outputs/reference" if args.reference else "outputs")
    build.mkdir(parents=True, exist_ok=True)
    out.mkdir(exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = str(sdcc.parent) + os.pathsep + env.get("PATH", "")

    def run(command):
        result = subprocess.run([str(item) for item in command], cwd=ROOT, env=env,
                                text=True, capture_output=True)
        for output in (result.stdout, result.stderr):
            if output.strip():
                print(output.strip())
        if result.returncode:
            raise SystemExit(result.returncode)

    # Pack the supplied, verified generated data; C and assembly are rebuilt.
    vram = (ROOT / "assets/vram.bin").read_bytes()
    course = (ROOT / "assets/stages.bin").read_bytes()
    scenery = (ROOT / "assets/scaled-atlas.bin").read_bytes()
    assert len(vram) == 98304, "VRAM image must occupy banks 4..15 (98304 bytes)"
    assert course and COURSE_OFFSET+len(course)<=ROM_BYTES, "Graphics exceed ROM allocation"
    flags = ["-mz80", "--std-sdcc11", "--opt-code-speed", "--no-std-crt0",
             "--code-loc", "0x8000", "--data-loc", "0xE000"]
    if args.reference:
        flags.append("-DREFERENCE_COMMANDS")
    if args.test_render_delay:
        flags.append("-DTEST_RENDER_DELAY")
    objects = []
    for name in ("game", "hardware", "view", "transition"):
        obj = build / f"{name}.rel"
        objects.append(obj)
        extra=["--codeseg", "VIEW", "--constseg", "VIEW", "--opt-code-size"] if name=="view" else (["--codeseg", "SCENE", "--constseg", "SCENE", "--opt-code-size"] if name=="transition" else (["--opt-code-size"] if name=="game" else []))
        run([sdcc, *flags, *extra, "-I", "src", "-c", f"src/{name}.c", "-o", obj.relative_to(ROOT)])
    # SDCC's 32-bit arithmetic helpers use _HOME. Without an explicit RAM
    # code address that area follows _DATA, outside the boot-copied runtime.
    # Reserve DC00-DFFF for these helpers; the HEX overlap/range audit below
    # rejects either a growing _CODE collision or a helper overflow.
    run([sdcc, *flags, "-Wl-b_HOME=0xDC00", "-Wl-b_VIEW=0x2400", "-Wl-b_SCENE=0xD940", "-o", build / "game.ihx", *objects])
    memory = {}
    for line in (build / "game.ihx").read_text().splitlines():
        if not line.startswith(":"):
            continue
        record = bytes.fromhex(line[1:])
        assert len(record) == record[0] + 5 and sum(record) % 256 == 0, "Invalid Intel HEX record"
        address = int.from_bytes(record[1:3], "big")
        kind = record[3]
        if kind == 0:
            for index, value in enumerate(record[4:-1]):
                target = address + index
                assert 0x2400 <= target < 0x3C00 or 0x8000 <= target < 0xE000, f"Runtime overflow at {target:04X}"
                assert target not in memory, f"Overlapping HEX data at {target:04X}"
                memory[target] = value
        elif kind not in (1,):
            raise AssertionError(f"Unsupported Intel HEX record type {kind}")
    map_text = (build / "game.map").read_text()
    symbols = {match[2]: int(match[1], 16) for match in
               re.finditer(r"^\s*([0-9A-F]{8})\s+(_[\w]+)\s", map_text, re.M)}
    areas = {match[1]: (int(match[2], 16), int(match[3], 16)) for match in
             re.finditer(r"^(_[\w]+)\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s", map_text, re.M)}
    assert "_main" in symbols, "Missing C entry point"
    assert "_DATA" in areas, "Missing linker data area"
    for name in ("_DATA", "_INITIALIZED", "_BSEG", "_BSS"):
        address, size = areas.get(name, (0, 0))
        assert not size or 0xE000 <= address <= address + size <= 0xF000, f"{name} exceeds E000-EFFF"
    runtime = bytearray([0xFF] * 24576)
    view_code=bytearray([0xFF]*6144)
    for address, value in memory.items():
        if address<0x8000:view_code[address-0x2400]=value
        else:runtime[address - 0x8000] = value
    assert areas["_VIEW"][0]==0x2400 and areas["_VIEW"][1]<=6144
    initializer, initial_size = areas.get("_INITIALIZER", (0, 0))
    initialized, data_size = areas.get("_INITIALIZED", (0, 0))
    assert initial_size == data_size, "SDCC initialized-data sizes disagree"
    initialization = ""
    if initial_size:
        assert 0x8000 <= initializer < initializer + initial_size <= 0xE000
        initialization = f"    ld hl,{initializer}\n    ld de,{initialized}\n    ld bc,{initial_size}\n    ldir"
    # Fixed host/player live in the verified gap below SDCC's _HOME area.
    assert areas['_CODE'][0]+areas['_CODE'][1] <= 0xD600
    assert areas['_DATA'][0]+areas['_DATA'][1] <= 0xEE00
    run([pasmo, '--bin', ROOT/'src/bgm.asm', build/'bgm.bin', build/'bgm.sym'])
    bgm=(build/'bgm.bin').read_bytes()
    assert len(bgm)<=0x340
    assert areas["_SCENE"][0]==0xD940 and areas["_SCENE"][1]<=0x2C0
    runtime=bytearray(runtime)
    runtime[0x5600:0x5600+len(bgm)]=bgm
    runtime=bytes(runtime)
    boot_source = (ROOT / "src/boot.asm").read_text()
    boot_source = boot_source.replace("ENTRY_POINT", str(symbols["_main"]))
    boot_source = boot_source.replace("INITIALIZE_DATA", initialization)
    (build / "boot.asm").write_text(boot_source)
    run([pasmo, "--bin", build / "boot.asm", build / "boot.bin"])
    boot = (build / "boot.bin").read_bytes()
    assert len(boot) == BANK_BYTES and boot[:2] == b"AB", "Invalid MSX cartridge boot bank"
    rom = boot + runtime + vram + course
    assert len(rom) <= 524288
    rom += bytes([255]) * (524288-len(rom))
    rom += (ROOT / "assets/long-course.bin").read_bytes()
    used = len(rom)
    rom += bytes([0xFF]) * (2097152 - used)
    logical_rom = rom[:1572864]+bytes([255])*524288
    # Retired marina geometry no longer occupies ROM.
    geometry = (ROOT / "assets/building-mesh.bin").read_bytes()
    assert len(geometry) <= 255*8192
    rom = bytearray([255])*ROM_BYTES
    for bank in range(256):
        rom[bank*16384+8192:bank*16384+16384] = logical_rom[bank*8192:(bank+1)*8192]
    rom[:8192] = boot
    for bank in range((len(geometry)+8191)//8192):
        rom[(bank+1)*16384:(bank+1)*16384+8192] = geometry[bank*8192:(bank+1)*8192]
    used += len(geometry) + 8192
    reciprocal=b"".join((491520//max(64,d*5)).to_bytes(2,"little") for d in range(4096))
    rom[192*16384+8192:193*16384]=reciprocal
    packets=(ROOT/'assets/traffic-packets.bin').read_bytes()
    assert len(packets)==7080
    rom[195*16384+8192:195*16384+8192+len(packets)]=packets
    rear=(ROOT/'assets/rear-course.bin').read_bytes()
    assert len(rear)==131072
    for block in range(16):
        start=(196+block)*16384+8192
        rom[start:start+8192]=rear[block*8192:(block+1)*8192]
    cross=bytearray()
    for w in range(256):
        half=w+(w>>2);mark=1+(w>>6);shoulder=max(1,w//10)
        vertices=[(-256,0,1),(-half-shoulder,0,0),(-half+mark,0,0),(half-mark,0,0),(half+shoulder,0,0),(2048,0,1),(-half-shoulder-(w*3//4),0,0),(-half-shoulder-(w*3//4)-max(1,w//16),0,0),(half+4+(w>>3),-(w>>3)-1,0),(half+4+(w>>3),-(w>>4),0),(-(mark//2),0,0),(mark,0,0)]
        for x,y,absolute in vertices:cross.extend(x.to_bytes(2,'little',signed=True)+bytes([y&255,absolute]))
        cross.extend(bytes(16))
    for block in range(2):
        start=(212+block)*16384+8192
        rom[start:start+8192]=cross[block*8192:(block+1)*8192]
    (ROOT/'assets/road-transfer.bin').write_bytes(cross)
    song=(ROOT/'assets/coastal-drive-opll/song.opz').read_bytes()
    assert 716<len(song)<=15713
    for block in range(2):
        part=song[block*8192:(block+1)*8192]
        start=(193+block)*16384+8192
        rom[start:start+len(part)]=part
    player_packet=(ROOT/'assets/player-packet.bin').read_bytes();assert len(player_packet)==4096
    player_model=(ROOT/'assets/player-model.bin').read_bytes();assert len(player_model)==276*5
    rom[215*16384+8192:215*16384+8192+4096]=player_packet
    rom[215*16384+8192+4096:215*16384+8192+4096+len(player_model)]=player_model
    player_projection=(ROOT/'assets/player-projection.bin').read_bytes();assert len(player_projection)==6*8192
    for block in range(6):
        start=(216+block)*16384+8192
        rom[start:start+8192]=player_projection[block*8192:(block+1)*8192]
    used += len(player_projection)
    markers=(ROOT/'assets/road-markers.bin').read_bytes();assert len(markers)==16*8192
    for block in range(16):
        start=(222+block)*16384+8192
        rom[start:start+8192]=markers[block*8192:(block+1)*8192]
    used += len(markers)
    rom[214*16384+8192:214*16384+8192+6144]=view_code
    used += 8192+len(packets)+len(rear)+len(song)+len(cross)+6144+4096+len(player_model)
    appearance=(ROOT/'assets/coast-appearance.bin').read_bytes()
    assert len(appearance)==8*8192
    for piece in range(8):
        start=(238+piece)*16384+8192
        assert rom[start:start+8192]==bytes([255])*8192
        rom[start:start+8192]=appearance[piece*8192:(piece+1)*8192]
    used+=len(appearance)
    inland=(ROOT/'assets/inland-sky.bin').read_bytes();assert len(inland)==256*78
    for block in range(3):
        part=inland[block*8192:(block+1)*8192];start=(246+block)*16384+8192
        assert rom[start:start+len(part)]==bytes([255])*len(part)
        rom[start:start+len(part)]=part
    used+=len(inland)
    rom = bytes(rom)
    assert len(rom) == ROM_BYTES
    assert logical_rom[COURSE_OFFSET:COURSE_OFFSET + len(course)] == course
    assert Path(args.rom_name).name == args.rom_name
    target = out / args.rom_name
    try:
        target.write_bytes(rom)
    except OSError as error:
        if error.errno not in (errno.EACCES, errno.EPERM, errno.EINVAL):
            raise
        raise SystemExit(
            f"Cannot replace {target.name}; Windows may be locking the loaded cartridge.\n"
            "Close this project's emulator, run BUILD.cmd again, then restart it with PLAY.cmd.\n"
            "Eject alone may leave the ROM file locked on Windows."
        ) from None
    symbols_json = json.dumps(symbols, indent=2) + "\n"
    (build / "symbols.json").write_text(symbols_json)
    (out / "symbols.json").write_text(symbols_json)
    source_paths = sorted((ROOT / "assets/coastal-drive-opll").glob("*"))+sorted((ROOT / "src").glob("*"))+sorted((ROOT / "tools").glob("*.py"))+sorted((ROOT / "assets/generated-modern").glob("*"))
    manifest = {
        "title": "MAGICAL HAPPY RALLY 3D", "version": "v0.1.0-demo", "working_title": False,
        "file": target.name, "machine": "MSX turbo R + V9968 + Geo3D V2", "mapper": "ASCII16",
        "rom_bytes": len(rom), "allocated_bytes": used, "free_bytes": ROM_BYTES - used,
        "view_ram_code_bytes":areas["_VIEW"][1], "view_ram_address":"2400-3BFF",
        "runtime_code_bytes": areas["_CODE"][1], "runtime_data_bytes": areas["_DATA"][1],
        "runtime_bytes": max(memory) - 0x8000 + 1, "runtime_address": "8000-DFFF",
        "data_address": "E000-EFFF", "stack_top": "F300", "entry": hex(symbols["_main"]),
        "vram": {"bytes": len(vram), "logical_8k_offset": 4 * BANK_BYTES, "physical_layout": "upper 8KiB of ASCII16 banks 4..15",
                 "first_bank": 4, "last_bank": 15, "sha256": digest(vram)},
        "course": {"bytes": 1048576, "logical_8k_offset": 524288, "physical_layout": "upper 8KiB of ASCII16 banks 64..191",
                   "first_bank": 64, "record_bytes": COURSE_RECORD_BYTES,
                   "records": 4096,"stages":1,"compression":"Uncompressed direct ROM read; 6000..7FFF, banks 64..191",
                   "road_bytes": 128, "object_bytes": 64, "event_projection_bytes": 64,
                   "sha256": digest((ROOT / "assets/long-course.bin").read_bytes())},
        "scenery": {"master_count":4,"storage":"compressed masters, two uploaded at stage entry","active_vram_bytes":65536,"vram_byte_offset":0x30000},
        "mesh": {"bytes":len(geometry),"record_bytes":480,"records_per_bank":17,"first_bank":1,"window":"4000..5FFF","sha256":digest(geometry)},
        "screen":{"mode":"SCREEN8 EPAL","width":256,"height":212,"colors":256,"vram_bytes":262144},
        "rear_view": {"bytes":len(rear),"rom_banks":[196,211],"records":4096,"sha256":digest(rear)},
        "traffic_transfer": {"bytes":len(packets),"rom_bank":195,"sha256":digest(packets)},
        "road_transfer": {"bytes":len(cross),"rom_banks":[212,213],"sha256":digest(cross)},
        "bgm":{"song_bytes":len(song),"song_sha256":digest(song),"rom_banks":[193,194],"mapper_ram_bytes":16384,"driver_ram":"EE00-EE2F","driver_code":"D600-D92A","update_hz":60,"loop":True},
        "ram_cache_bytes":480,"minimum_ram_bytes":262144,"cpu_mode":"R800 ROM mode; internal RAM runtime; direct ROM course",
        "sha256": digest(rom),
        "sources": {str(path.relative_to(ROOT)).replace("\\", "/"): digest(path.read_bytes())
                    for path in source_paths if path.is_file()},
    }
    (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
