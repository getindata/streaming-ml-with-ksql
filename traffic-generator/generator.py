import random
import socket
import struct
from datetime import datetime
from dataclasses import dataclass

from doge_datagen import (
    DataOnlineGenerator,
    Subject,
    Transition,
    SubjectFactory,
    EventSink,
    KafkaAvroSinkFactory,
)
import pymysql.cursors


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


key_schema = """
{
  "type": "record",
  "name": "Key",
  "fields": [
    { "name":  "user_id", "type":  "string"}
  ]
}
"""

value_schema = """
{
  "type": "record",
  "name": "Value",
  "fields": [
    { "name":  "user_id", "type":  "string"},
    { "name":  "ts", "type":  "long"},
    { "name":  "event", "type":  "string"}
  ]
}
"""


def create_user():
    connection = pymysql.connect(
        host="mysql",
        user="root",
        password="kafkademo",
        database="demo",
        cursorclass=pymysql.cursors.DictCursor,
    )

    user_id = random.randint(4000, 5000)

    with connection:
        with connection.cursor() as cursor:
            sql = "INSERT INTO `users` (`id`, `name`, `platform`, `country`, `ip_address`, `nb_orders`) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(
                sql,
                (
                    user_id,
                    f"User_{user_id}",
                    random.choice(["Windows", "Linux", "Android", "iOS"]),
                    random.choice(["PL", "DE", "FR"]),
                    socket.inet_ntoa(struct.pack(">I", random.randint(1, 0xFFFFFFFF))),
                    0,
                ),
            )

        connection.commit()
    return user_id


if __name__ == "__main__":
    user_id = create_user()
    print("Created user", user_id)

    sink = KafkaAvroSinkFactory(
        bootstrap_servers=["kafka:9092"],
        schema_registry_url="http://schema-registry:8081",
        client_id="traffic-generator",
    ).create(
        topic="events",
        key_function=lambda subject, transition: {"user_id": str(subject.user_id)},
        key_schema=key_schema,
        value_function=lambda ts, subject, transition: {
            "user_id": str(subject.user_id),
            "ts": ts,
            "event": transition.to_state,
        },
        value_schema=value_schema,
    )

    generate_users_activity(1, sink, user_id)
