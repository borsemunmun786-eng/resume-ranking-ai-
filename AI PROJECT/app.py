import os
import re
import json
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import PyPDF2
import docx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import numpy as np

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

try:
    nltk.download('punkt_tab', quiet=True)
except:
    pass

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.secret_key = 'resume_ranking_secret_key'

os.makedirs('uploads', exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

# Skill keywords by category
SKILL_CATEGORIES = {
    "Programming Languages": ["python", "java", "javascript", "c++", "c#", "ruby", "php", "swift", "kotlin", "go", "rust", "typescript", "scala", "r", "matlab"],
    "Web Technologies": ["html", "css", "react", "angular", "vue", "node.js", "django", "flask", "spring", "express", "bootstrap", "jquery"],
    "Databases": ["sql", "mysql", "postgresql", "mongodb", "redis", "oracle", "sqlite", "cassandra", "elasticsearch"],
    "Cloud & DevOps": ["aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git", "ci/cd", "terraform", "ansible"],
    "AI/ML": ["machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "nlp", "computer vision", "data science", "pandas", "numpy"],
    "Soft Skills": ["leadership", "communication", "teamwork", "problem solving", "management", "agile", "scrum", "project management"]
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    except Exception as e:
        text = f"Error reading PDF: {str(e)}"
    return text

def extract_text_from_docx(filepath):
    text = ""
    try:
        doc = docx.Document(filepath)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        text = f"Error reading DOCX: {str(e)}"
    return text

def extract_text_from_txt(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading TXT: {str(e)}"

def extract_text(filepath, filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        return extract_text_from_pdf(filepath)
    elif ext == 'docx':
        return extract_text_from_docx(filepath)
    elif ext == 'txt':
        return extract_text_from_txt(filepath)
    return ""

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_skills(text):
    text_lower = text.lower()
    found_skills = {}
    for category, skills in SKILL_CATEGORIES.items():
        matched = [skill for skill in skills if skill in text_lower]
        if matched:
            found_skills[category] = matched
    return found_skills

def extract_experience_years(text):
    patterns = [
        r'(\d+)\+?\s*years?\s*of\s*experience',
        r'(\d+)\+?\s*years?\s*experience',
        r'experience\s*of\s*(\d+)\+?\s*years?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return 0

def extract_education(text):
    education_keywords = {
        'phd': 4, 'doctorate': 4, 'ph.d': 4,
        'master': 3, 'mba': 3, 'm.s': 3, 'm.tech': 3, 'msc': 3,
        'bachelor': 2, 'b.s': 2, 'b.tech': 2, 'bsc': 2, 'b.e': 2,
        'diploma': 1, 'associate': 1
    }
    text_lower = text.lower()
    highest = 0
    highest_label = "Not Specified"
    labels = {4: "PhD/Doctorate", 3: "Master's Degree", 2: "Bachelor's Degree", 1: "Diploma/Associate"}
    for keyword, level in education_keywords.items():
        if keyword in text_lower and level > highest:
            highest = level
            highest_label = labels[level]
    return highest_label, highest

def calculate_match_score(resume_text, job_description):
    processed_resume = preprocess_text(resume_text)
    processed_jd = preprocess_text(job_description)
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
    try:
        tfidf_matrix = vectorizer.fit_transform([processed_jd, processed_resume])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    except Exception:
        similarity = 0.0
    return round(float(similarity) * 100, 2)

def analyze_resume(resume_text, job_description, filename):
    match_score = calculate_match_score(resume_text, job_description)
    skills = extract_skills(resume_text)
    exp_years = extract_experience_years(resume_text)
    education_label, education_score = extract_education(resume_text)

    # Count total matched skills
    total_skills = sum(len(v) for v in skills.values())

    # Composite score
    skill_bonus = min(total_skills * 1.5, 20)
    exp_bonus = min(exp_years * 2, 15)
    edu_bonus = education_score * 2
    composite = min(match_score + skill_bonus + exp_bonus + edu_bonus, 100)

    jd_words = set(preprocess_text(job_description).split())
    resume_words = set(preprocess_text(resume_text).split())
    missing_keywords = list(jd_words - resume_words)[:10]

    return {
        "filename": filename,
        "match_score": match_score,
        "composite_score": round(composite, 2),
        "skills": skills,
        "total_skills": total_skills,
        "experience_years": exp_years,
        "education": education_label,
        "missing_keywords": missing_keywords,
        "text_length": len(resume_text.split())
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rank', methods=['POST'])
def rank_resumes():
    job_description = request.form.get('job_description', '').strip()
    if not job_description:
        return jsonify({'error': 'Job description is required'}), 400

    files = request.files.getlist('resumes')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'Please upload at least one resume'}), 400

    results = []
    errors = []

    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            try:
                text = extract_text(filepath, filename)
                if text and len(text.strip()) > 50:
                    analysis = analyze_resume(text, job_description, filename)
                    results.append(analysis)
                else:
                    errors.append(f"{filename}: Could not extract sufficient text")
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            if file.filename:
                errors.append(f"{file.filename}: Unsupported file format")

    if not results:
        return jsonify({'error': 'No resumes could be processed', 'details': errors}), 400

    # Rank by composite score
    results.sort(key=lambda x: x['composite_score'], reverse=True)
    for i, r in enumerate(results):
        r['rank'] = i + 1
        if r['composite_score'] >= 75:
            r['badge'] = 'Excellent Match'
            r['badge_color'] = 'excellent'
        elif r['composite_score'] >= 50:
            r['badge'] = 'Good Match'
            r['badge_color'] = 'good'
        elif r['composite_score'] >= 25:
            r['badge'] = 'Average Match'
            r['badge_color'] = 'average'
        else:
            r['badge'] = 'Low Match'
            r['badge_color'] = 'low'

    return jsonify({'results': results, 'errors': errors, 'total': len(results)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
