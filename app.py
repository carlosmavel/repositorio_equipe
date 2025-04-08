from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory, flash
import os
import json
import time
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "chave_secreta_aleatoria"  # Troque por algo mais seguro

# Usuários fake
users = {
    "admin": {
        "password": generate_password_hash("admin123"),
        "role": "admin",
        "foto": None,
        "nome_completo": "Administrador Geral",
        "cargo": "Gerente de TI",
        "setor": "Tecnologia"
    },
    "colaborador": {
        "password": generate_password_hash("col123"),
        "role": "colaborador",
        "foto": None,
        "nome_completo": "João Silva",
        "cargo": "Analista",
        "setor": "Operações"
    },
    "editor": {
        "password": generate_password_hash("edit123"),
        "role": "editor",
        "foto": None,
        "nome_completo": "Maria Oliveira",
        "cargo": "Supervisora",
        "setor": "Qualidade"
    }
}

# Pastas
UPLOAD_FOLDER = "uploads"
PROFILE_PICS_FOLDER = "profile_pics"
for folder in [UPLOAD_FOLDER, PROFILE_PICS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)  # Criar pasta com permissões padrão
    # Verificar e ajustar permissões (opcional, dependendo do sistema)
    if not os.access(folder, os.W_OK):
        print(f"Sem permissão de escrita em {folder}. Ajuste manualmente as permissões.")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROFILE_PICS_FOLDER"] = PROFILE_PICS_FOLDER

