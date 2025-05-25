from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from PIL import Image
from PIL.ExifTags import TAGS
import exifread
from PyPDF2 import PdfReader

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limite de 10MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Função para extrair metadados de imagens (EXIF)
def get_exif_data(image_path):
    exif_data = {}
    try:
        # Usando exifread para metadados brutos
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            for tag, value in tags.items():
                exif_data[tag] = str(value)
        
        # Usando Pillow para metadados adicionais
        img = Image.open(image_path)
        if hasattr(img, '_getexif') and img._getexif() is not None:
            for tag, value in img._getexif().items():
                tag_name = TAGS.get(tag, tag)
                exif_data[f"PIL_{tag_name}"] = str(value)
        
        exif_data["Image Format"] = img.format
        exif_data["Image Size"] = f"{img.width}x{img.height}"
        img.close()
        
    except Exception as e:
        exif_data["error"] = f"Erro ao ler EXIF: {str(e)}"
    return exif_data

# Função para extrair metadados de PDF
def extract_pdf_metadata(file_path):
    metadata = {}
    try:
        with open(file_path, 'rb') as f:
            pdf = PdfReader(f)
            info = pdf.metadata
            if info:
                metadata.update({
                    "PDF Author": info.get('/Author', 'N/A'),
                    "PDF Title": info.get('/Title', 'N/A'),
                    "PDF Creator": info.get('/Creator', 'N/A'),
                    "PDF Producer": info.get('/Producer', 'N/A'),
                    "PDF Pages": len(pdf.pages),
                    "PDF Encrypted": "Sim" if pdf.is_encrypted else "Não"
                })
            else:
                metadata["PDF Info"] = "Nenhum metadado encontrado"
        return metadata
    except Exception as e:
        return {"error": f"Erro ao ler PDF: {str(e)}"}

# Rota principal para upload
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nome de arquivo inválido"}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        
        # Processa de acordo com o tipo de arquivo
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            metadata = get_exif_data(filepath)
        elif filename.lower().endswith('.pdf'):
            metadata = extract_pdf_metadata(filepath)
        else:
            os.remove(filepath)
            return jsonify({"error": "Formato não suportado. Use JPEG, PNG ou PDF."}), 400
        
        os.remove(filepath)
        return jsonify({"filename": filename, "metadata": metadata})
    
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# Rota de saúde para verificar se o servidor está online
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "service": "metadata-extractor"})

if __name__ == '__main__':
    app.run(debug=True)