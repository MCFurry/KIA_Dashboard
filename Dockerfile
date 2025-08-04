FROM python
RUN pip install dash dash-auth dash-daq flask requests pandas hyundai-kia-connect-api influxdb-client
COPY KIA_Dashboard.py /KIA_Dashboard.py
CMD python3 KIA_Dashboard.py