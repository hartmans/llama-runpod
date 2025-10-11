FROM docker.io/runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404 AS base
RUN apt update&&apt install -y git-lfs cmake s3cmd libcurl4-openssl-dev && rm -rf /var/lib/apt/lists/*.
RUN pip install runpod&&rm -rf /root/.cache




ENV GGML_CUDA=1
FROM base AS BUILD
RUN git clone https://github.com/ggml-org/llama.cpp
RUN cd llama.cpp &&cmake  -B build -DGGML_NATIVE=off -DGGML_CUDA=on -DCMAKE_EXE_LINKER_FLAGS=-Wl,--allow-shlib-undefined -DGGML_BACKEND_DL=ON -DGGML_CPU_ALL_VARIANTS=ON -DLLAMA_BUILD_TESTS=OFF .&& cmake --build build  --config release -j8 
RUN cd llama.cpp&&DESTDIR=/stage cmake --install build
RUN tar -cf /app.tar -C /stage .


FROM base
RUN --mount=type=bind,from=BUILD,src=/,dst=/build cd / &&tar xpf /build/app.tar
RUN ldconfig
ENV PORT=8080
ENV PORT_HEALTH=8081
RUN pip3 install --break-system-packages fastapi uvicorn sh
COPY manager.py /manager.py

ENV LLAMA_ARG_MODEL=/workspace/model.gguf
ENV LLAMA_ARG_CTX_SIZE=32767

CMD ["/manager.py"]


