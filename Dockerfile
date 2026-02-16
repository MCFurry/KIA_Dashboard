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

# Temp fix for Kia EU, see: https://github.com/Hyundai-Kia-Connect/kia_uvo/discussions/1285
RUN curl -o /usr/local/lib/python3.13/site-packages/hyundai_kia_connect_api/KiaUvoApiEU.py \
    https://gist.githubusercontent.com/marvinwankersteen/af92c571881ac76579a037fac4f3a63a/raw/1d50e14daccb4638a82363254c3cc8a614026206/KiaUvoApiEU.py

COPY KIA_Dashboard.py /KIA_Dashboard.py
CMD ["python3", "KIA_Dashboard.py"]
