from flask_restx import Namespace, Resource, fields
from src.server.extensions import db
from src.models.models import Streams

api = Namespace(
    name="streams", description="Individual records of a track being played"
)

streams_model = api.model(
    name="Streams",
    model={
        "id": fields.Integer(
            required=True, attribute="id", description="the id of stream"
        ),
        "track_id": fields.Integer(
            required=True,
            attribute="track_id",
            description="the id of track that was streamed",
        ),
        "album_id": fields.Integer(
            required=True,
            attribute="album_id",
            description="the id of album that was streamed",
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
        "ratio_played": fields.Float(
            required=True,
            attribute="ratio_played",
            description="The ratio of how much a track was streamed for 0.0 -> 1.0",
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
        "created_date": fields.DateTime(
            required=True,
            attribute="created_date",
            description="The datetime when this track track object was created in UTC",
        ),
        "modified_date": fields.DateTime(
            required=True,
            attribute="modified_date",
            description="The datetime when this track object was last modified in UTC",
        ),
    },
)

streams_page_model = api.model(
    name="StreamsPage",
    model={
        "page": fields.Integer(
            required=True,
            attribute="page",
            description="The current page this list of streams map to",
        ),
        "per_page": fields.Integer(
            required=True,
            attribute="per_page",
            description="The number of streams returned in this page",
        ),
        "items": fields.List(fields.Nested(streams_model)),
        "total": fields.Integer(
            required=True,
            attribute="total",
            description="The total number of streams that exist",
        ),
    },
)


@api.route("/")
class StreamsListResource(Resource):
    @api.marshal_with(streams_page_model)
    def get(self):
        return db.paginate(db.session.query(Streams), per_page=1000)


@api.route("/<int:stream_id>")
@api.param(name="stream_id", description="The id of a stream object")
class StreamsResource(Resource):
    @api.marshal_with(streams_model)
    def get(self, stream_id):
        stream = db.session.query(Streams).filter(Streams.id == stream_id).first()
        if stream:
            return stream
        else:
            return 404
