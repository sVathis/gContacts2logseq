FROM python:3.12-slim

RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gContacts2logseq.py .

# /secrets: token.json + credentials.json (mounted read-only or read-write)
# /contacts: Logseq contacts output directory (mounted read-write)
RUN mkdir /secrets /contacts && chown appuser:appuser /secrets /contacts

USER appuser

CMD ["python", "gContacts2logseq.py"]
