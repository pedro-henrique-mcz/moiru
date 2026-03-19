FROM python:3.12-slim
WORKDIR /usr/src/app

RUN groupadd -r app && useradd -r -g app umj

COPY --chown=appuser:umj requirements.txt ./

RUN apt-get update && apt-get install -y \
	gcc \
	pkg-config \
	libcairo2-dev \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=umj:app src ./src

EXPOSE 8000

USER umj

WORKDIR src

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]   





