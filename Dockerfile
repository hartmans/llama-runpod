FROM docker.io/runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04
RUN apt update&&apt install -y git-lfs && rm -rf /var/lib/apt/lists/*.
RUN pip install runpod

WORKDIR /workspace

COPY /workspace /workspace


#ENV CUDA_DOCKER_ARCH=all
ENV GGML_CUDA=1
RUN CMAKE_ARGS="-DGGML_CUDA=on" FORCE_CMAKE=1 pip install llama-cpp-python

# for local test
# RUN pip install llama-cpp-python==0.1.78

CMD ["/bin/bash"]

ADD handler.sh /handler.sh
CMD ["/handler.sh"]
