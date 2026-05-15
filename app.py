from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from models import db, Veiculo, Agendamento, Usuario, Foto
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import uuid

load_dotenv()
print("EMAIL:", os.environ.get('MAIL_USERNAME'))
print("SENHA:", os.environ.get('MAIL_PASSWORD'))

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['WTF_CSRF_ENABLED'] = True
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Limita o upload para 16MB

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

db.init_app(app)

EXTENSOES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'webp', 'jfif'}
def arquivo_permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS


def limpar_agendamentos_passados():
    hoje = date.today().strftime('%Y-%m-%d')
    Agendamento.query.filter(Agendamento.data < hoje).delete()
    db.session.commit()


with app.app_context():
    db.create_all()
    limpar_agendamentos_passados()

    admin = Usuario.query.filter_by(email='admin@email.com').first()

    if not admin:
        admin = Usuario(
            nome='Administrador',
            email='admin@email.com',
            telefone='999999999',
            senha=generate_password_hash('123'),
            is_admin=True,
            confirmado=True
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
        usuario = db.session.get(Usuario, session['usuario_id'])

    busca = request.args.get('busca', '')
    if busca:
        veiculos = Veiculo.query.filter(
            Veiculo.nome.ilike(f'%{busca}%') |
            Veiculo.descricao.ilike(f'%{busca}%')
        ).all()
    else:
        veiculos = Veiculo.query.all()
    return render_template('index.html', veiculos=veiculos, usuario=usuario, busca=busca)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        senha = request.form['senha']
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

        # Envia email de confirmação
        token = serializer.dumps(email, salt='confirmacao-email')
        link = url_for('confirmar_email', token=token, _external=True)
        msg = Message('Confirme seu email', sender=os.environ.get('MAIL_USERNAME'), recipients=[email])
        msg.body = f'Olá {nome}! Clique no link para confirmar seu email: {link}'
        mail.send(msg)

        flash('Cadastro realizado! Verifique seu email para confirmar a conta.', 'sucesso')
        return redirect('/login')
    
    return render_template('registro.html')

@app.route('/confirmar/<token>')
def confirmar_email(token):
    try:
        email = serializer.loads(token, salt='confirmacao-email', max_age=3600)
    except:
        flash('Link de confirmação inválido ou expirado!', 'erro')
        return redirect('/login')
    
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario:
        usuario.confirmado = True
        db.session.commit()
        flash('Email confirmado com sucesso! Faça login.', 'sucesso')

    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.senha, senha):
            if not usuario.confirmado:
                flash('Confirme seu email antes de fazer login!', 'erro')
                return redirect('/login')
            session['usuario_id'] = usuario.id
            session['is_admin'] = usuario.is_admin
            session['usuario_nome'] = usuario.nome
            return redirect('/')
        else:
            flash('Email ou senha incorretos', 'erro')
        
    return render_template('login.html')

@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form['email']
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario:
            token = serializer.dumps(email, salt='recuperacao-senha')
            link = url_for('redefinir_senha', token=token, _external=True)

            msg = Message('Redefinição de senha', sender=os.environ.get('MAIL_USERNAME'), recipients=[email])
            msg.body = f'Olá {usuario.nome}! Clique no link para redefinir sua senha: {link}\n\nO link expira em 1 hora.'
            mail.send(msg)

        # Sempre mostra a mesma mensagem por segurança
        flash('Se este email estiver cadastrado, você receberá um link em breve.', 'sucesso')
        return redirect('/login')
    
    return render_template('esqueci_senha.html')

