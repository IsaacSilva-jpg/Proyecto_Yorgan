# LOGIN
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length
# ____________________________________________________________

# CLASE DEFINICION DEL LOGIN // Clase heredada de una clase padre
class LoginForm(FlaskForm):
    # Definimos uno por uno los campos del formulario

    # Las variables contienen los datos del formulario y son llamadas con el mismo nombre
    # Gmail equivale a la etiqueta "label" el usuario verá en el navegador
    # validators -> lista de reglas
    # "Email" -> Valida que lo escrito tenga un formato de correo electrónico real
    # "message" contiene los mensajes de error que se mostraran al usuario  
    correo = StringField("Gmail", validators=[DataRequired(message="Campo obligatorio"), Email(message="Introduce un correo valido", allow_smtputf8=False)])
    password = PasswordField("Contraseña", validators=[DataRequired(message="Campo obligatorio"), Length(8, 15, message="Contraseña no valida")])
    recuerdame = BooleanField("Mantener sesion iniciada")
    
    submit = SubmitField("Ingresar")

class RegisterForm(FlaskForm):

    correo = StringField("Gmail", validators=[DataRequired(message="Campo obligatorio"), Email(message="Introduce un correo valido", allow_smtputf8=False)])
    password = PasswordField("Contraseña", validators=[DataRequired(message="Campo obligatorio"), Length(8, 15, message="Contraseña no valida")])
    confirm_password = PasswordField("Contraseña", validators=[DataRequired(message="Campo obligatorio"), Length(8, 15, message="Contraseña no valida")])

class ReenviarForm(FlaskForm):

    correo= StringField("Gmail", validators=[DataRequired(message="Campo obligatorio"), Email(message="Introducde un correo valido", allow_smtputf8=False)])
    submit= SubmitField("Reenviar")

class NuevaContra(FlaskForm):

    password = PasswordField("Nueva contraseña", validators=[DataRequired(message="Campo obligatorio"), Length(8, 15, message="Contraseña no valida")])
    confirm_password = PasswordField("Confirma nueva contraseña", validators=[DataRequired(message="Campo obligatorio"), Length(8, 15, message="Contraseña no valida")])

class Soporte(FlaskForm):

    nombre= StringField("Nombre", validators=[DataRequired(message="Escribe tu nombre")])
    correo= StringField("Gmail",validators=[DataRequired(message="Campo obligatorio"), Email(message="Escribe tu correo", allow_smtputf8=False)])
    mensaje= TextAreaField("Mensaje", validators=[DataRequired(message="Campo obligatorio")])
    opcion= SelectField("Elije el tipo de reporte", choices=[("Buzon de sugerencias", "Sugerencias de mejora"), ("Reporte de fallas", "Reportar falla")], validators=[DataRequired(message="Selecciona el tipo de reporte")])

class CerrarSesion(FlaskForm):

    cerrar_sesion= SubmitField("cerrar sesion")