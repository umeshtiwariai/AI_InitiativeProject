from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage


def generate_bullets(report_data, user_prompt, api_key):
    try:
        llm = ChatGoogleGenerativeAI(
            model='gemini-3-flash-preview',
            google_api_key=api_key,
            temperature=0.2
        )
        metrics = report_data['summary'].to_dict(orient='records')[0]
        prompt = f"""
Generate 5 concise PMO weekly status report bullets.
Use these metrics: {metrics}
Instruction: {user_prompt}
No markdown. Business tone.
"""
        res = llm.invoke([HumanMessage(content=prompt)])
        rows = [x.strip('-• ') for x in str(res.content).split('\n') if x.strip()]
        return rows[:5]
    except Exception:
        return [
            'Projects progressing as planned across active workstreams.',
            'Go-live pipeline remains stable this week.',
            'Few aging items need focused intervention.',
            'UAT movement continues as scheduled.',
            'Dependencies are under active monitoring.'
        ]