
from flask import Flask, jsonify, render_template, abort, request, url_for, redirect

# importamos la clase requerida
from datetime import timedelta

# MODULO PARA QUE SQL ACEPTE MI CONTRASEÑA
from urllib.parse import quote_plus

from extensions import limitador, mail, google, oauth, db, login_manager, logfire_flask, migrate

from auth import auth_bp

from services import cargar_usuario_login_manager

import logfire

from dotenv import load_dotenv
import os
from extensions import csrf
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.engine import URL

def crear_app():

    load_dotenv()

    # CREACION DEL OBJETO PRINCIPAL
    app = Flask(__name__)

    logfire.configure()


    logfire_flask.instrument_flask(app)

    csrf.init_app(app)

    app.wsgi_app = ProxyFix(app.wsgi_app,x_proto=1)



    # CARGANDO VARIABLES DE ENTORNO

    db_user= os.getenv("DB_USER")
    db_host= os.getenv("DB_HOST")
    db_name= os.getenv("DB_NAME")
    db_pass= os.getenv("SQLPASS")

    db_port = int(os.getenv("DB_PORT"))
    db_ca = os.getenv("DB_CA")



    flask_login_pass= os.getenv("FLASK_LOGIN_KEY")
    flask_mail_pass= os.getenv("FLASK_MAIL")

    mail_sender = os.getenv("MAIL_DEFAULT_SENDER")

    variables_criticas= [
        db_user, 
        db_host, 
        db_name, 
        db_pass, 
        flask_login_pass,
        flask_mail_pass,
        os.getenv("CLIENT_ID"),
        os.getenv("CLIENT_SECRET"),
        os.getenv("KEY_SERIALI"),
        os.getenv("GEMINI_API_KEY"),
        mail_sender,
        db_port,
        db_ca
    ]

    if not all(variables_criticas):
        raise KeyError("Error critico: faltan variables escenciales en .env")

    # ASIGNAMOS CONTRASEÑA
    #_______________
    # SQL_pass = db_pass
    # SQL_contra_escapada = quote_plus(SQL_pass)
    #_______________

    # CONFIGURACION DE LA BASE DE DATOS

    app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
        drivername="mysql+pymysql",
        username=db_user,
        password=db_pass,
        host=db_host,
        port=db_port,
        database=db_name
    )

    # app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{db_user}:{SQL_contra_escapada}@{db_host}/{db_name}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # CONECTAMOS EL db CON ESTA APP

    db.init_app(app)
    
    migrate.init_app(app, db)

    with app.app_context():
        logfire.instrument_sqlalchemy(engine=db.engine)

    # CONFIGURACIONES DE FLASK-LOGIN

    # aca estamos metiendo la clave directamente
    app.config["SECRET_KEY"] = flask_login_pass
    
    # aca estamos estableciendo el tiempo de vida de la sesión del 
    # usuario en exactamente 15 minutos

    # Para que esta configuración tenga efecto real, debes marcar la 
    # sesión como permanente dentro de la ruta (función) donde el 
    # usuario inicia sesión
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=900)
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)

    # limitacion del tamaño permitido para la subida de archivos de 
    # usuarios,  actúa a nivel de protocolo (HTTP) antes de que 
    # tu aplicación gaste recursos procesando el archivo.
    app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

    # CONFIGURACIONES DE SEGURIDAD DE COOKIES
    secure_cookies = os.getenv("SECURE_COOKIES", "false").lower() == "true"

    app.config.update(
        SESSION_COOKIE_SECURE=secure_cookies,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",

        REMEMBER_COOKIE_SECURE=secure_cookies,
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax"
    )

    app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

    # CONFIGURACION DE LAS CREDENCIALES DEL CORREO GMAIL (Flask-MAIL)
    app.config["MAIL_SERVER"] = 'smtp.gmail.com'
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config['MAIL_USE_SSL'] = False
    app.config["MAIL_USERNAME"] = mail_sender
    app.config["MAIL_PASSWORD"] = flask_mail_pass
    app.config['MAIL_DEFAULT_SENDER'] = mail_sender
    app.config["MAIL_ASCII_ATTACHMENTS"] = False

    # Establecemos a la pagina la cual será redirijida al usuario en caso de entrar
    # a un endpoint protegido
    login_manager.login_view = "auth.inicio_sesion"  # Nombre de la función de tu ruta de login

    # Decorador que se activa cuando flask necesite saber sobre el usuario actual
    @login_manager.user_loader
    # Funcion que recibe el ID
    def load_user(user_id):

        # Esa linea busca el usuario en la BD con la ID int, para que 
        # retorne el objeto del usuario para usar sus metodos
        return cargar_usuario_login_manager(user_id)


    # 2. Manejar solicitudes de usuarios no autenticados
    @login_manager.unauthorized_handler
    def manejar_sesion_no_autenticada():

        es_ajax = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
        )

        acepta_json = (
            "application/json" in request.headers.get("Accept", "")
        )

        if es_ajax or acepta_json:
            return jsonify({
                "autenticado": False,
                "error": "SESSION_EXPIRED",
                "message": "Tu sesión ha caducado. Inicia sesión nuevamente.",
                "login_url": url_for(
                    login_manager.login_view,
                    next=request.url
                )
            }), 401

        return redirect(
            url_for(login_manager.login_view, next=request.url)
        )

    # CONECTAMOS EL LIMITADOR CON ESTA APP
    limitador.init_app(app)

    # CONECTAMOS EL mail CON ESTA APP
    mail.init_app(app)

    # CONECTAMOS EL OBJETO oauth CON ESTA APP, PARA QUE EL OBJETO "google" funcione
    oauth.init_app(app)


    # Conecta el manejador con la aplicacion flask 
    login_manager.init_app(app)

    # Registras tus rutas
    app.register_blueprint(auth_bp)


    @app.errorhandler(429)
    def error_limite_excedido(e):
        return jsonify({
            "fail": "429",
            "error_details": e.description
        }),429

    @app.errorhandler(503)
    def error_nodisponible(e):
        return jsonify({
            "fail": "ERROR 503",
            "error_details":"La IA esta teniendo mucha demanda, intente mas tarde"
        }),503

    @app.errorhandler(404)
    def recurso_no_encotrado(e):
        return render_template("manejo_errores.html", error = "recurso_no_encotrado"),404


    @app.errorhandler(405)
    def recurso_no_encotrado(e):
        return render_template("manejo_errores.html", error = "metodo_no_aceptado"),405


    @app.errorhandler(CSRFError)
    def manejar_error_csrf(e):
        return {
            "error": "csrf_error",
            "mensaje": e.description
        }, 400


    return app

if __name__ == "__main__":

    app = crear_app()

    with app.app_context():
        db.create_all()    
    app.run(debug=True)

