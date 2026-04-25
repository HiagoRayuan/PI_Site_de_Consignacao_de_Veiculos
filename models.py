from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Veiculo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    descricao = db.Column(db.Text)
    preco = db.Column(db.Float)
    imagem = db.Column(db.String(200))

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(100))
    data = db.Column(db.String(50))
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'))