@app.route('/redefinir_senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    try:
        email = serializer.loads(token, salt='recuperacao-senha', max_age=3600)
    except:
        flash('Link inválido ou expirado!', 'erro')
        return redirect('/login')
    
    if request.method == 'POST':
        senha = request.form['senha']
        confirmar_senha = request.form['confirmar_senha']

        if senha != confirmar_senha:
            flash('As senhas não coincidem!', 'erro')
            return redirect(request.url)
        
        usuario = Usuario.query.filter_by(email=email).first()
        usuario.senha = generate_password_hash(senha)
        db.session.commit()

        flash('Senha redefinida com sucesso!', 'sucesso')
        return redirect('/login')
    
    return render_template('redefinir_senha.html')

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
    
    veiculo = db.session.get(Veiculo, id)
    db.session.delete(veiculo)
    db.session.commit()

    return redirect('/admin/veiculos')

@app.route('/admin/usuarios')
def admin_usuarios():
    if not session.get('is_admin'):
        return redirect('/')
    
    busca = request.args.get('busca', '')
    if busca:
        usuarios = Usuario.query.filter(
            Usuario.nome.ilike(f'%{busca}%') |
            Usuario.email.ilike(f'%{busca}%') 
        ).all()
    else:
        usuarios = Usuario.query.all()

    return render_template('admin/usuarios.html', usuarios=usuarios, busca=busca)

@app.route('/admin/usuarios/excluir/<int:id>', methods=['POST'])
def excluir_usuario(id):
    if not session.get('is_admin'):
        return redirect('/')
    
    usuario = db.session.get(Usuario, id)

    if usuario.is_admin:
        flash('Não é possível excluir um administrador!', 'erro')
        return redirect('/admin/usuarios')
    
    db.session.delete(usuario)
    db.session.commit()

    flash('Usuário excluído com sucesso!', 'sucesso')
    return redirect('/admin/usuarios')

@app.route('/admin/usuarios/toggle-admin/<int:id>', methods=['POST'])
def toggle_admin(id):
    if not session.get('is_admin'):
        return redirect('/')
    
    usuario = db.session.get(Usuario, id)

    if usuario.id == session['usuario_id']:
        flash('Você não pode alterar seu próprio status de admin!', 'erro')
        return redirect('/admin/usuarios')
    
    usuario.is_admin = not usuario.is_admin
    db.session.commit()

    flash('Permissões do usuário atualizadas!', 'sucesso')
    return redirect('/admin/usuarios')

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    
    if not session.get('is_admin'):
        return redirect('/')
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = request.form['preco']

        imagem_principal = request.files['imagem']

        if not arquivo_permitido(imagem_principal.filename):
            flash('Formato de imagem inválido. Use PNG, JPG ou WEBP', 'erro')
            return redirect('/cadastrar')

        nome_principal = f"{uuid.uuid4()}_{imagem_principal.filename}"
        caminho_principal = f"static/uploads/{nome_principal}"
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
                nome_arquivo = f"{uuid.uuid4()}_{img.filename}"
                caminho = f"static/uploads/{nome_arquivo}"
                img.save(caminho)
                foto = Foto(caminho = caminho, veiculo_id = novo.id)
                db.session.add(foto)
        db.session.commit()
        
        flash('Veículo cadastrado com sucesso!', 'sucesso')
        return redirect('/admin/veiculos')
    

    return render_template('cadastrar_veiculo.html')

@app.route('/veiculo/<int:id>', methods=['GET', 'POST'])
def veiculo(id):

    if not session.get('usuario_id'):
        return redirect('/login')

    veiculo = db.get_or_404(Veiculo, id)

    HORARIOS = ['09:00','09:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', 
                '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30', '17:00', '17:30']

    if request.method == 'POST':
        agendamento_existente = Agendamento.query.filter_by(
            usuario_id=session['usuario_id'],
            veiculo_id=id
        ).first()

        if agendamento_existente:
            flash('Você já possui uma visita agendada para este veículo!', 'erro')
            return redirect(f'/veiculo/{id}')
        
        data = request.form['data']
        horario = request.form['horario']

        data_obj = datetime.strptime(data, '%Y-%m-%d').date()

        if data_obj < date.today():
            flash('Não é possível agendar uma visita em uma data passada!', 'erro')
            return redirect(f'/veiculo/{id}')
        
        horario_ocupado = Agendamento.query.filter_by(
            veiculo_id = id,
            data=data,
            horario=horario
        ).first()

        if horario_ocupado:
            flash('Este horário já está reservado para esta data!', 'erro')
            return redirect(f'/veiculo/{id}')
        
        agendamento = Agendamento(
            usuario_id=session['usuario_id'],
            data=data,
            horario=horario,
            veiculo_id=id
        )
        db.session.add(agendamento)
        db.session.commit()

        flash('Agendamento realizado com sucesso!', 'sucesso')
        return redirect('/')
    
    agendamento_do_veiculo = Agendamento.query.filter_by(veiculo_id=id).all()
    ocupados = [f"{a.data}_{a.horario}" for a in agendamento_do_veiculo]
    
    return render_template('veiculo.html', veiculo=veiculo, horarios=HORARIOS, ocupados=ocupados)

@app.route('/agendamentos')
def agendamentos():
    if not session.get('usuario_id'):
        return redirect('/login')
    
    limpar_agendamentos_passados()
    
    if session.get('is_admin'):
        agendamentos = Agendamento.query.all()
    else:
        agendamentos = Agendamento.query.filter_by(usuario_id=session['usuario_id']).all()

    return render_template('agendamentos.html', agendamentos=agendamentos)

@app.route('/agendamentos/excluir/<int:id>', methods=['POST'])
def excluir_agendamento(id):
    if not session.get('usuario_id'):
        return redirect('/login')
    
    agendamento = db.get_or_404(Agendamento, id)
    # Verifica se o agendamento pertence ao usuário ou se é admin
    if agendamento.usuario_id != session['usuario_id'] and not session.get('is_admin'):
        flash('Acesso negado!', 'erro')
        return redirect('/agendamentos')
    
    db.session.delete(agendamento)
    db.session.commit()

    flash('Agendamento excluído com sucesso!', 'sucesso')
    return redirect('/agendamentos')

@app.route('/agendamentos/editar/<int:id>', methods=['GET', 'POST'])
def editar_agendamento(id):
    if not session.get('usuario_id'):
        return redirect('/login')
    
    agendamento = db.session.get(Agendamento, id)

    # Verifica se o agendamento pertence ao usuário
    if agendamento.usuario_id != session['usuario_id']:
        flash('Acesso negado!', 'erro')
        return redirect('/agendamentos')
    
    if request.method == 'POST':
        data = request.form['data']
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()

        if data_obj < date.today():
            flash('Não é possível agendar uma visita em uma data passada!', 'erro')
            return redirect(f'/agendamentos/editar/{id}')
        
        agendamento.data = data
        db.session.commit()
        flash('Agendamento atualizado com sucesso!', 'sucesso')
        return redirect('/agendamentos')
    
    return render_template('editar_agendamentos.html', agendamento=agendamento)

@app.route('/admin/agendamentos/excluir/<int:id>', methods=['POST'])
def admin_excluir_agendamento(id):
    if not session.get('is_admin'):
        return redirect('/')
    
    agendamento = db.session.get(Agendamento, id)
    db.session.delete(agendamento)
    db.session.commit()

    flash('Agendamento excluído com sucesso!', 'sucesso')
    return redirect('/agendamentos')


if __name__ == '__main__':
    app.run(debug=True)