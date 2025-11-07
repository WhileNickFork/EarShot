import asyncio, subprocess, logging, os, random, time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
log = logging.getLogger("gps")

class TachyonGPS:
    def __init__(self, simulation: bool = False):
        self.sim = simulation
        self.last: Optional[Dict[str,Any]] = None

    def _sim(self)->Dict[str,Any]:
        base_lat, base_lon = 43.0731, -89.4012
        return {
            'valid': 1,
            'latitude': base_lat + random.uniform(-0.001, 0.001),
            'longitude': base_lon + random.uniform(-0.001, 0.001),
            'altitude': 260.0 + random.uniform(-5, 5),
            'speed': random.uniform(0, 5),
            'utc': datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S"),
            'svnum': random.randint(8, 12),
            'fixmode': 3,
            'gpssta': 1
        }

    def _query_ril(self)->Optional[Dict[str,Any]]:
        try:
            r = subprocess.run(['particle-tachyon-ril-ctl','gnss'],
                               capture_output=True, text=True, timeout=10)
            if r.returncode not in (0,250):
                log.error(f"gnss rc={r.returncode} stderr={r.stderr.strip()}")
                return None
            out = {}
            for line in r.stdout.strip().splitlines():
                if ':' in line:
                    k,v = line.split(':',1)
                    k=k.strip(); v=v.strip()
                    try:
                        out[k] = float(v) if '.' in v else int(v)
                    except ValueError:
                        out[k] = v
            return out
        except Exception as e:
            log.warning(f"gnss query error: {e}")
            return None

    async def run(self, poll_sec:int=2):
        log.info(f"gps: starting (simulation={self.sim})")
        while True:
            d = self._sim() if self.sim else self._query_ril()
            if d and d.get('valid',0) and d.get('fixmode',1) >= 2:
                self.last = {"lat": float(d.get('latitude',0.0)),
                             "lon": float(d.get('longitude',0.0))}
            await asyncio.sleep(poll_sec)

    def current(self)->Optional[Dict[str,float]]:
        return self.last