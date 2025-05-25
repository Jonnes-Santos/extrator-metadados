from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from PIL import Image
from PIL.ExifTags import TAGS
import exifread
from PyPDF2 import PdfReader

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Extrai metadados de imagens (EXIF)
def get_exif_data(image_path):
    exif_data = {}
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            for tag, value in tags.items():
                exif_data[tag] = str(value)
        
        img = Image.open(image_path)
        if hasattr(img, '_getexif') and img._getexif() is not None:
            for tag, value in img._getexif().items():
                tag_name = TAGS.get(tag, tag)
                exif_data[f"PIL_{tag_name}"] = str(value)
        
        exif_data["Image Format"] = img.format
        exif_data["Image Size"] = f"{img.width}x{img.height}"
        img.close()
    except Exception as e:
        exif_data["error"] = f"Erro EXIF: {str(e)}"
    return exif_data

# Extrai metadados de PDF
def extract_pdf_metadata(file_path):
    metadata = {}
    try:
        with open(file_path, 'rb') as f:
            pdf = PdfReader(f)
            info = pdf.metadata
            metadata.update({
                "Author": info.get('/Author', 'N/A'),
                "Title": info.get('/Title', 'N/A'),
                "Pages": len(pdf.pages),
                "Producer": info.get('/Producer', 'N/A'),
                "Encrypted": pdf.is_encrypted
            })
        return metadata
    except Exception as e:
        return {"error": f"Erro PDF: {str(e)}"}

# Rotas
@app.route('/')
def home():
    return {"message": "API de Metadados. Use /upload para arquivos."}, 200

@app.route('/health')
def health():
    return {"status": "online", "service": "metadata-extractor"}, 200

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nome inválido"}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            metadata = get_exif_data(filepath)
        elif filename.lower().endswith('.pdf'):
            metadata = extract_pdf_metadata(filepath)
        else:
            os.remove(filepath)
            return jsonify({"error": "Formato não suportado (use JPEG/PNG/PDF)"}), 400
        
        os.remove(filepath)
        return jsonify({"filename": filename, "metadata": metadata})
    
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, threaded=True)