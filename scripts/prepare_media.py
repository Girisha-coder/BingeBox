"""Prewarm and probe all demo runtimes inside the running API container."""

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = """
import json,subprocess
from app.database import connect
from app.main import placeholder
with connect() as db:
    runtimes=[r['seconds'] for r in db.execute('SELECT duration_min*60 AS seconds FROM movie UNION SELECT duration_min*60 FROM episode ORDER BY seconds')]
items=[]
for runtime in runtimes:
    path=placeholder(runtime)
    result=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=width,height,codec_name','-of','json',str(path)]))
    actual=float(result['format']['duration'])
    assert abs(actual-runtime)<0.01,(runtime,actual)
    assert result['streams'][0]['codec_name']=='h264'
    items.append({'runtime_sec':runtime,'actual_duration_sec':actual,'bytes':path.stat().st_size})
print(json.dumps({'generated_original_placeholders':True,'quality':'SD','width':640,'height':360,'count':len(items),'total_bytes':sum(i['bytes'] for i in items),'items':items}))
"""
if __name__ == "__main__":
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c", PROGRAM],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    (ROOT / "media/manifest.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "items"}, indent=2))
