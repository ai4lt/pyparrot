FROM python:3.11

COPY requirements.txt ./
ARG KAFKA_PYTHON_VERSION=2.0.2
RUN python -c 'import os, pathlib, re; p=pathlib.Path("requirements.txt"); text=p.read_text(); pathlib.Path("/tmp/kafka-requirements.txt").write_text(re.sub(r"(?m)^kafka-python==[^\n]+$", "kafka-python==" + os.environ["KAFKA_PYTHON_VERSION"], text))'
RUN pip install --no-cache-dir -r /tmp/kafka-requirements.txt
COPY run.py ./

CMD python run.py

