
from extensions import db
from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from flask_login import UserMixin
from datetime import datetime

# UserMixin LO USA EL FLASK LOGIN, tenemos que meter flask login en 
# este archivo
# DEFINICION DE LA TABLA 
class Usuario(UserMixin, db.Model):

    __tablename__= "usuarios"

    # DEFINICION DE LAS COLUMNAS DE LA TABLA 
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=True)

    # Este diseño es escalable por que acepta cualquier string, pueden 
    # repetirse, pueden poner "google", "apple" y "github"
    auth_provider = db.Column(db.String(20), default= "local")
    estado = db.Column(db.String(20), nullable= False)
    imagen_google = db.Column(db.String(500), nullable= True)

    historiales= db.relationship("AnalisisCV", backref= "usuarios", lazy =True)

    def __repr__(self):
        return f"Usuario {self.email}"        
    
class AnalisisCV(db.Model):

    __tablename__ = "analisis"

    id= db.Column(db.Integer, primary_key= True)
    fecha_creacion= db.Column(db.DateTime, default= db.func.current_timestamp())
    resultado_ia = db.Column(db.Text, nullable= True)

    texto_cv= db.Column(db.Text, nullable= False)
    texto_vacante= db.Column(db.Text, nullable= False)

    usuario_id= db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable= False)

    def __repr__(self):
        return f"Resultado analisis {self.resultado_ia}"
    

class noticia(db.Model):

    __tablename__ = "noticia"

    id= db.Column(db.Integer, primary_key= True)
    slug= db.Column(db.String(150), unique=True, nullable= False)
    titulo= db.Column(db.String(255), nullable= False)
    contenido= db.Column(db.Text, nullable= False)
    fecha_publicacion= db.Column(db.DateTime, default= datetime.now)
    


