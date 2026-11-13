"""Isolated optional investigation. No arbitrary Fo prompts or external actions.

Default: handshake, schemas, and read-only conversation listing (no transcripts).
--greeting: the single static no-action greeting authorized for the investigation.
Never prints keys, account titles, conversation ids, or user transcripts.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import httpx

URL='https://mcp.api.wajo.ai/fo'
GREETING='This is an isolated LifeLine read-only integration test. Do not perform external actions, call tools, access connected accounts, contact anyone, or change anything. Reply with only: LifeLine read-only connection verified.'


def local_key():
    key=os.environ.get('WAJO_API_KEY','')
    path=Path(__file__).resolve().parents[1]/'.env.local'
    if not key and path.exists():
        for line in path.read_text().splitlines():
            name,separator,value=line.partition('=')
            if name.strip()=='WAJO_API_KEY' and separator:
                key=value.strip().strip('"\'')
    if not key:
        raise SystemExit('Set WAJO_API_KEY in the server environment or ignored .env.local. Do not paste it into chat.')
    return key


def parse(response):
    if response.status_code!=200:
        raise SystemExit(f'Wajo HTTP {response.status_code}; no response body or credential displayed. No automatic retry.')
    if 'text/event-stream' in response.headers.get('content-type',''):
        return json.loads(next(line[5:].strip() for line in response.text.splitlines() if line.startswith('data:')))
    return response.json()


def structured(data):
    result=data.get('result',{})
    if result.get('isError') or 'error' in data:
        raise SystemExit('Wajo returned a tool/protocol error; no private response content displayed.')
    if 'structuredContent' in result:
        return result['structuredContent']
    for block in result.get('content',[]):
        if block.get('type')=='text':
            try:
                return json.loads(block['text'])
            except ValueError:
                pass
    raise SystemExit('Wajo returned an unsupported result shape.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--greeting',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    evidence={'checked_at':datetime.now(timezone.utc).isoformat(),'endpoint':URL,'checks':[]}
    with httpx.Client(timeout=50.,follow_redirects=False,headers={'X-API-Key':local_key(),'Accept':'application/json, text/event-stream'}) as client:
        def rpc(method,params):
            started=time.monotonic()
            data=parse(client.post(URL,json={'jsonrpc':'2.0','id':1,'method':method,'params':params}))
            evidence['checks'].append({'method':method,'seconds':round(time.monotonic()-started,3)})
            return data
        rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'lifeline-read-only-probe','version':'1.0'}})
        client.post(URL,json={'jsonrpc':'2.0','method':'notifications/initialized'})
        discovery=rpc('tools/list',{})['result']
        evidence['tools']=discovery['tools']
        listing=next(t for t in discovery['tools'] if t['name']=='list_fo_conversations')
        assert listing['annotations']['readOnlyHint'] is True
        structured(rpc('tools/call',{'name':'list_fo_conversations','arguments':{}}))
        evidence['read_only_listing_succeeded']=True
        evidence['private_transcripts_read']=False
        if args.greeting:
            data=structured(rpc('tools/call',{'name':'ask_fo','arguments':{'message':GREETING,'newConversation':True}}))
            # Retain only in process, never report or persist the internal handle.
            deadline=time.monotonic()+120
            while data.get('status')=='working' and time.monotonic()<deadline:
                print('Wajo is still working on the isolated greeting.',flush=True)
                data=structured(rpc('tools/call',{'name':'get_fo_reply','arguments':{'conversationId':data['conversationId'],'waitSeconds':20}}))
            evidence['greeting_status']=data.get('status')
            evidence['greeting_exact_match']=data.get('response','').strip()=='LifeLine read-only connection verified.'
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps({k:v for k,v in evidence.items() if k!='tools'},indent=2))


if __name__=='__main__':
    main()
