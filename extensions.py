# ACA HACEMOS EL ARCHIVO PARA CREAR LOS OBJETOS SIN ASIGNARLE NINGUNA 
# APP DE FLASK AUN
from flask_sqlalchemy import SQLAlchemy

# Flask-limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address 

# FLASK-MAIL
from flask_mail import Mail

# libreria google OAuth
from authlib.integrations.flask_client import OAuth

# Flask-Login
from flask_login import LoginManager

import logfire

import os
from dotenv import load_dotenv

from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

csrf = CSRFProtect()

load_dotenv()

client_id_google= os.getenv("CLIENT_ID")
client_secret_key= os.getenv("CLIENT_SECRET")

logfire_flask= logfire

# Creamos el objeto db sin asignarle ninguna app todavía
db = SQLAlchemy()
migrate = Migrate()

limitador = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day"],
    storage_uri="memory://"
)

# OBJETO VACIO PARA ENVIAR CORREOS
mail = Mail()

# CONFIGURACION GOOGLE OAUTH

# DE ESTE PASAMOS TODA LA CONFIGURACION, LA INSTANCIA oauth NECESITA app, Y 
# LA INSTANCIA google, DEPENDE DE oauth, ASI QUE POR ESO MOVEMOS TODO PARA EL 
# TERCER ARCHIVO  
oauth = OAuth()

google = oauth.register(
    name='google',
    client_id= client_id_google,
    client_secret= client_secret_key,
    
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    api_base_url='https://openidconnect.googleapis.com/v1/',  
    server_metadata_url= "https://accounts.google.com/.well-known/openid-configuration",

    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Creacion del objeto vacio encargado de la logica de seguridad 
login_manager = LoginManager()