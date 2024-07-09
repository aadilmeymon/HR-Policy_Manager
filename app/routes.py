from flask import Blueprint, request, render_template, redirect, url_for, flash
import os
import openai
import pinecone
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

OPENAI_KEY = os.getenv('OPENAI_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_ENV = os.getenv('PINECONE_ENV')

main = Blueprint('main', __name__)

openai.api_key = OPENAI_KEY

# Initialize Pinecone client
pinecone_client = pinecone.Pinecone(api_key=PINECONE_API_KEY)

# Check if index exists, if not create it
index_name = 'testindex'

if index_name not in pinecone_client.list_indexes().names():
    pinecone_client.create_index(
        name=index_name,
        dimension=1536,
        metric='cosine'
    )

policy_index = pinecone_client.Index(index_name)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        process_file(filepath)
        flash('File successfully uploaded and processed')
        return redirect(url_for('main.index'))

@main.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['search_query']
        results = search_chunks(query)
        return render_template('search_results.html', results=results, query=query)
    return render_template('search_form.html')

@main.route('/delete/<chunk_id>', methods=['POST'])
def delete_chunk(chunk_id):
    policy_index.delete(ids=[chunk_id])
    flash(f'Chunk {chunk_id} deleted successfully')
    return redirect(url_for('main.index'))

@main.route('/update/<chunk_id>', methods=['POST'])
def update_chunk(chunk_id):
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        with open(filepath, 'r') as file:
            content = file.read()
            embedding = get_embedding(content)
            policy_index.upsert(vectors=[{
                'id': chunk_id,
                'values': embedding,
                'metadata': {'filename': filename, 'content': content[:200]}  # Update metadata as needed
            }])
        flash(f'Chunk {chunk_id} updated successfully')
        return redirect(url_for('main.index'))

def search_chunks(query):
    embedding = get_embedding(query)
    results = policy_index.query(queries=[embedding], top_k=10, include_metadata=True)
    return results

def process_file(filepath):
    with open(filepath, 'r') as file:
        content = file.read()
        chunks = split_into_chunks(content, chunk_size=200)  # Adjust the chunk size as needed

        for index, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            policy_index.upsert(vectors=[{
                'id': f'{os.path.basename(filepath)}-chunk-{index}',  # Chunk ID includes filename and chunk number
                'values': embedding,
                'metadata': {
                    'filename': os.path.basename(filepath),  # Metadata including filename
                    'content': chunk  # The entire chunk content
                }
            }])

def split_into_chunks(content, chunk_size=200):
    lines = content.split('\n')
    chunks = []
    current_chunk = ''

    for line in lines:
        if len(current_chunk) + len(line) > chunk_size:
            chunks.append(current_chunk)
            current_chunk = ''
        current_chunk += line + '\n'

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def get_embedding(text):
    response = openai.Embedding.create(
        input=[text],
        model="text-embedding-3-large"
    )
    return response['data'][0]['embedding']
