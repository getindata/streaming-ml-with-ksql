ARG IMAGE_VARIANT=slim-buster
ARG PYTHON_VERSION=3.8

FROM python:${PYTHON_VERSION}-${IMAGE_VARIANT} 

# other packages used for training
RUN pip --no-cache-dir install doge-datagen PyMySQL[rsa]

COPY generator.py /

ENTRYPOINT ["sh", "-c", "sleep infinity"]