# Lista temporária de artigos com IDs
artigos = []

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("novo_artigo"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and check_password_hash(users[username]["password"], password):
            session["username"] = username
            session["role"] = users[username]["role"]
            session["foto"] = users[username]["foto"]
            session["nome_completo"] = users[username]["nome_completo"]
            return redirect(url_for("novo_artigo"))
        flash("Usuário ou senha inválidos!", "danger")
        return redirect(url_for("login"))
    users_json = json.dumps({k: {"foto": v["foto"]} for k, v in users.items()})
    return render_template("login.html", users=users, users_json=users_json)

@app.route("/novo-artigo", methods=["GET", "POST"])
def novo_artigo():
    if "username" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        if session["role"] in ["colaborador", "editor", "admin"]:
            titulo = request.form["titulo"]
            texto = request.form["texto"]
            files = request.files.getlist("files")  # Receber múltiplos arquivos
            filenames = []
            
            if files and files[0].filename:  # Verificar se algum arquivo foi enviado
                for file in files:
                    if file and file.filename:
                        filename = file.filename
                        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                        try:
                            file.save(file_path)
                            if os.path.exists(file_path):
                                filenames.append(filename)
                            # Remover a mensagem de erro
                            # else:
                            #     flash(f"Arquivo {filename} foi salvo, mas não encontrado após gravação.", "danger")
                        except Exception as e:
                            flash(f"Falha ao salvar o arquivo {filename}: {str(e)}", "danger")
                if not filenames:
                    flash("Nenhum arquivo foi salvo com sucesso. Verifique os arquivos ou permissões.", "danger")
                    return redirect(url_for("novo_artigo"))
            
            # Criar artigo mesmo sem arquivos
            artigo = {
                "id": len(artigos),
                "titulo": titulo,
                "texto": texto,
                "arquivos": filenames,  # Pode ser uma lista vazia
                "status": "pendente",
                "autor": session["username"],
                "bloqueado_por": None,
                "bloqueado_motivo": None,
                "created_at": datetime.now()  # Adiciona a data/hora de criação
            }
            artigos.append(artigo)
            flash("Artigo criado com sucesso!", "success")
            
            # Atraso pra simular processamento (já adicionado antes)
            time.sleep(2)
            
            return redirect(url_for("meus_artigos"))
    
    return render_template("novo_artigo.html", artigos=artigos)

@app.route("/meus-artigos")
def meus_artigos():
    if "username" not in session:
        return redirect(url_for("login"))
    
    meus_artigos = [artigo for artigo in artigos if artigo["autor"] == session["username"]]
    return render_template("meus_artigos.html", artigos=meus_artigos, now=datetime.now())

@app.route("/artigo/<int:artigo_id>", methods=["GET", "POST"])
def artigo(artigo_id):
    if "username" not in session:
        return redirect(url_for("login"))
    
    # Buscar o artigo pelo ID
    artigo = next((a for a in artigos if a["id"] == artigo_id), None)
    if not artigo:
        flash("Artigo não encontrado!", "danger")
        return redirect(url_for("meus_artigos"))
    
    # Verificar permissões: admin pode acessar qualquer artigo, outros só os próprios
    if session["role"] != "admin" and artigo["autor"] != session["username"]:
        flash("Você não tem permissão para acessar este artigo!", "danger")
        return redirect(url_for("meus_artigos"))
    
    # Verificar lock
    if artigo.get("bloqueado_por") and artigo["bloqueado_por"] != session["username"]:
        flash(f"Este artigo está sendo {artigo['bloqueado_motivo']} por {artigo['bloqueado_por']}.", "warning")
        return redirect(url_for("meus_artigos"))
    
    if request.method == "GET":
        # Bloquear artigo pra edição
        artigo["bloqueado_por"] = session["username"]
        artigo["bloqueado_motivo"] = "editando"
    
    if request.method == "POST" and session["role"] in ["colaborador", "editor", "admin"]:
        # Atualizar título e texto
        artigo["titulo"] = request.form["titulo"]
        artigo["texto"] = request.form["texto"]
        
        # Subir novos anexos
        files = request.files.getlist("files")
        novos_arquivos = artigo["arquivos"].copy() if artigo["arquivos"] else []
        if files and files[0].filename:  # Verificar se algum arquivo foi enviado
            for file in files:
                if file and file.filename:
                    filename = file.filename
                    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    try:
                        file.save(file_path)
                        if os.path.exists(file_path):
                            novos_arquivos.append(filename)
                        # Remover a mensagem de erro
                        # else:
                        #     flash(f"Arquivo {filename} foi salvo, mas não encontrado após gravação.", "danger")
                    except Exception as e:
                        flash(f"Falha ao salvar o arquivo {filename}: {str(e)}", "danger")

        # Remover anexos, se solicitado
        if "remover_anexos" in request.form:
            arquivos_remover = request.form["remover_anexos"].split(",") if request.form["remover_anexos"] else []
            for filename in arquivos_remover:
                if filename in novos_arquivos:
                    novos_arquivos.remove(filename)
                    try:
                        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                    except Exception as e:
                        flash(f"Falha ao remover o arquivo {filename}: {str(e)}", "danger")

        artigo["arquivos"] = novos_arquivos
        artigo["status"] = "pendente"  # Volta pra pendente após edição
        artigo["bloqueado_por"] = None
        artigo["bloqueado_motivo"] = None
        flash("Artigo atualizado com sucesso!", "success")  # Mensagem simplificada

        # Adicionar atraso de 2 segundos pra simular processamento
        time.sleep(1)

        return redirect(url_for("meus_artigos"))
    
    # Renderizar o template para GET ou quando POST não é executado
    return render_template("artigo.html", artigo=artigo, artigos=artigos)

@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if "username" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        foto = request.files.get("foto")
        if foto:
            filename = f"{session['username']}_{foto.filename}"
            file_path = os.path.join(app.config["PROFILE_PICS_FOLDER"], filename)
            try:
                foto.save(file_path)
                if os.path.exists(file_path):
                    users[session["username"]]["foto"] = filename
                    session["foto"] = filename
                else:
                    flash(f"Foto {filename} foi salva, mas não encontrada após gravação.", "danger")
            except Exception as e:
                flash(f"Falha ao salvar a foto {filename}: {str(e)}", "danger")
        return redirect(url_for("perfil"))
    
    user_data = users[session["username"]]
    return render_template("perfil.html", username=session["username"], role=session["role"], foto=session["foto"],
                          nome_completo=user_data["nome_completo"], cargo=user_data["cargo"], setor=user_data["setor"], artigos=artigos)

@app.route("/aprovacao", methods=["GET", "POST"])
def aprovacao():
    if "username" not in session or session["role"] not in ["editor", "admin"]:
        flash("Você não tem permissão para acessar esta página!", "danger")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        artigo_id = int(request.form["artigo_id"])
        acao = request.form["acao"]
        artigo = next((a for a in artigos if a["id"] == artigo_id), None)
        if artigo and artigo["status"] == "pendente":
            # Verificar lock
            if artigo.get("bloqueado_por") and artigo["bloqueado_por"] != session["username"]:
                flash(f"Este artigo está sendo {artigo['bloqueado_motivo']} por {artigo['bloqueado_por']}.", "warning")
                return redirect(url_for("aprovacao"))
            
            # Bloquear artigo pra análise
            artigo["bloqueado_por"] = session["username"]
            artigo["bloqueado_motivo"] = "analisando"
            
            if acao == "aprovar":
                artigo["status"] = "aprovado"
                artigo["bloqueado_por"] = None
                artigo["bloqueado_motivo"] = None
                flash(f"Artigo '{artigo['titulo']}' aprovado com sucesso!", "success")
            elif acao == "rejeitar":
                artigo["status"] = "rejeitado"
                artigo["bloqueado_por"] = None
                artigo["bloqueado_motivo"] = None
                flash(f"Artigo '{artigo['titulo']}' rejeitado!", "warning")
        return redirect(url_for("aprovacao"))
    
    # Garantir que pendentes seja uma lista válida
    if not isinstance(artigos, (list, tuple)):
        pendentes = []
    else:
        pendentes = [artigo for artigo in artigos if artigo["status"] == "pendente" and not artigo.get("bloqueado_por")]
    
    return render_template("aprovacao.html", artigos=artigos, pendentes=pendentes)

@app.route("/pesquisar")
def pesquisar():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("pesquisar.html", artigos=artigos, now=datetime.now())

@app.route("/profile_pics/<filename>")
def profile_pics(filename):
    return send_from_directory(app.config["PROFILE_PICS_FOLDER"], filename)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("role", None)
    session.pop("foto", None)
    session.pop("nome_completo", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)