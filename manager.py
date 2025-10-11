#!/usr/bin/env python
import asyncio
import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
import boto3
import s3transfer
import sh
import requests


initialized = False
shutdown = False

app = FastAPI()

@app.get('/ping')
async def ping():
    if shutdown:
        return Response(status_code=502)
    if not initialized:
        return Response(status_code=204)
    return {'status': 'healthy'}

def llama_done(*args):
    print('Llama server done')
    global shutdown
    shutdown = True
    
async def initialize():
    global initialized
    try:
        sh.llama_server('--jinja',
                        '--no-webui',
                        '--port', os.environ['PORT'],
                        '--host', '0.0.0.0',
                        _done=llama_done,
                        _bg=True,
                        _out=sys.stdout,
                        _err_to_out=True,
                        )
        timeout = 2.0
        for i in range(10):
            try:
                await asyncio.to_thread(requests.post, f'http://127.0.0.1:{os.environ['PORT']}/completion',
                              json=dict(prompt="Tell me how it feels to be an AI.",
                                        n_predict=128))
                break
            except requests.exceptions.ConnectionError as e:
                print(e)
                await asyncio.sleep(timeout)
                timeout = timeout*2
                if timeout > 32: timeout = 32
                    
        initialized = True
    except Exception as e:
        asyncio.get_event_loop().call_soon(llama_done)
        raise

async def main():
    global main_loop
    main_loop = asyncio.get_event_loop()
    main_loop.create_task(initialize())
    config = uvicorn.Config(app,
                             port=int(os.environ['PORT_HEALTH']),
                             host='0.0.0.0',
                             )
    server = uvicorn.Server(config)
    server_task = main_loop.create_task(server.serve())
    while not shutdown:
        await asyncio.sleep(10)
    server_task.cancel()
    try: await server_task
    except BaseException: pass

if __name__ == '__main__':
    asyncio.run(main())
