FROM python
RUN pip install \
    dash \
    dash-auth \
    dash-daq \
    flask \
    hyundai-kia-connect-api \
    influxdb-client \
    pandas \
    requests
COPY KIA_Dashboard.py /KIA_Dashboard.py
CMD ["python3", "KIA_Dashboard.py"]