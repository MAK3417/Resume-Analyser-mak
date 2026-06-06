import os
import uuid
from flask import Flask, request, render_template, url_for
from werkzeug.utils import secure_filename
from openai import OpenAI
import re

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

SKILLS = [
    "python", "java", "c", "c++", "sql",
    "html", "css", "javascript", "react",
    "nodejs", "aws", "docker", "git",
    "flask", "mongodb", "mysql"
]

SKILLS.extend([
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "tensorflow",
    "pytorch",
    "data analysis",
    "power bi",
    "excel",
    "linux",
    "kubernetes",
    "rest api",
    "fastapi",
    "django"
])


def extract_skills(text):
    text = (text or "").lower()
    return {
        skill for skill in SKILLS
        if re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", text)
    }

def call_openai_feedback(prompt):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        return None

    try:
        client = OpenAI(api_key=openai_api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=220,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI Error:", e)
        return None


def generate_ai_feedback(score, matched, missing):
    prompt = (
        f"Analyze this resume-job match with a score of {score}% .\n"
        f"Matched skills: {', '.join(matched) or 'none'} .\n"
        f"Missing skills: {', '.join(missing) or 'none'} .\n"
        "Provide concise improvement advice and a short learning roadmap."
    )
    ai_response = call_openai_feedback(prompt)
    if ai_response:
        return ai_response

    feedback = []

    if score >= 80:
        feedback.append(
            "Your profile strongly matches the job requirements."
        )
    elif score >= 50:
        feedback.append(
            "Your profile is partially aligned with the role."
        )
    else:
        feedback.append(
            "There is a significant skill gap for this position."
        )

    if matched:
        feedback.append(
            f"Your strongest matching skills are: {', '.join(matched[:5])}."
        )

    if missing:
        feedback.append(
            f"Consider learning: {', '.join(missing[:5])}."
        )

    return " ".join(feedback)


def learning_roadmap(missing):
    return [f"Learn {skill}" for skill in missing]


def analyze_resume(resume_text, job_text):
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)
    matched = sorted(resume_skills & job_skills)
    missing = sorted(job_skills - resume_skills)

    score = round((len(matched) / len(job_skills) * 100) if job_skills else 0, 2)
    recommendation = (
        "Excellent match! Your resume aligns very well with the job requirements."
        if score >= 80 else
        "Good match. Add the missing skills to improve your chances."
        if score >= 50 else
        "Your profile needs improvement. Focus on the missing skills listed below."
    )

    if score >= 90:
        rank = "Top 10%"
    elif score >= 75:
        rank = "Top 25%"
    elif score >= 50:
        rank = "Top 50%"
    else:
        rank = "Below Average"

    ai_feedback = generate_ai_feedback(score, matched, missing)

    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "recommendation": recommendation,
        "rank": rank,
        "ai_feedback": ai_feedback,
        "learning_roadmap": learning_roadmap(missing),
    }


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_blank(value):
    return not value or not value.strip()

photo_url = None


@app.route("/", methods=["GET", "POST"])
def home():
    resume = ""
    job = ""
    analysis = None
    error = None
    photo_url = None

    if request.method == "POST":
        resume = request.form.get("resume", "").strip()
        job = request.form.get("job", "").strip()
        photo = request.files.get("photo")

        if is_blank(resume) or is_blank(job):
            error = "Please paste both your resume and the job description."
        else:
            if photo and photo.filename:
                if allowed_file(photo.filename):
                    original_filename = secure_filename(photo.filename)
                    extension = os.path.splitext(original_filename)[1]
                    unique_filename = f"{uuid.uuid4().hex}{extension}"
                    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                    photo_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                    photo.save(photo_path)
                    photo_url = url_for("static", filename=f"uploads/{unique_filename}")
                else:
                    error = "Only PNG, JPG, JPEG, and GIF files are allowed for the resume photo."

            if not error:
                analysis = analyze_resume(resume, job)

    return render_template(
        "index.html",
        resume=resume,
        job=job,
        analysis=analysis,
        error=error,
        skills=SKILLS,
        photo_url=photo_url,
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)










