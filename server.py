from flask import Flask, jsonify, request
from flask.views import MethodView
from model import Session, User, Advertisement
from schema import CreateUser, UpdateUser, VALIDATION_CLASS
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from config import Config

app = Flask("adv_app")

app.config.from_object(Config)

jwt = JWTManager(app)


class HttpError(Exception):
    def __init__(self, status_code: int, message: dict | list | str):
        self.status_code = status_code
        self.message = message


@app.errorhandler(HttpError)
def http_error_handler(error: HttpError):
    error_message = {"status": "error", "description": error.message}
    response = jsonify(error_message)
    response.status_code = error.status_code
    return response


def get_adv(session: Session, advertisement_id: int):
    adv = session.get(Advertisement, advertisement_id)
    if adv is None:
        raise HttpError(404, message="Advertisement doesn't exists")
    return adv


def get_user(session: Session, user_id: int):
    user = session.get(User, user_id)
    if user is None:
        raise HttpError(404, message="User doesn't exists")
    return user


def get_session():
    with Session() as session:
        return session


def get_jsonify_adv(adv):
    return jsonify(
        {
            "id": adv.id,
            "title": adv.title,
            "description": adv.description,
            "creation_date": adv.creation_date.isoformat(),
            "user_id": adv.user_id,
        }
    )


def get_jsonify_user(user):
    token = user.get_token()
    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "creation_time": user.creation_time.isoformat(),
            "token": token,
        }
    )


def check_permission_adv(adv):
    if adv.user_id != get_jwt_identity():
        raise HttpError(
            403, message="You don't have permission to edit this advertisement"
        )


def check_permission_user(user):
    if user.id != get_jwt_identity():
        raise HttpError(403, message="You don't have permission to edit this user")


def validate_json(json_data: dict, validation_model: VALIDATION_CLASS):
    try:
        model_obj = validation_model(**json_data)
        model_obj_dict = model_obj.dict()
    except ValidationError as error:
        raise HttpError(400, message=error.errors())
    return model_obj_dict


class AdvertisementView(MethodView):
    @jwt_required()
    def get(self, advertisement_id: int):
        session = get_session()
        adv = get_adv(session, advertisement_id)
        return get_jsonify_adv(adv)

    @jwt_required()
    def post(self):
        json_data = request.json
        session = get_session()
        adv = Advertisement(**json_data)
        adv.user_id = get_jwt_identity()
        session.add(adv)
        session.commit()
        return get_jsonify_adv(adv)

    @jwt_required()
    def patch(self, advertisement_id: int):
        json_data = request.json
        session = get_session()
        adv = get_adv(session, advertisement_id)
        check_permission_adv(adv)
        for field, value in json_data.items():
            setattr(adv, field, value)
            session.add(adv)
            session.commit()
            return get_jsonify_adv(adv)

    @jwt_required()
    def delete(self, advertisement_id: int):
        session = get_session()
        adv = get_adv(session, advertisement_id)
        check_permission_adv(adv)
        session.delete(adv)
        session.commit()
        return jsonify({"status": "success"})


class UserView(MethodView):
    @jwt_required()
    def get(self, user_id: int):
        session = get_session()
        user = get_user(session, user_id)
        return jsonify(
            {
                "id": user.id,
                "username": user.username,
                "creation_time": user.creation_time,
            }
        )

    @jwt_required()
    def patch(self, user_id: int):
        json_data = validate_json(request.json, UpdateUser)
        session = get_session()
        user = get_user(session, user_id)
        check_permission_user(user)
        for field, value in json_data.items():
            setattr(user, field, value)
            session.add(user)
            try:
                session.commit()
            except IntegrityError:
                raise HttpError(409, f'{json_data["username"]} is busy')
        return get_jsonify_user(user)

    @jwt_required()
    def delete(self, user_id: int):
        session = get_session()
        user = get_user(session, user_id)
        check_permission_user(user)
        session.delete(user)
        session.commit()
        return jsonify({"status": "success"})


app.add_url_rule(
    "/adv/<int:advertisement_id>",
    view_func=AdvertisementView.as_view("with_adv_id"),
    methods=["GET", "PATCH", "DELETE"],
)

app.add_url_rule(
    "/adv/", view_func=AdvertisementView.as_view("create_adv"), methods=["POST"]
)

app.add_url_rule(
    "/user/<int:user_id>",
    view_func=UserView.as_view("with_user_id"),
    methods=["GET", "PATCH", "DELETE"],
)

app.add_url_rule("/user/", view_func=UserView.as_view("create_user"), methods=["POST"])


@app.route("/register/", methods=["POST"])
def register():
    json_data = validate_json(request.json, CreateUser)
    user = User(**json_data)
    session = get_session()
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        raise HttpError(409, f'{json_data["username"]} is busy')
    token = user.get_token()
    return get_jsonify_user(user)


@app.route("/login/", methods=["POST"])
def login():
    params = request.json
    user = User.authenticate(**params)
    token = user.get_token
    return get_jsonify_user(user)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
