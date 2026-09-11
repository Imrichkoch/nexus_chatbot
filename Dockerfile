FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    NEXUS_DATABASE=/opt/nexuschat/data/nexus.sqlite3 \
    NEXUS_SYNTHETIC_DATABASE=/opt/nexuschat/data/synthetic-business.sqlite3 \
    NEXUS_INFRA_SNAPSHOT=/opt/nexuschat/data/infra-snapshot.json \
    NEXUS_LDAP_SECRET_PATH=/opt/nexuschat/data/ldap-bind-password \
    NEXUS_REGISTRATION_ENABLED=0 NEXUS_SECURE_COOKIES=1 NEXUS_BASE_PATH=""
WORKDIR /opt/nexuschat
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 nexuschat \
    && useradd --uid 10001 --gid 10001 --system --no-create-home nexuschat \
    && mkdir data && chown nexuschat:nexuschat data
COPY nexus ./nexus
USER 10001:10001
EXPOSE 8300
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8300/ready', timeout=3)"
CMD ["uvicorn", "nexus.app:app", "--host", "0.0.0.0", "--port", "8300", "--workers", "1", "--proxy-headers"]
