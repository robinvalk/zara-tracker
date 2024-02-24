FROM python:3.12-alpine

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /opt/scrapy/data

ENTRYPOINT [ "scrapy" ]
