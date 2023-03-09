from flask_restx import Namespace, Resource, fields
from src.server.extensions import db
from src.models.models import Streams
import datetime

api = Namespace(
    name="streams", description="Individual records of a track being played"
)

streams_marshal = api.model(
    name="Streams",
    model={
        "id": fields.Integer(
            required=True, attribute="id", description="the id of stream"
        ),
        "stream_date": fields.DateTime(
            required=True,
            attribute="stream_date",
            description="The datetime when a track was streamed in UTC",
        ),
        "ms_played": fields.Integer(
            required=True,
            attribute="ms_played",
            description="The amount of time a track was streamed for in milliseconds",
        ),
        "reason_start": fields.String(
            required=True,
            attribute="reason_start",
            description="The reason why a track started streamed",
        ),
        "reason_end": fields.String(
            required=True,
            attribute="reason_end",
            description="The reason why a track ended streaming",
        ),
        "shuffle": fields.Boolean(
            required=True,
            attribute="shuffle",
            description="If shuffle mode was used when streaming the track",
        ),
        "skipped": fields.String(
            required=True,
            attribute="skipped",
            description="If the user skipped to the next song",
        ),
    },
)


@api.route("/")
class StreamsResource(Resource):
    @api.doc("test doc decoration")
    @api.marshal_with(streams_marshal, as_list=True)
    def get(self):
        return db.session.query(Streams).all()

    @api.doc("create field")
    @api.marshal_with(streams_marshal)
    def post(self):
        stream = Streams(
            stream_date=datetime.datetime.now(),
            ms_played=1000,
            reason_start="start reason",
            reason_end="end reasonnnn",
            shuffle=False,
            skipped="maybe???",
        )
        db.session.add(stream)
        db.session.commit()
        return stream
