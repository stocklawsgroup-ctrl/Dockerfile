FROM ubuntu:20.04

  ENV DEBIAN_FRONTEND=noninteractive

  RUN apt-get update && apt-get install -y \
      wget python3 python3-pip \
      libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
      libcups2 libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 libx11-6 \
      libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
      libgbm1 libpango-1.0-0 libcairo2 libasound2 \
      && apt-get clean && rm -rf /var/lib/apt/lists/*

  RUN wget -q https://github.com/tsl0922/ttyd/releases/download/1.7.4/ttyd.x86_64 -O /usr/local/bin/ttyd \
      && chmod +x /usr/local/bin/ttyd

  RUN pip3 install playwright
  RUN playwright install chromium
  RUN playwright install-deps chromium

  WORKDIR /app
  COPY . .

  CMD ["/bin/sh", "-c", "ttyd -p ${PORT:-10000} bash"]
