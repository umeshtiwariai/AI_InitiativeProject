from agents.report_agent import generate_summary


def revise_report(report, prompt):
    report['bullets']=generate_summary(report, prompt)
    return report