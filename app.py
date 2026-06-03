from openai import OpenAI


def generate_interview_assessment(
    company,
    position,
    job_description,
    final_score,
    board_avg,
    recommendation,
    interview_notes,
    api_key=None,
    model="gpt-5.2",
):
    client = OpenAI(api_key=api_key) if api_key else OpenAI()

    instructions = """
You are an interview preparation advisor for a senior finance professional focused on
Treasury, Funding, Liquidity, Hedging, Debt Structuring, Project Finance,
Infrastructure Finance, Treasury Transformation, and Strategic Finance.

Be direct, practical, and interview-oriented.
Do not write a generic career-coaching answer.
Use the job context and interview notes to prepare the candidate for the next round.
"""

    prompt = f"""
Company:
{company}

Position:
{position}

Job Description:
{job_description}

Current Final Score:
{final_score}

Board Average Score:
{board_avg}

Current Recommendation:
{recommendation}

Interview Notes / Feedback / Next Step:
{interview_notes}

Please provide:
1. Short assessment of what the interview notes imply
2. What likely matters most to the interviewer
3. Strengths confirmed by the interview
4. Risks, objections, or weak signals detected
5. What to improve before the next round
6. Best talking points for the next round
7. Questions the candidate should ask next
8. Suggested concise follow-up message
9. Updated recommendation: Continue strongly / Continue carefully / Reconsider
"""

    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=prompt,
    )

    return response.output_text
