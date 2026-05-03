from flask import Flask, render_template, request, redirect, session, flash
from models import db, Veiculo, Agendamento, Usuario, Foto
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '123456'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)

with app.app_context():
    db.create_all()

    admin = Usuario.query.filter_by(email='admin@email.com').first()

    if not admin:
        admin = Usuario(
            nome='Administrador',
            email='admin@email.com',
            telefone='999999999',
            senha=generate_password_hash('123'),
            is_admin=True
        )

        db.session.add(admin)
        db.session.commit()

@app.template_filter('moeda')
def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",","X").replace(".",",").replace("X",".")

@app.template_filter('formatar_data')
def formatar_data(data):
    data_obj = datetime.strptime(data, '%Y-%m-%d')
    return data_obj.strftime('%d/%m/%Y')

@app.route('/')
def home():
    usuario = None
    if session.get('usuario_id'):
        usuario = Usuario.query.get(session['usuario_id'])
    veiculos = Veiculo.query.all()
    return render_template('index.html', veiculos=veiculos, usuario=usuario)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        senha = request.form['senha']
        senha_hash = generate_password_hash(senha)
        confirmar_senha = request.form['confirmar_senha']

        #Validação
        if senha != confirmar_senha:
            flash('As senhas não coincidem', 'erro')
            return redirect('/registro')

        #Email já existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash('Email já cadastrado', 'erro')
            return redirect('/registro')
        
        senha_hash = generate_password_hash(senha)

        usuario = Usuario(nome=nome, email=email, telefone=telefone, senha=senha_hash)
    
        db.session.add(usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso!', 'sucesso')
        return redirect('/login')
    
    return render_template('registro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            session['is_admin'] = usuario.is_admin
            return redirect('/')
        else:
            flash('Email ou senha incorretos', 'erro')
        
    return render_template('login.html')
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect('/')
    
    total_veiculos = Veiculo.query.count()
    total_agendamentos = Agendamento.query.count()
    total_usuarios = Usuario.query.count()

    return render_template(
        'admin/dashboard.html',
        veiculos = total_veiculos,
        agendamentos = total_agendamentos,
        usuarios = total_usuarios
    )

@app.route('/admin/veiculos')
def admin_veiculos():
    if not session.get('is_admin'):
        return redirect('/')
    
    veiculos = Veiculo.query.all()
    return render_template('admin/veiculos.html', veiculos=veiculos)

@app.route('/admin/excluir/<int:id>', methods=['POST'])
def excluir_veiculo(id):
    if not session.get('is_admin'):
        return redirect('/')
    
    veiculo = Veiculo.query.get(id)

    db.session.delete(veiculo)
    db.session.commit()

    return redirect('/admin/veiculos')

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    
    if not session.get('is_admin'):
        return "Acesso negado"
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = request.form['preco']

        imagem_principal = request.files['imagem']
        caminho_principal = f"static/uploads/{imagem_principal.filename}"
        imagem_principal.save(caminho_principal)

        novo = Veiculo(
            nome = nome,
            descricao = descricao,
            preco = preco,
            imagem = caminho_principal
        )

        db.session.add(novo)
        db.session.commit()

        #Salvar imagens extras
        imagens = request.files.getlist('imagens')

        for img in imagens:
            if img.filename != "":
                import uuid
                nome_arquivo = f"{uuid.uuid4()}_{img.filename}"
                caminho = f"static/uploads/{nome_arquivo}"
                img.save(caminho)

                foto = Foto(
                    caminho = caminho,
                    veiculo_id = novo.id
                )
                db.session.add(foto)
        db.session.commit()

        flash('Veículo cadastrado com sucesso!', 'sucesso')
        return redirect('/admin/veiculos')
    
    return render_template('cadastrar_veiculo.html')

@app.route('/veiculo/<int:id>', methods=['GET', 'POST'])
def veiculo(id):

    if not session.get('usuario_id'):
        return redirect('/login')

    veiculo = Veiculo.query.get(id)

    if request.method == 'POST':
        data = datetime.strptime(request.form['data'], '%Y-%m-%d')

        agendamento = Agendamento(
            usuario_id=session['usuario_id'],
            data=data,
            veiculo_id=id
        )

        db.session.add(agendamento)
        db.session.commit()

        return redirect('/')
    
    return render_template('veiculo.html', veiculo=veiculo)


@app.route('/agendamentos')
def agendamentos():
    if not session.get('usuario_id'):
        return redirect('/login')
    
    if session.get('is_admin'):
        agendamentos = Agendamento.query.all()
    else:
        agendamentos = Agendamento.query.filter_by(usuario_id=session['usuario_id']).all()

    return render_template('agendamentos.html', agendamentos=agendamentos)

if __name__ == '__main__':
    app.run(debug=True)