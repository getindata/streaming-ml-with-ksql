ARG IMAGE_VARIANT=slim-buster
ARG OPENJDK_VERSION=8
ARG PYTHON_VERSION=3.8

FROM python:${PYTHON_VERSION}-${IMAGE_VARIANT} AS py3
FROM openjdk:${OPENJDK_VERSION}-${IMAGE_VARIANT}

COPY --from=py3 / /

# download pyspark
ARG PYSPARK_VERSION=3.0.2
RUN pip --no-cache-dir install pyspark==${PYSPARK_VERSION}

# other packages used for training
RUN pip --no-cache-dir install boto3 mlflow-skinny doge-datagen pandas scipy mleap

ENV GIT_PYTHON_REFRESH quiet
ENV MLFLOW_S3_ENDPOINT_URL http://minio:9000
ENV MLFLOW_TRACKING_URI http://mlflow:8080
ENV AWS_ACCESS_KEY_ID minioadmin
ENV AWS_SECRET_ACCESS_KEY minioadmin

# pre-fetch extra spark packages
RUN python -c "from pyspark.sql import SparkSession; SparkSession.builder.config('spark.jars.packages', 'ml.combust.mleap:mleap-spark_2.12:0.19.0,org.mlflow:mlflow-spark:1.11.0').config('spark.jars.excludes', 'net.sourceforge.f2j:arpack_combined_all').getOrCreate()"

COPY train.py /

ENTRYPOINT ["python", "/train.py"]
