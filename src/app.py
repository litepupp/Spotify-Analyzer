import datetime
from flask import Flask
from flask_restx import Resource, Api, reqparse
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
api = Api(app)
db = SQLAlchemy(app)


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    date_created = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, name, email):
        self.name = name
        self.email = email


parser = reqparse.RequestParser()
parser.add_argument("name", type=str, help="nameeeee")
parser.add_argument("email", type=str, help="emailllll")


@api.route("/api")
class HelloWorld(Resource):
    def get(self):
        return "test"

    @api.doc(parser=parser)
    def post(self):
        args = parser.parse_args()
        user = Users(args["name"], args["email"])
        db.session.add(user)
        db.commit()
        return {"name": args["name"], "email": args["email"]}


if __name__ == "__main__":
    app.run(debug=True)
