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
        "streamDate": fields.DateTime(
            required=True,
            attribute="stream_date",
            description="The datetime when a track was streamed",
        ),
    },
)


@api.route("/")
class StreamsResource(Resource):
    @api.doc("Get all streams")
    @api.marshal_with(streams_marshal)
    def get(self):
        """
        dsd
        """
        return db.session.query(Streams).all()

    @api.doc("create field")
    def post(self):
        stream = Streams(stream_date=datetime.datetime(year=1999, month=12, day=1))
        db.session.add(stream)
        db.session.commit()
        return stream
