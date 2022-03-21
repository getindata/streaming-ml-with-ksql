import random
from datetime import datetime
from dataclasses import dataclass

import pandas as pd
import mlflow
import mlflow.spark
import mlflow.pyspark.ml
from mlflow.models.signature import infer_signature
from doge_datagen import (
    DataOnlineGenerator,
    Subject,
    Transition,
    SubjectFactory,
    EventSink,
)
import mleap.pyspark

from pyspark.sql import SparkSession
from pyspark.ml.feature import (
    VectorAssembler,
    StandardScaler,
    OneHotEncoder,
    StringIndexer,
    IndexToString,
)
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.classification import DecisionTreeClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.sql.functions import when, col

spark = (
    SparkSession.builder.config(
        "spark.jars.packages",
        "ml.combust.mleap:mleap-spark_2.12:0.19.0,org.mlflow:mlflow-spark:1.11.0",
    )
    .config("spark.jars.excludes", "net.sourceforge.f2j:arpack_combined_all")
    .getOrCreate()
)
sc = spark.sparkContext


@dataclass
class User:
    user_id: int

    def __hash__(self):
        return self.user_id


class UserFactory(SubjectFactory[User]):
    def __init__(self, starting_id=0):
        self.current_id = starting_id

    def create(self) -> User:
        user = User(self.current_id)
        self.current_id += 1
        return user


class PandasDataframeSink(EventSink):
    def __init__(self):
        self.rows = []

    def collect(self, timestamp: int, subject: Subject, transition: Transition):
        self.rows.append(
            {
                "timestamp": pd.Timestamp(timestamp, unit="ms"),
                **subject.__dict__,
                "trigger": transition.trigger,
                "from_state": transition.from_state,
                "to_state": transition.to_state,
            }
        )

    def get_df(self):
        return pd.DataFrame(self.rows)


def generate_users_activity(users_num, sink, start_user_id_at):
    user_activity = DataOnlineGenerator(
        ["main_page", "products_listing", "product_page", "product_gallery"],
        "main_page",
        UserFactory(start_user_id_at),
        subjects_num=users_num,
        tick_ms=1000,
        ticks_num=7200,
        timestamp_start=1000 * int(datetime(2022, 3, 15, 14).strftime("%s")),
    )
    user_activity.add_transition(
        "entered_product_listing_from_main_page",
        "main_page",
        "products_listing",
        0.8,
        event_sinks=[sink],
    )
    user_activity.add_transition(
        "entered_product_from_main_page",
        "main_page",
        "product_page",
        0.2,
        event_sinks=[sink],
    )
    user_activity.add_transition(
        "check_product_from_listing",
        "products_listing",
        "product_page",
        0.9,
        event_sinks=[sink],
    )
    user_activity.add_transition(
        "back_on_home_page_from_listing",
        "products_listing",
        "main_page",
        0.1,
        event_sinks=[sink],
    )

    user_activity.add_transition(
        "enter_product_gallery",
        "product_page",
        "product_gallery",
        0.4,
        event_sinks=[sink],
    )
    user_activity.add_transition(
        "continue_browsing_gallery",
        "product_gallery",
        "product_gallery",
        0.9,
        event_sinks=[sink],
    )
    user_activity.add_transition(
        "back_from_gallery_to_product_page",
        "product_gallery",
        "product_page",
        0.1,
        event_sinks=[sink],
    )

    user_activity.add_transition(
        "back_from_product_to_listing",
        "product_page",
        "products_listing",
        0.6,
        event_sinks=[sink],
    )

    user_activity.start()


def generate_bots_activity(bots_num, sink, start_user_id_at):
    bot_activity = DataOnlineGenerator(
        ["main_page", "products_listing", "product_page", "product_gallery"],
        "main_page",
        UserFactory(start_user_id_at),
        subjects_num=bots_num,
        tick_ms=1000,
        ticks_num=36000,
        timestamp_start=1000 * int(datetime(2022, 3, 15, 14).strftime("%s")),
    )
    bot_activity.add_transition(
        "entered_product_listing_from_main_page",
        "main_page",
        "products_listing",
        1,
        event_sinks=[sink],
    )
    bot_activity.add_transition(
        "check_product_from_listing",
        "products_listing",
        "product_page",
        0.95,
        event_sinks=[sink],
    )
    bot_activity.add_transition(
        "back_on_home_page_from_listing",
        "products_listing",
        "main_page",
        0.05,
        event_sinks=[sink],
    )

    bot_activity.add_transition(
        "enter_product_gallery",
        "product_page",
        "product_gallery",
        0.8,
        event_sinks=[sink],
    )
    bot_activity.add_transition(
        "continue_browsing_gallery",
        "product_gallery",
        "product_gallery",
        0.6,
        event_sinks=[sink],
    )
    bot_activity.add_transition(
        "back_from_gallery_to_product_page",
        "product_gallery",
        "product_page",
        0.4,
        event_sinks=[sink],
    )

    bot_activity.add_transition(
        "back_from_product_to_listing",
        "product_page",
        "products_listing",
        0.2,
        event_sinks=[sink],
    )

    bot_activity.start()


