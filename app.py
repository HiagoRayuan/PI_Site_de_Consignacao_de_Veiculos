from flask import Flask, render_template, request, redirect
from models import db, Veiculo, Agendamento

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    veiculos = Veiculo.query.all()
    return render_template('index.html', veiculos=veiculos)

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.methods == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = request.form['preco']
        imagem = request.form['imagem']

        caminho = f"static/uploads/{imagem.filename}"
        imagem.save(caminho)

        novo = Veiculo(
            nome = nome,
            descricao = descricao,
            preco = preco,
            imagem = imagem
        )

        db.session.add(novo)
        db.session.commit()

        return redirect('/')
    
    return render_template('cadastrar_veiculo.html')

@app.route('/veiculo/<int:id>', methods=['GET', 'POST'])
def veiculo(id):
    veiculo = Veiculo.query.get(id)

    if request.method == 'POST':
        nome_cliente = request.form['nome']
        data = request.form['data']

        agendamento = Agendamento(
            nome_cliente=nome_cliente,
            data=data,
            veiculo_id=id
        )

        db.session.add(agendamento)
        db.session.commit()

        return redirect('/')
    
    return render_template('veiculo.html', veiculo=veiculo)


@app.route('/agendamentos')
def agendamentos():
    agendamentos = Agendamento.query.all()
    return render_template('agendamentos.html', agendamentos=agendamentos)