from openai import OpenAI


def generate_interview_assessment(
    company,
    position,
    job_description,
    final_score,
    board_avg,
    recommendation,
    interview_notes,
):
    client = OpenAI()

    prompt = f"""
You are an interview preparation advisor for a senior finance professional focused on:
Treasury, Funding, Liquidity, Hedging, Debt Structuring, Project Finance, Infrastructure Finance, Treasury Transformation, and Strategic Finance.

Assess the interview notes below and prepare the candidate for the next step.

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
1. Short interview feedback assessment
2. What likely matters most to the interviewer
3. Strengths confirmed by the interview
4. Risks or objections detected
5. What to improve before the next round
6. Best talking points for the next round
7. Suggested follow-up message
8. Updated recommendation: Continue strongly / Continue carefully / Reconsider
"""

    response = client.responses.create(
        model="gpt-5.2",
        input=prompt,
    )

    return response.output_text
