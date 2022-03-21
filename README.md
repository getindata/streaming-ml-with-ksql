# Streaming-ML with KSQL

A proof-of-concept of a MLOps system that doesn't require coding skills (other then SQL) to apply the ML model in production. Core components:

* [Mlflow](https://mlflow.org/) - used as the experiments tracker and model registry
* Models trained on generated sample data with [Spark MLLib](https://spark.apache.org/mllib/), serialized using [Mleap](https://github.com/combust/mleap)
* [Kafka Connect](https://kafka.apache.org/documentation/#connect) server to stream the inputs from database using CDC
* [KSQL](https://ksqldb.io/) User Defined Function (UDF) that downloads the model and runs the predictions
* random data generator for demo purposes

## How to run it?

1. Compile the KSQL UDF, by entering `udf` directory and executing: (TODO - automate it)

        ./gradlew download 
        ./gradlew build

1. Enter the main directory and run `docker-compose up -d` in order to start all the services. 
1. Navigate to `http://localhost:8080` and confirm that training process started
1. Once training is finished, register the model as `Bot Detector`
1. TODO
