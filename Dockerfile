FROM python:3.12-slim
RUN pip install \
    dash \
    dash-auth \
    dash-daq \
    flask \
    hyundai-kia-connect-api \
    influxdb-client \
    pandas \
    requests

COPY *.py ./

CMD ["python3", "KIA_Dashboard.py"]
