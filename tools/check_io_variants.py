from pathlib import Path
import hashlib
R=Path(__file__).resolve().parents[1]
a=(R/'rom/MAGICAL_HAPPY_RALLY_3D.rom').read_bytes()
b=(R/'rom/MAGICAL_HAPPY_RALLY_3D_EXTERNAL_88H.rom').read_bytes()
assert len(a)==len(b)==4194304
assert hashlib.sha256(a).hexdigest()=='3ef176403cb7ad752196dca81f877b99ffddaefd508315676bddcd159c345ea6'
diff=[i for i in range(len(a)) if a[i]!=b[i]]
assert len(diff)==321
assert all(a[i]-b[i]==16 and a[i] in (0x98,0x99,0x9a,0x9b,0x9c,0x9d,0x9f) and a[i-1] in (0xd3,0xdb,0x0e,0x01) for i in diff)
print('Verified: only 321 I/O operand bytes differ; internal release preserved.')
