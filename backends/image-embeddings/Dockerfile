FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 HF_HOME=/cache/huggingface
# CUDA 12.8 wheels include Blackwell kernels (RTX PRO 6000 / sm_120).
RUN pip install --no-cache-dir torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py encoder.py ./
EXPOSE 8010
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1", "--limit-concurrency", "8"]
