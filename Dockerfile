FROM python:latest
WORKDIR /home/
COPY ./requirements.txt ./
COPY ./re_crawler/ ./re_crawler/
COPY ./scrapy.cfg ./scrapy.cfg
COPY ./entrypoint.sh ./entrypoint.sh
RUN mkdir ./data && python -m pip install -r ./requirements.txt 
ENTRYPOINT ["./entrypoint.sh"]