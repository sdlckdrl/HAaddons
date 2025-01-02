FROM python:slim-bookworm

ENV LANG C.UTF-8
ENV TZ=Asia/Seoul

# # Install tzdata for timezone support
# RUN apt-get update && apt-get install -y tzdata && \
#     cp /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
#     echo "Asia/Seoul" > /etc/timezone && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

# Install requirements for add-on
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    paho-mqtt==1.6.1 \
    PyYAML==6.0.1 \
    flask==2.3.3 \
    telnetlib3 \
    requests==2.31.0 \
    gevent \
    gevent-websocket

WORKDIR /share
# Copy data for add-on
COPY apps /apps

CMD ["python3", "/apps/main.py"]
