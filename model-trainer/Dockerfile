ARG IMAGE_VARIANT=slim-buster
ARG OPENJDK_VERSION=8
ARG PYTHON_VERSION=3.8

FROM python:${PYTHON_VERSION}-${IMAGE_VARIANT} AS py3
FROM openjdk:${OPENJDK_VERSION}-${IMAGE_VARIANT}

COPY --from=py3 / /

ARG PYSPARK_VERSION=3.0.2
RUN pip --no-cache-dir install pyspark==${PYSPARK_VERSION}

RUN pip --no-cache-dir install mlflow-skinny

RUN pip --no-cache-dir install doge-datagen

RUN pip --no-cache-dir install pandas 

#RUN pip --no-cache-dir install Cython

RUN pip --no-cache-dir install scipy

RUN pip --no-cache-dir install mleap

ENV GIT_PYTHON_REFRESH quiet
ENV MLFLOW_S3_ENDPOINT_URL http://minio:9000
ENV MLFLOW_TRACKING_URI http://mlflow:8080

RUN python -c "from pyspark.sql import SparkSession; SparkSession.builder.config('spark.jars.packages', 'ml.combust.mleap:mleap-spark_2.12:0.19.0,org.mlflow:mlflow-spark:1.11.0').config('spark.jars.excludes', 'net.sourceforge.f2j:arpack_combined_all').getOrCreate()"

RUN pip --no-cache-dir install boto3

ENV AWS_ACCESS_KEY_ID minioadmin
ENV AWS_SECRET_ACCESS_KEY minioadmin
COPY train.py /
ENTRYPOINT ["python", "/train.py"]
