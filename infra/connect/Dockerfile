FROM confluentinc/cp-kafka-connect-base:7.0.1

RUN confluent-hub install --no-prompt debezium/debezium-connector-mysql:1.7.1 && \
    confluent-hub install --no-prompt mongodb/kafka-connect-mongodb:1.6.1
