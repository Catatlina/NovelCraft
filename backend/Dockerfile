# Multi-stage build: reduce image size, no build tools in final image
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 用虚拟环境而不是 `pip install --user`：后者会把包装进 /root/.local，
# 而 /root 目录默认权限是 700(只有 root 能进)。最终镜像里切换到非 root
# 的 appuser 运行时，会因为连 /root 都进不去而 "Permission denied"，
# 容器启动即崩溃退出——这是导致"后端未运行"的根因，已用真实用户权限
# 模拟复现过。虚拟环境装在 /opt/venv，是一个和 /root 无关的中性路径，
# chown 给 appuser 之后可以被正常访问。
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy only app code (not .env / tests / dev files)
# schemas.py 已移入 app/ 包内 (P0-0 修复)，随下面这行一起被复制，不再需要单独 COPY
COPY app/ app/
COPY migrations/ migrations/
COPY main.py schema_v8.sql apply_migrations.py ./

# Ensure __init__.py files exist for Python package resolution
RUN mkdir -p app/api app/services app/tasks app/core app/ws app/db && \
    touch app/__init__.py app/api/__init__.py app/services/__init__.py \
          app/tasks/__init__.py app/core/__init__.py app/ws/__init__.py app/db/__init__.py

# Non-root user — /opt/venv 也要 chown，否则 appuser 无法执行虚拟环境里的可执行文件/导入其中的包
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /opt/venv
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

EXPOSE 8100

CMD ["sh", "-c", "python apply_migrations.py && uvicorn main:app --host 0.0.0.0 --port 8100"]
