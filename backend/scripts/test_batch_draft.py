from app.services.llm import get_llm, parse_json_response

def test():
    llm = get_llm(tier="flash", temperature=0.2)
    prompt = """You are a senior grant proposal specialist for Indian NGOs.
Applicant: Child Rights and You (CRY)
Grant: Mission Vatsalya (Ministry of Women and Child Development)
Mission: Child protection, education, pediatric health.

Draft the following 2 sections in valid JSON format:
{
  "executive_summary": "Comprehensive executive summary paragraph",
  "problem_statement": "Needs assessment and problem statement"
}
Return ONLY the JSON object.
"""
    r = llm.invoke(prompt)
    print("RAW RESPONSE:", r.content[:300])
    parsed = parse_json_response(r.content)
    print("PARSED KEYS:", list(parsed.keys()))

if __name__ == "__main__":
    test()
