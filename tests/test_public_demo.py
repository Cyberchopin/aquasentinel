from http.server import HTTPServer
from http.cookiejar import CookieJar
import json
import threading
import unittest
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import HTTPError
from aquasentinel.store import Store
from aquasentinel.server import make_handler
from aquasentinel.engine import now


class PublicTests(unittest.TestCase):
    def run_server(self, read_only=False):
        ready=threading.Event()
        def run():
            self.store=Store(':memory:')
            self.server=HTTPServer(('127.0.0.1',0),lambda *args: None)
            self.base=f'http://127.0.0.1:{self.server.server_port}'
            handler=make_handler(self.store,read_only=read_only,public_demo=not read_only,public_origin=self.base)
            handler.log_message=lambda *args:None
            self.server.RequestHandlerClass=handler
            ready.set();self.server.serve_forever(poll_interval=.01)
            self.server.server_close();self.store.close()
        t=threading.Thread(target=run);t.start();self.assertTrue(ready.wait(5))
        self.addCleanup(lambda:(self.server.shutdown(),t.join(5)))

    def call(self, client, path, data=None):
        r=Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,
            headers={'Content-Type':'application/json'})
        try:response=client.open(r,timeout=5)
        except HTTPError as e:response=e
        with response:return response.status,json.loads(response.read())

    def test_sessions_do_not_share_writes(self):
        self.run_server()
        a=build_opener(HTTPCookieProcessor(CookieJar()));b=build_opener(HTTPCookieProcessor(CookieJar()))
        record=dict(source_id='demo',external_id='1',stream_id='test',observed_at=now(),lat=34,lon=-118,signal='odor',synthetic=True)
        self.assertEqual(self.call(a,'/api/observations',record)[0],201)
        self.assertEqual(len(self.call(a,'/api/snapshot?stream=test')[1]['evidence']),1)
        self.assertEqual(len(self.call(b,'/api/snapshot?stream=test')[1]['evidence']),0)

    def test_readonly_rejects_write(self):
        self.run_server(True)
        self.assertEqual(self.call(build_opener(),'/api/observations',{})[0],403)

    def test_rate_limit(self):
        self.run_server()
        a=build_opener(HTTPCookieProcessor(CookieJar()))
        for _ in range(120):self.assertEqual(self.call(a,'/api/health')[0],200)
        self.assertEqual(self.call(a,'/api/health')[0],429)
