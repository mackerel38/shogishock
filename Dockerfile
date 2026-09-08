FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash ca-certificates clang lld make git python3 python3-venv curl libarchive-tools && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY . .
RUN ./scripts/setup.sh
ENTRYPOINT ["surprise"]
