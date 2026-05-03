from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    senha = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    is_admin = db.Column(db.Boolean, default=False)

class Veiculo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    descricao = db.Column(db.Text)
    preco = db.Column(db.Float)
    imagem = db.Column(db.String(200))

class Foto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caminho = db.Column(db.String(200))
    
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'))
    veiculo = db.relationship('Veiculo', backref='fotos')

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(50))

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'))

    usuario = db.relationship('Usuario')
    veiculo = db.relationship('Veiculo')