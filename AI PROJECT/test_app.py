"""Quick test for Resume Ranking AI — run with: python test_app.py"""
import sys
from app import app, analyze_resume, calculate_match_score, extract_skills, extract_experience_years, extract_education

# ── Sample data ────────────────────────────────────────────────────────────────
RESUME_1 = """
John Doe - Senior Software Engineer
Bachelor of Technology in Computer Science, 2018

5 years of experience in software development.

Skills: Python, Flask, Django, React, JavaScript, PostgreSQL, Docker, AWS
Machine learning, TensorFlow, scikit-learn, pandas, numpy, data science
Teamwork, leadership, agile, scrum, project management, communication
"""

RESUME_2 = """
Jane Smith - Junior Developer
Diploma in IT, 2022

1 year of experience.

Skills: HTML, CSS, JavaScript, basic Python
"""

JD = """
We are looking for a Python developer with 3+ years of experience in Flask,
REST APIs, PostgreSQL, Docker, and AWS. Machine learning experience preferred.
Strong communication, teamwork, and agile skills required.
"""

# ── Unit tests ─────────────────────────────────────────────────────────────────
def test_extract_skills():
    skills = extract_skills(RESUME_1)
    assert "Programming Languages" in skills, "Should detect programming languages"
    assert "AI/ML" in skills, "Should detect AI/ML skills"
    print("  [PASS] extract_skills")

def test_experience():
    years = extract_experience_years(RESUME_1)
    assert years == 5, f"Expected 5, got {years}"
    print("  [PASS] extract_experience_years")

def test_education():
    label, score = extract_education(RESUME_1)
    assert score == 2, f"Expected Bachelor level (2), got {score}"
    print("  [PASS] extract_education")

def test_match_score():
    score = calculate_match_score(RESUME_1, JD)
    assert 0 <= score <= 100, f"Score out of range: {score}"
    print(f"  [PASS] calculate_match_score  score={score}%")

def test_analyze_resume():
    r = analyze_resume(RESUME_1, JD, "john_doe.pdf")
    assert r["filename"] == "john_doe.pdf"
    assert 0 <= r["composite_score"] <= 100
    assert r["experience_years"] == 5
    print(f"  [PASS] analyze_resume  composite={r['composite_score']}%  match={r['match_score']}%")
    return r

def test_ranking_order():
    r1 = analyze_resume(RESUME_1, JD, "senior.pdf")
    r2 = analyze_resume(RESUME_2, JD, "junior.pdf")
    assert r1["composite_score"] > r2["composite_score"], (
        f"Senior resume should score higher: {r1['composite_score']} vs {r2['composite_score']}"
    )
    print(f"  [PASS] ranking order  senior={r1['composite_score']}%  junior={r2['composite_score']}%")

def test_flask_routes():
    client = app.test_client()

    # GET /
    resp = client.get("/")
    assert resp.status_code == 200, f"GET / returned {resp.status_code}"
    assert b"Resume Ranking" in resp.data
    print("  [PASS] GET /  200 OK, page loaded")

    # POST /rank — missing JD
    resp = client.post("/rank", data={})
    assert resp.status_code == 400
    print("  [PASS] POST /rank (no JD)  400 as expected")

    # POST /rank — no files
    resp = client.post("/rank", data={"job_description": "Python developer"})
    assert resp.status_code == 400
    print("  [PASS] POST /rank (no files)  400 as expected")

    # POST /rank — with a real in-memory text file
    import io
    txt_file = (io.BytesIO(RESUME_1.encode()), "john_doe.txt")
    resp = client.post(
        "/rank",
        data={"job_description": JD, "resumes": txt_file},
        content_type="multipart/form-data"
    )
    assert resp.status_code == 200, f"POST /rank returned {resp.status_code}: {resp.data}"
    payload = resp.get_json()
    assert "results" in payload and len(payload["results"]) == 1
    result = payload["results"][0]
    print(f"  [PASS] POST /rank (real file)  rank=#{result['rank']}  badge={result['badge']}  score={result['composite_score']}%")

# ── Run all ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n========================================")
    print("  Resume Ranking AI — Test Suite")
    print("========================================\n")

    tests = [
        test_extract_skills,
        test_experience,
        test_education,
        test_match_score,
        test_analyze_resume,
        test_ranking_order,
        test_flask_routes,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1

    print(f"\n----------------------------------------")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"----------------------------------------")

    if failed:
        print("\n  [X] Some tests failed.\n")
        sys.exit(1)
    else:
        print("\n  [OK] All tests passed! Run: python app.py\n")
        print("  Open: http://127.0.0.1:5000\n")
