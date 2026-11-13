"""Validate/reprocess the bundled NASA response offline, retaining its provenance."""
from datetime import datetime, timedelta
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'data/nasa_power_raw.json';raw=path.read_bytes();data=json.loads(raw)
    metadata=json.loads((ROOT/'data/kisumu_weather.json').read_text())
    if data['parameters']['ALLSKY_SFC_SW_DWN']['units']!='Wh/m^2' or data['header']['time_standard']!='UTC':
        raise ValueError('Unexpected units/time standard; conversion must be reviewed')
    values=data['properties']['parameter']['ALLSKY_SFC_SW_DWN'];local=datetime.fromisoformat(metadata['local_date'])
    profile=[]
    for hour in range(24):
        value=values[(local+timedelta(hours=hour-3)).strftime('%Y%m%d%H')]
        if type(value) not in (float,int) or not math.isfinite(value) or not 0<=value<=2000:
            raise ValueError('Missing or unexpected irradiance value')
        profile.append(value/1000)
    metadata.update(irradiance_kwh_m2=profile,raw_sha256=hashlib.sha256(raw).hexdigest())
    (ROOT/'data/kisumu_weather.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(f'Validated 24 local hours: {sum(profile):.5f} kWh/m²')

if __name__=='__main__': main()