def generate_users_info(identifiers):
    users = pd.DataFrame(identifiers, columns=["id"])
    users["is_bot"] = users["id"] >= 1000000
    users["country"] = pd.Series(
        random.choices(["PL", "DE", "FR"], k=len(users)), index=users.index
    )
    users["platform"] = pd.Series(
        random.choices(
            ["Windows", "Linux", "Android", "iOS"], weights=[10, 1, 20, 4], k=len(users)
        ),
        index=users.index,
    )
    users["nb_orders"] = users.apply(
        lambda row: (random.randint(0, 1) if row["is_bot"] else random.randint(0, 10))
        if random.randint(0, 4) == 0
        else 0,
        axis=1,
    )
    return users


clickstream_sink = PandasDataframeSink()
generate_users_activity(1000, clickstream_sink, start_user_id_at=0)
generate_bots_activity(40, clickstream_sink, start_user_id_at=1000000)
generate_bots_activity(5, clickstream_sink, start_user_id_at=10000)  # noise
clickstream_logs = clickstream_sink.get_df()

clickstream_logs["product_views"] = (
    clickstream_logs["to_state"] == "product_page"
).astype(int)
clickstream_logs["listing_views"] = (
    clickstream_logs["to_state"] == "products_listing"
).astype(int)
clickstream_logs["gallery_views"] = (
    clickstream_logs["to_state"] == "product_gallery"
).astype(int)

clickstream_logs.drop(["from_state", "to_state", "trigger"], axis=1, inplace=True)

users = generate_users_info(clickstream_logs["user_id"].unique())


def count_actions_in_time_window(pdf):
    return (
        pdf.set_index("timestamp")
        .rolling("600s")
        .sum()
        .reset_index()
        .drop(["user_id"], axis=1)
    )


input_df = (
    clickstream_logs.groupby("user_id")
    .apply(count_actions_in_time_window)
    .reset_index()
    .drop("level_1", axis=1)
    .merge(users, left_on="user_id", right_on="id")
)


mlflow.spark.autolog()
#mlflow.pyspark.ml.autolog()
with mlflow.start_run():
    df = spark.createDataFrame(input_df).withColumn(
        "label", when(col("is_bot"), "bot").otherwise("user")
    ).withColumn('product_views', col('product_views').cast('int')
    ).withColumn('listing_views', col('listing_views').cast('int')
    ).withColumn('gallery_views', col('gallery_views').cast('int'))

    country_indexer = StringIndexer(inputCol="country", outputCol="country_idx")
    country_ohe = OneHotEncoder(inputCols=["country_idx"], outputCols=["country_ohe"])
    platform_indexer = StringIndexer(inputCol="platform", outputCol="platform_idx")
    platform_ohe = OneHotEncoder(
        inputCols=["platform_idx"], outputCols=["platform_ohe"]
    )
    assembler = VectorAssembler(
        inputCols=[
            country_ohe.getOutputCols()[0],
            platform_ohe.getOutputCols()[0],
            "product_views",
            "listing_views",
            "gallery_views",
            "nb_orders",
        ],
        outputCol="features",
    )

    label_indexer = StringIndexer(inputCol="label", outputCol="indexed_label").fit(df)
    dtc = DecisionTreeClassifier(labelCol="indexed_label", featuresCol="features")
    prediction_unindexer = IndexToString(
        inputCol="prediction", outputCol="predicted_label", labels=label_indexer.labels
    )

    (training_data, test_data) = df.randomSplit([0.7, 0.3])

    pipeline = Pipeline(
        stages=[
            country_indexer,
            country_ohe,
            platform_indexer,
            platform_ohe,
            assembler,
            label_indexer,
            dtc,
            prediction_unindexer,
        ]
    )

    grid = (
        ParamGridBuilder()
        .addGrid(dtc.maxDepth, [2, 3, 4])
        .addGrid(dtc.maxBins, [2, 4])
        .build()
    )

    evaluator = BinaryClassificationEvaluator(
        rawPredictionCol='prediction', labelCol="indexed_label"
    )
    cv = CrossValidator(
        estimator=pipeline, evaluator=evaluator, estimatorParamMaps=grid, numFolds=3
    )
    cvModel = cv.fit(training_data)

    test_metric = evaluator.evaluate(cvModel.transform(test_data))

    mlflow.log_metric("test_" + evaluator.getMetricName(), test_metric)

    model = pipeline.fit(training_data)
    results = model.transform(test_data)

    pred_model = PipelineModel(
        cvModel.bestModel.stages[:5] + cvModel.bestModel.stages[6:]
    )
    signature = infer_signature(
        training_data.select(
            "country",
            "platform",
            "product_views",
            "listing_views",
            "gallery_views",
            "nb_orders",
        ),
        results.select("predicted_label"),
    )

    mlflow.mleap.log_model(
        spark_model=pred_model,
        sample_input=test_data,
        artifact_path="mleap-model",
        signature=signature,
    )

    pred_model.serializeToBundle("jar:file:/tmp/bundle.zip", results)
    mlflow.log_artifact("/tmp/bundle.zip")

    print("Sample user:", results.where(results.predicted_label == 'user').first())
    print("Sample bot:", results.where(results.predicted_label == 'bot').first())
