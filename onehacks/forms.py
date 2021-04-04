from sanic_wtf import SanicForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


class LoginForm(SanicForm):
    email = StringField("Email", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


class SignInForm(SanicForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")
