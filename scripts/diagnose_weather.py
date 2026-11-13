"""Opt-in, read-only network diagnosis. Never changes OS/DNS/TLS settings.

Compare this report on both demo machines at approximately the same time.
Candidate addresses are operator supplied or from explicitly requested public
DNS probes. They are temporary routes, never a bundled upstream IP list.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import ipaddress
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import ssl
import subprocess
import sys
import time
from urllib.parse import urlencode

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'backend'))
from app.forecast_models import ForecastLocation
from app.weather_forecast import FORECAST_URL, parse_forecast, local_day

FORECAST_HOST='api.open-meteo.com'


def verified_route_options(connect_ip=None):
    """Diagnostic only: retain HTTP Host, SNI and normal certificate checks."""
    if not connect_ip:
        return FORECAST_URL, {}, {}
    try:
        address=ipaddress.ip_address(connect_ip)
    except ValueError:
        raise ValueError('Candidate must be a public IP, not a URL or hostname') from None
    if not address.is_global:
        raise ValueError('Candidate must be globally routable')
    return str(httpx.URL(FORECAST_URL).copy_with(host=str(address))), {'Host':FORECAST_HOST}, {'sni_hostname':FORECAST_HOST}


def system_dns():
    try:
        return {'addresses':sorted({r[4][0] for r in socket.getaddrinfo(FORECAST_HOST,443,type=socket.SOCK_STREAM)})}
    except socket.gaierror as exc:
        return {'addresses':[],'error_type':type(exc).__name__,'error_code':exc.errno}


def public_dns(subnet=None):
    params={'name':FORECAST_HOST,'type':'A','edns_client_subnet':subnet or '0.0.0.0/0'}
    try:
        response=httpx.get('https://dns.google/resolve',params=params,timeout=5.)
        response.raise_for_status()
        body=response.json()
        if not isinstance(body,dict) or body.get('Status')!=0 or not isinstance(body.get('Answer',[]),list):
            raise ValueError('DNS lookup did not return a successful answer')
        records=[]
        for record in body.get('Answer',[]):
            if not isinstance(record,dict):
                raise ValueError('Unsupported DNS record')
            if record.get('type')==1 and record.get('name','').rstrip('.')==FORECAST_HOST:
                value=ipaddress.ip_address(record['data'])
                if value.is_global:
                    records.append({'address':str(value),'ttl_seconds':record.get('TTL')})
        return {'resolver':'Google Public DNS over HTTPS','client_subnet':params['edns_client_subnet'],
                'dns_status':body.get('Status'),'records':records}
    except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
        return {'resolver':'Google Public DNS over HTTPS','client_subnet':params['edns_client_subnet'],'error_type':type(exc).__name__,'records':[]}


def probe(location, timeout, connect_ip=None, trust_env=True, clock=None):
    params={'latitude':location.latitude,'longitude':location.longitude,
            'hourly':'shortwave_radiation,terrestrial_radiation','timezone':'auto',
            'timeformat':'unixtime','forecast_days':3}
    url,headers,extensions=verified_route_options(connect_ip)
    events=[]
    def trace(name,info):
        events.append({'event':name,**({'error_type':type(info['exception']).__name__} if 'exception' in info else {})})
    started=time.monotonic()
    result={'client':'httpx','connect_ip':connect_ip,'trust_env':trust_env,'tls_hostname':FORECAST_HOST,
            'certificate_verification':True,'validated_forecast':False}
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout,connect=timeout),trust_env=trust_env,follow_redirects=False) as client:
            response=client.get(url,params=params,headers={'User-Agent':'LifeLine-network-diagnostic/1.0',**headers},
                                extensions=extensions|{'trace':trace})
        result['http_status']=response.status_code
        if response.is_success:
            retrieved=(clock or (lambda:datetime.now(timezone.utc)))()
            series=parse_forecast(response.json(),location,retrieved,FORECAST_URL+'?'+urlencode(params))
            from zoneinfo import ZoneInfo
            today=retrieved.astimezone(ZoneInfo(series.timezone)).date()
            days=[local_day(series,today+timedelta(days=i)) for i in (0,1)]
            result.update(validated_forecast=True,timezone=series.timezone,
                planning_dates=[d.date.isoformat() for d in days],samples=len(series.times),
                source_url=series.source_url,retrieved_at=retrieved.isoformat())
    except Exception as exc:
        # No raw exception, request header, environment value, or credential is
        # included. Provider-data validation errors are distinct from transport.
        result['error_type']=type(exc).__name__
    result['seconds']=round(time.monotonic()-started,3)
    result['events']=events
    failed=[e['event'] for e in events if e['event'].endswith('.failed')]
    result['failed_stage']=('tls_handshake' if any('start_tls' in e for e in failed) else
                            'connect_tcp_or_dns' if any('connect_tcp' in e for e in failed) else
                            'http_or_forecast_validation' if result.get('error_type') or result.get('http_status',0)>=400 else None)
    return result


def native_curl(location,timeout):
    executable=shutil.which('curl')
    if not executable:
        return {'client':'native_curl','available':False}
    query=urlencode({'latitude':location.latitude,'longitude':location.longitude,
        'hourly':'shortwave_radiation,terrestrial_radiation','timezone':'auto','timeformat':'unixtime','forecast_days':3})
    output='{"http_status":"%{http_code}","remote_ip":"%{remote_ip}","tcp_seconds":%{time_connect},"tls_seconds":%{time_appconnect},"total_seconds":%{time_total}}'
    try:
        result=subprocess.run([executable,'--silent','--show-error','--connect-timeout',str(timeout),
            '--max-time',str(timeout+2),'--output',os.devnull,'--write-out',output,FORECAST_URL+'?'+query],
            capture_output=True,text=True,timeout=timeout+5)
        return {'client':'native_curl','exit_code':result.returncode,'measurements':json.loads(result.stdout)}
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        return {'client':'native_curl','error_type':type(exc).__name__}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--latitude',type=float,default=-.0917)
    parser.add_argument('--longitude',type=float,default=34.768)
    parser.add_argument('--timeout',type=float,default=5.)
    parser.add_argument('--candidate-ip',action='append',default=[],help='Current public API address to verify; can repeat. Does not edit DNS.')
    parser.add_argument('--public-dns',action='store_true',help='Read Google Public DNS using a zero-length client subnet.')
    parser.add_argument('--routing-subnet',action='append',default=[],help='Optional explicit public-prefix GeoDNS diagnostic only. Does not change forecast coordinates or OS settings.')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if not 0<args.timeout<=20:parser.error('Use a timeout greater than zero and at most 20 seconds')
    location=ForecastLocation(latitude=args.latitude,longitude=args.longitude)
    for address in args.candidate_ip:
        try:verified_route_options(address)
        except ValueError as exc:parser.error(str(exc))
    for subnet in args.routing_subnet:
        try:
            network=ipaddress.ip_network(subnet,strict=False)
            if network.prefixlen and not network.network_address.is_global:
                parser.error('Use a public diagnostic prefix, not a private network')
        except ValueError:parser.error('Routing subnet must be a valid public diagnostic prefix')
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'platform':platform.system(),
        'python':platform.python_version(),'openssl':ssl.OPENSSL_VERSION,'httpx':httpx.__version__,
        'location':location.model_dump(),'system_dns':system_dns(),
        'proxy_variables_present':{k:bool(os.environ.get(k)) for k in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy')},
        'scope':'Run from an ordinary terminal or an approved host context. Restricted-runner DNS failures do not establish a Mac/Windows defect. No OS settings, DNS cache, hosts file or certificate policy were changed.'}
    queries=[None] if args.public_dns else []
    queries+=args.routing_subnet
    dns_reports=[public_dns(s) for s in queries]
    report['public_dns']=dns_reports
    candidates=set(args.candidate_ip)
    candidates.update(r['address'] for d in dns_reports for r in d.get('records',[]))
    candidates.difference_update(report['system_dns']['addresses'])
    # Bound a single diagnosis; no scanning or arbitrary remote host support.
    candidates=sorted(candidates)[:4]
    with ThreadPoolExecutor(max_workers=4) as executor:
        normal=executor.submit(probe,location,args.timeout)
        no_proxy=executor.submit(probe,location,args.timeout,None,False)
        curl=executor.submit(native_curl,location,args.timeout)
        alternate=[executor.submit(probe,location,args.timeout,ip) for ip in candidates]
        report['probes']=[normal.result(),no_proxy.result(),curl.result()]+[f.result() for f in alternate]
    healthy=[p['connect_ip'] for p in report['probes'] if p.get('validated_forecast') and p.get('connect_ip')]
    report['verified_candidate_addresses']=healthy
    report['interpretation']=('Normal route failed during TLS while alternate routes fetched a validated forecast with the same hostname/certificate checks. This isolates the failure to the selected destination/network path, not a general Python or forecast-model incompatibility.'
        if report['probes'][0]['failed_stage']=='tls_handshake' and healthy else
        'Inspect the recorded stages and compare both machines at the same time; these measurements alone do not identify an ISP, firewall or operating-system cause.')
    report['limitations']=['Public DNS/addresses and availability change. Reverify a candidate before each temporary use; never hardcode it permanently.',
        'An alternate route does not identify who drops/stalls the original TLS handshake or which address another machine used.',
        'Exit success means at least one actual forecast was validated, not that the normal route is healthy.']
    text=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text,encoding='utf-8')
    print(text)
    return 0 if any(p.get('validated_forecast') for p in report['probes']) else 1


if __name__=='__main__':
    raise SystemExit(main())
