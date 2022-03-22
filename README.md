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
1. Once training is finished, register the model as `Bot Detector` and promote it to `Production`
1. Create a Kafka Connect sink to stream MySQL data into Kafka

        http :8083/connectors @infra/connect/mysql-source.json

1. Then, in KSQL CLI (`docker exec -ti ksql ksql`) setup the users changes stream with the table:

        CREATE STREAM users_stream WITH (KAFKA_TOPIC = 'mysql.demo.users', VALUE_FORMAT = 'AVRO');
        CREATE STREAM users_stream_rekey AS SELECT * FROM users_stream PARTITION BY id;
        CREATE TABLE users WITH (KAFKA_TOPIC = 'USERS_STREAM_REKEY', VALUE_FORMAT = 'AVRO');

1. You may want to add some records to MySQL (`docker exec -ti mysql mysql -pkafkademo demo`) and check the changes with `select * from users emit changes;`
1. Next, simulate some traffic:

        $ docker exec -ti traffic-generator bash
        python generator.py

1. Configured aggregated views on the data with 10-minutes hoping window (2-minutes slide):

        CREATE STREAM events WITH (KAFKA_TOPIC = 'events', VALUE_FORMAT = 'AVRO', TIMESTAMP='ts');

        CREATE TABLE events_in_10_minutes_window AS SELECT 
          user_id,
          TIMESTAMPTOSTRING(min(events.rowtime), 'HH:mm:ss') as window_start,
          TIMESTAMPTOSTRING(max(events.rowtime), 'HH:mm:ss') as window_end,
          SUM(CASE WHEN event = 'main_page' THEN 1 ELSE 0 END) AS main_page_views,
          SUM(CASE WHEN event = 'products_listing' THEN 1 ELSE 0 END) AS listing_views,
          SUM(CASE WHEN event = 'product_page' THEN 1 ELSE 0 END) AS product_views,
          SUM(CASE WHEN event = 'product_gallery' THEN 1 ELSE 0 END) AS gallery_views
        FROM events 
        WINDOW HOPPING (SIZE 10 MINUTES, ADVANCE BY 2 MINUTES) GROUP BY user_id;

        CREATE STREAM aggregated_events_stream WITH (KAFKA_TOPIC = 'EVENTS_IN_10_MINUTES_WINDOW', VALUE_FORMAT = 'AVRO');

1. Check input data for model:

        SELECT user_id, country, platform, product_views, listing_views, gallery_views, nb_orders FROM aggregated_events_stream
        LEFT JOIN users ON aggregated_events_stream.user_id = users.rowkey
        EMIT CHANGES;

1. Finally, pass the data through ML model trained in the earlier steps and push results back to Kafka:

        CREATE STREAM bot_detection_results AS
        SELECT
            user_id,
            ip_address,
            window_start,
            window_end,
            predict('Bot Detector', as_array(country, platform), as_array(product_views, listing_views, gallery_views, nb_orders)) AS prediction
        FROM aggregated_events_stream
        LEFT JOIN users ON aggregated_events_stream.user_id = users.rowkey;

1. Push the topic with predictions into MongoDB:

        http :8083/connectors @infra/connect/mongo-sink.json

1. Verify data in MongoDB:

        docker exec -ti mongo mongo
        > db.bot_detection_results.find()

## Resetting the state

In order to keep the trained models, but reset Kafka state as a demo preparation, run:

    docker-compose stop kafka schema-registry connect mysql ksql mongo
    docker-compose rm -f kafka mysql mongo
    docker-compose up -d
