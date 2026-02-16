FROM python:3.12-slim
RUN pip install \
    dash \
    dash-auth \
    dash-daq \
    flask \
    hyundai-kia-connect-api \
    influxdb-client \
    pandas \
    pytz \
    requests

# Temp fix for Kia EU, see: https://github.com/Hyundai-Kia-Connect/kia_uvo/discussions/1285
RUN python3 -c "\
import urllib.request, site; \
path = site.getsitepackages()[0]; \
urllib.request.urlretrieve('https://gist.githubusercontent.com/marvinwankersteen/af92c571881ac76579a037fac4f3a63a/raw/1d50e14daccb4638a82363254c3cc8a614026206/KiaUvoApiEU.py', f'{path}/hyundai_kia_connect_api/KiaUvoApiEU.py'); \
print(f'Downloaded to {path}/hyundai_kia_connect_api/KiaUvoApiEU.py') \
"

COPY *.py ./

CMD ["python3", "KIA_Dashboard.py"]
