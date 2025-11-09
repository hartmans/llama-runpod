#!/usr/bin/env python
import asyncio
from pathlib import Path
import os
import re
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
    await s3_download()
    try:
        sh.llama_server('--jinja',
                        '--no-webui',
                        '-np', '4',
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
        else:
            raise RuntimeError('Failed to connect to llama server after retries')

        initialized = True
    except Exception as e:
        asyncio.get_event_loop().call_soon(llama_done)
        raise

async def s3_download():
    if not 'S3_MODEL_URL' in os.environ:
        return
    model = os.environ['LLAMA_ARG_MODEL']
    model_path = Path(model)
    if  model_path.exists(): return
    client = boto3.client('s3')
    if not (match := re.match(
            r's3://([^/]+)/(.*)$', os.environ['S3_MODEL_URL'])):
        raise RunnTimeError('Unable to parse s3 url')
    s3_bucket = match.group(1)
    s3_key = match.group(2)
    s3_transfer = s3transfer.S3Transfer(client)
    print('Downloading model from s3')
    await asyncio.to_thread(s3_transfer.download_file, s3_bucket, s3_key, os.environ['LLAMA_ARG_MODEL'])
    print("Model downloaded")
    
    
    
def initialize_status(future):
    if future.exception():
        global shutdown
        shutdown = True
        print("Initialization error: "+str(future.exception()))

async def main():
    global main_loop
    main_loop = asyncio.get_event_loop()
    main_loop.create_task(initialize()).add_done_callback(initialize_status)
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
