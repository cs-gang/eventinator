from sanic_wtf import SanicForm
from wtforms import StringField, SubmitField, DateTimeField
from wtforms.validators import DataRequired


class LoginForm(SanicForm):
    email = StringField("Email", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


class SignUpForm(SanicForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


class EventCreationForm(SanicForm):
    eventname = StringField("Name of the event", validators=[DataRequired()])
    passcode = StringField("Passcode", validators=[DataRequired()])
    starttime = DateTimeField(
        "Start Time", validators=[DataRequired()], format="%Y-%m-%dT%H:%M"
    )
    endtime = DateTimeField(
        "End Time", validators=[DataRequired()], format="%Y-%m-%dT%H:%M"
    )
    shortdescription = StringField("Short Description", validators=[DataRequired()])
    longdescription = StringField("Long Description", validators=[DataRequired()])
    submit = SubmitField("Submit")


class DashboardForm(SanicForm):
    timezone = StringField("Timezone", validators=[DataRequired()])
