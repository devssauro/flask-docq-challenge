from collections import Counter
from datetime import datetime

from flask import Flask, request, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import os
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///files.db3'


class Base(DeclarativeBase):
    ...


db = SQLAlchemy(model_class=Base)
db.init_app(app)
CORS(app, resources={r"*": {"origins": "*"}})


class File(db.Model):
    __tablename__ = "file"
    id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    text: Mapped[str] = mapped_column(Text, default="")
    src: Mapped[str] = mapped_column(String, nullable=False)
    date_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())


with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')


@app.post('/upload')
def upload():
    # Verifica se foi enviado um arquivo
    if 'img' not in request.files:
        return "Nenhuma imagem enviada", 400

    img = request.files['img']

    # Verifica se o arquivo tem um nome
    if img.filename == '':
        return "Nome de arquivo vazio", 400

    # Gere um nome aleatório usando uuid4
    file_extension = img.filename.rsplit('.', 1)[1].lower()
    _id = str(uuid.uuid4())
    random_filename = str(_id) + f".{file_extension}"
    file_path = os.path.join('static', random_filename)

    # Salva o arquivo com o nome aleatório
    img.save(file_path)

    # Obtém o texto do POST
    text_data = request.form.get('text_data')

    file = File(id=_id, text=text_data, src=f"{request.host_url}static/{random_filename}")
    db.session.add(file)
    db.session.commit()

    return {
        "id": file.id,
        "src": file.src,
        "text": file.text,
        "date_created": file.date_created
    }


@app.get('/<string:file_id>/words/total')
def total_words(file_id: str):
    file = db.get_or_404(File, file_id)
    words = [word for word in file.text.split() if word != '']
    return {"total_words": len(words)}


@app.get('/<string:file_id>/words/occurencies')
def word_ocurrencies(file_id: str):
    file = db.get_or_404(File, file_id)
    words = [word for word in file.text.split() if word != '']
    common_words = [
        "the", "and", "of", "in", "a", "an", "with", "is", "that", "for",
        "a", "da", "do", "as", "os", "se", "o", "e", "na", "no", "pra", "pro", "de", "em", "um",
        "uma", "com", "é", "que", "para", ".", ",", "-", *[str(n) for n in range(11)]
    ]

    word_count = Counter()

    for word in words:
        word = word.lower()
        if word not in common_words:
            word_count[word] += 1

    top_10_words = dict(word_count.most_common(10))

    result = {
        "labels": list(top_10_words.keys()),
        "datasets": [{"data": list(top_10_words.values())}]
    }

    return result


@app.get("/all")
def all_imges():
    where_clause = []
    if request.args.get("query"):
        where_clause.append(File.text.contains(request.args.get("query")))
    images: list[File] = db.session.execute(
        db.select(File).where(*where_clause).order_by(
            File.date_created.desc()
        )).scalars()

    return [{
        "id": image.id,
        "src": image.src,
        "text": image.text
    } for image in images]


if __name__ == '__main__':
    app.run(debug=True, port=5010)
