from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage


def generate_summary(report, prompt, api_key=''):
    comments=' | '.join(report.get('comments',[])[:5])
    try:
        llm=ChatGoogleGenerativeAI(model='gemini-3-flash-preview', google_api_key=api_key, temperature=0.2)
        msg=f'''Generate 5 executive weekly summary bullets using metrics {report['summary'].to_dict()} and latest comments {comments}. User ask: {prompt}. Mention project names when useful.'''
        res=llm.invoke([HumanMessage(content=msg)])
        return [x.strip('-• ') for x in str(res.content).split('\n') if x.strip()][:5]
    except:
        return ['Overall portfolio remains stable.','Deliveries progressed in the last week.','Aging risks require focus.','UAT movement continues.','Leadership attention needed on top blockers.']