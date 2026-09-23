FROM python:3.11-slim

WORKDIR /app

# The portal (src/web/studio_server.py), the MCP/reasoning engine and the
# pipeline all run on the Python standard library only, so no pip install step
# is required. requirements.txt stays in the repo for the optional BigQuery /
# Gemini notebook integrations, which are not part of this container.
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

EXPOSE 8080

CMD ["python3", "-m", "src.web.studio_server"]
