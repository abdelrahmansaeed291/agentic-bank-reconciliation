FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
ARG INSTALL_BEDROCK=false
COPY agent-service/requirements*.txt ./
RUN if [ "$INSTALL_BEDROCK" = "true" ]; then \
      pip install --no-cache-dir -r requirements-bedrock.txt; \
    else \
      pip install --no-cache-dir -r requirements.txt; \
    fi
COPY agent-service/app ./app
COPY policies ./policies
ENV POLICY_PATH=/app/policies/reconciliation_policy.md
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
