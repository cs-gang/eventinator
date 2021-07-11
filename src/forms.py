from sanic_wtf import SanicForm
from wtforms import DateField, StringField, SubmitField
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
    passcode = StringField("Passcode")
    starttime = DateField("Start Time", validators=[DataRequired()], format="%Y-%m-%d")
    endtime = DateField("End Time", validators=[DataRequired()], format="%Y-%m-%d")
    shortdescription = StringField("Short Description", validators=[DataRequired()])
    longdescription = StringField("Long Description", validators=[DataRequired()])
    submit = SubmitField("Submit")


class DashboardForm(SanicForm):
    timezone = StringField("Timezone", validators=[DataRequired()])


class EventActionForm(SanicForm):
    """
    Form to:
        1) Leave an event
        2) Join an event
        3) Delete an event
    """

    event_id = StringField("Event", validators=[DataRequired()])
