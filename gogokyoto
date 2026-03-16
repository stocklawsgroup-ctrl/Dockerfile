FROM ubuntu:20.04

  ENV DEBIAN_FRONTEND=noninteractive

  RUN apt-get update && apt-get install -y \
      shellinabox \
      python3 python3-pip \
      libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
      libcups2 libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 libx11-6 \
      libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
      libgbm1 libpango-1.0-0 libcairo2 libasound2 \
      fonts-noto-cjk \
      && apt-get clean && rm -rf /var/lib/apt/lists/*

  RUN pip3 install playwright
  RUN playwright install chromium

  RUN echo 'root:root' | chpasswd

  WORKDIR /app

  CMD ["/bin/sh", "-c", "shellinaboxd --no-beep -t -p ${PORT:-10000} -s '/:root:root:/:bash'"]


