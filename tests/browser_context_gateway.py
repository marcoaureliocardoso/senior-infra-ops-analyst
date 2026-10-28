"""Owned offline Anthropic emulator; never forwards and never logs request data."""
from __future__ import annotations

import copy
import json
import secrets
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from browser_context_contract import STAGES, label, observation, offline_usage, stage_policy

MAX_BODY=1024*1024
READ_TIMEOUT=1


def strict_json(raw):
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError("duplicate")
            value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=unique,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError("nonfinite")))


def text(content):
    if type(content) is str:return content
    if type(content) is list:
        return "\n".join(b.get("text","") for b in content if type(b) is dict and b.get("type")=="text" and type(b.get("text")) is str)
    return ""


class Gateway:
    def __init__(self,nonce):
        self.nonce=label(nonce);self.lock=threading.RLock();self.server=None;self.thread=None
        self.stopped=True;self.port=0;self.stage=None;self.index=-1;self.before=None
        self.phase="new";self.tool_id=None;self.markers={};self.links={s:False for s in STAGES[1:]}
        self.generation=0;self.counts=0;self.stage_counts=dict.fromkeys(STAGES,0);self.fault="NONE"

    def fail(self,reason):
        if self.fault=="NONE":self.fault=reason

    def begin_stage(self,stage):
        with self.lock:
            if self.index+1>=4 or stage!=STAGES[self.index+1] or (self.index>=0 and self.phase!="done"):
                self.fail("STATE_UNPROVEN");raise ValueError("STATE_UNPROVEN")
            self.index+=1;self.stage=stage;self.before=None;self.phase="new";self.tool_id=None

    def arm(self,before):
        with self.lock:
            if self.before is not None or self.stage is None or self.fault!="NONE":raise ValueError("STATE_UNPROVEN")
            self.before=observation(before)

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(dict(fault=self.fault,generationAttempts=self.generation,countAttempts=self.counts,
                                      stageCounts=self.stage_counts,historyLinked=self.links))

    def __enter__(self):
        owner=self
        class Handler(BaseHTTPRequestHandler):
            protocol_version="HTTP/1.0"
            def log_message(self,*_):pass
            def setup(self):
                super().setup();self.connection.settimeout(READ_TIMEOUT)
            def send(self,status,body,content_type="application/json"):
                try:
                    self.send_response(status);self.send_header("Content-Type",content_type)
                    self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
                except (OSError,TimeoutError):
                    with owner.lock:owner.fail("STATE_UNPROVEN")
            def do_POST(self):
                path=self.path
                with owner.lock:
                    if path=="/v1/messages":owner.generation+=1
                    elif path=="/v1/messages/count_tokens":
                        owner.counts+=1
                        if owner.stage:owner.stage_counts[owner.stage]+=1
                    else:owner.fail("STATE_UNPROVEN")
                    if owner.generation>40 or owner.counts>192 or any(n>48 for n in owner.stage_counts.values()):owner.fail("BUDGET_INCONCLUSIVE")
                    if owner.fault!="NONE":self.send(409,b'{}');return
                try:
                    length=self.headers.get("Content-Length")
                    if self.headers.get("Transfer-Encoding") or not length or not length.isascii() or not length.isdigit():raise ValueError()
                    length=int(length)
                    if length>MAX_BODY:
                        with owner.lock:owner.fail("STATE_UNPROVEN")
                        self.send(413,b'{}');return
                    raw=self.rfile.read(length)
                    if len(raw)!=length:raise ValueError()
                    value=strict_json(raw)
                    if type(value) is not dict:raise ValueError()
                except (ValueError,UnicodeError,RecursionError,OSError,TimeoutError):
                    with owner.lock:owner.fail("STATE_UNPROVEN")
                    self.send(400,b'{}');return
                with owner.lock:
                    if owner.stage is None:owner.fail("STATE_UNPROVEN")
                    if path=="/v1/messages/count_tokens":
                        if type(value.get("messages")) is not list:owner.fail("STATE_UNPROVEN")
                        if owner.fault=="NONE":self.send(200,b'{"input_tokens":11}');return
                    elif path=="/v1/messages":
                        try:reply=owner.generate(value)
                        except (ValueError,KeyError,TypeError,RecursionError):owner.fail("STATE_UNPROVEN");reply=None
                        if owner.fault=="NONE" and reply is not None:
                            if value.get("stream") is True:self.send(200,sse(reply),"text/event-stream")
                            else:self.send(200,json.dumps(reply,separators=(",",":")).encode())
                            return
                    self.send(409,b'{}')
            def reject(self):
                with owner.lock:owner.fail("STATE_UNPROVEN")
                self.send(405,b'{}')
            do_GET=do_PUT=do_DELETE=do_PATCH=do_HEAD=do_OPTIONS=reject
        self.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        # A timed-out request is still evidence. Join bounded handlers before final snapshot/publication.
        self.server.daemon_threads=False;self.server.block_on_close=True
        self.port=self.server.server_address[1];self.stopped=False
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={"poll_interval":.02},daemon=True)
        self.thread.start();return self

    def __exit__(self,*_):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)
        self.stopped=not self.thread.is_alive();self.markers.clear();self.before=None
        if not self.stopped:self.fail("CLEANUP_INCONCLUSIVE")

    def generate(self,value):
        if self.before is None:self.fail("STATE_UNPROVEN");return None
        messages=value.get("messages")
        if type(messages) is not list or not messages or len(messages)>4096:raise ValueError()
        p=stage_policy(self.stage,self.nonce)
        top=any(type(m) is dict and m.get("role")=="user" and p["prompt"] in text(m.get("content")) for m in messages)
        child=(not top and self.stage=="subagent" and self.phase=="tool" and
               any(type(m) is dict and m.get("role")=="user" and "P004B_SUBAGENT_ACK" in text(m.get("content")) for m in messages))
        if not top and not child:self.fail("UNEXPECTED_TOOL");return None
        if child:
            # Foreground child generation is part of the same global HTTP budget.
            content=[{"type":"text","text":"P004B_SUBAGENT_ACK"}];stop="end_turn"
        else:
            if self.phase=="new" and self.index:
                marker=self.markers.get(STAGES[self.index-1])
                found=bool(marker) and any(type(m) is dict and m.get("role")=="assistant" and
                    marker in text(m.get("content")) for m in messages)
                if not found:self.fail("HISTORY_UNPROVEN");return None
                self.links[self.stage]=True
            if self.phase=="done":self.fail("STATE_UNPROVEN");return None
            tools=value.get("tools",[])
            if type(tools) is not list or len(tools)>4096:raise ValueError()
            names=[x.get("name") for x in tools if type(x) is dict]
            if self.phase=="new" and not (self.stage=="discovery" and "ToolSearch" not in names):
                if p["name"] not in names:self.fail("UNEXPECTED_TOOL");return None
                self.tool_id="tool_"+secrets.token_hex(12);self.phase="tool"
                content=[dict(type="tool_use",id=self.tool_id,name=p["name"],input=p["input"])];stop="tool_use"
            else:
                if self.phase=="tool":
                    results=[]
                    for m in messages:
                        if type(m) is dict and m.get("role")=="user" and type(m.get("content")) is list:
                            results.extend(b for b in m["content"] if type(b) is dict and b.get("type")=="tool_result" and b.get("tool_use_id")==self.tool_id)
                    if len(results)!=1 or results[0].get("is_error") not in (None,False):self.fail("STATE_UNPROVEN");return None
                self.phase="done";ack="P004B_"+self.stage.upper()+"_OK"
                if self.stage!="use":
                    marker="P004B_HISTORY_"+secrets.token_hex(24);self.markers[self.stage]=marker;ack+=" "+marker
                content=[dict(type="text",text=ack)];stop="end_turn"
        try:usage=offline_usage(self.before,self.generation)
        except ValueError:self.fail("CHALLENGE_UNAVAILABLE");return None
        return dict(id="msg_"+secrets.token_hex(12),type="message",role="assistant",model=value.get("model","synthetic"),
                    content=content,stop_reason=stop,stop_sequence=None,usage=usage)


def sse(reply):
    """One complete message; assembled stream usage equals the JSON reply."""
    events=[("message_start",dict(type="message_start",message={**reply,"content":[],"stop_reason":None,
            "usage":{**reply["usage"],"output_tokens":0}}))]
    for index,block in enumerate(reply["content"]):
        initial={**block}
        if block["type"]=="text":initial["text"]=""
        else:initial["input"]={}
        events.append(("content_block_start",dict(type="content_block_start",index=index,content_block=initial)))
        delta=(dict(type="text_delta",text=block["text"]) if block["type"]=="text" else
               dict(type="input_json_delta",partial_json=json.dumps(block["input"],separators=(",",":"))))
        events.append(("content_block_delta",dict(type="content_block_delta",index=index,delta=delta)))
        events.append(("content_block_stop",dict(type="content_block_stop",index=index)))
    events.extend([("message_delta",dict(type="message_delta",delta=dict(stop_reason=reply["stop_reason"],stop_sequence=None),usage={"output_tokens":10})),
                   ("message_stop",dict(type="message_stop"))])
    return "".join("event: "+kind+"\ndata: "+json.dumps(data,separators=(",",":"))+"\n\n" for kind,data in events).encode()
