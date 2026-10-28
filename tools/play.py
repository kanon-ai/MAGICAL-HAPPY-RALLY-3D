from pathlib import Path
import argparse,os,shutil,subprocess
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description="Launch MAGICAL HAPPY RALLY 3D with a separately installed Geo3D V2 openMSX.")
p.add_argument("--openmsx",default=os.environ.get("OPENMSX",shutil.which("openmsx")))
p.add_argument("--machine",default="Panasonic_FS-A1ST_V9968")
p.add_argument("--rom",type=Path,default=R/"rom/MAGICAL_HAPPY_RALLY_3D.rom")
p.add_argument("--dry-run",action="store_true")
a=p.parse_args()
if not a.openmsx:p.error("Set OPENMSX to the compatible openMSX executable, or pass --openmsx.")
e=Path(a.openmsx).resolve()
if not e.is_file():p.error("openMSX executable not found")
if not a.rom.is_file():p.error("ROM not found")
cmd=[str(e),"-machine",a.machine,"-ext","geo3d","-cart",str(a.rom.resolve()),"-romtype","ASCII16","-script",str(R/"tools/play.tcl")]
env=dict(os.environ)
if (e.parent/"share").is_dir():env["OPENMSX_SYSTEM_DATA"]=str(e.parent/"share")
if a.dry_run:print(subprocess.list2cmdline(cmd))
else:raise SystemExit(subprocess.call(cmd,env=env))
