FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN echo 'exec zsh' > /root/.bashrc
RUN apt-get update && apt-get install -y --no-install-recommends curl dnsutils ipcalc iproute2 iputils-ping jq mtr-tiny nano netcat tcpdump termshark vim-nox zsh
RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc
RUN apt-get update && apt-get upgrade -y
RUN apt install rsync grsync -y
RUN apt install build-essential -y
RUN apt-get install manpages-dev
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
RUN . $HOME/.cargo/env
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install --version 0.11.3 -f routinator
RUN routinator init --accept-arin-rpa
RUN routinator -v vrps -o ROAs.csv
