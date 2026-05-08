from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length


class ReverterForm(FlaskForm):
    chassi = StringField('Chassi', validators=[DataRequired()])
    motivo = TextAreaField('Motivo (≥3 chars)', validators=[
        DataRequired(), Length(min=3, max=500),
    ])
