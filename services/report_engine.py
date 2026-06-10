import pandas as pd, numpy as np
from datetime import datetime, timedelta


def load_files(files):
    dfs=[]
    for f in files:
        if f.name.endswith('.csv'):
            dfs.append(pd.read_csv(f))
        else:
            dfs.append(pd.read_excel(f))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def find_col(df, names):
    if isinstance(names, str): names=[names]
    for n in names:
        for c in df.columns:
            if n.lower() in str(c).lower():
                return c
    return None


def clean(df):
    df.columns=[str(c).strip() for c in df.columns]
    for c in df.columns:
        if any(x in c.lower() for x in ['date','start','live','delivery']):
            try: df[c]=pd.to_datetime(df[c], errors='coerce', dayfirst=True)
            except: pass
    return df.fillna('')


def aging_bucket(v):
    if pd.isna(v): return ''
    v=int(v)
    if v<=30: return '0 - 30 Days'
    if v<=60: return '30 - 60 Days'
    if v<=90: return '60 - 90 Days'
    return '> 90 Days'


def generate_outlook(df, status_col, uat_col, project_col):
    """Generate outlook for next week"""
    if not uat_col or not project_col:
        return pd.DataFrame()
    
    today = pd.Timestamp.today().normalize()
    days_to_monday = (7 - today.weekday()) % 7
    if days_to_monday == 0:
        days_to_monday = 7
    next_mon = today + timedelta(days=days_to_monday)
    next_fri = next_mon + timedelta(days=4)
    
    outlook_rows = []
    for _, r in df.iterrows():
        dt = pd.to_datetime(r[uat_col], errors='coerce')
        if pd.notna(dt) and next_mon <= dt.normalize() <= next_fri:
            outlook_rows.append({
                'Project Module': r[project_col],
                'Planned Delivery': 'UAT/Go Live',
                'Date': dt.strftime('%d-%b-%Y')
            })
    
    return pd.DataFrame(outlook_rows).head(5) if outlook_rows else pd.DataFrame()


def generate_bullets(df, status_col, project_col, desc_col):
    """Generate executive summary bullets"""
    bullets = []
    if not project_col:
        return bullets
    
    df_copy = df.copy()
    df_copy = df_copy.sort_values('Aging', ascending=False) if 'Aging' in df_copy.columns else df_copy
    
    for _, r in df_copy.head(5).iterrows():
        proj = str(r.get(project_col, '')).strip()
        status = str(r.get(status_col, '')).strip() if status_col else ''
        aging = int(r.get('Aging', 0)) if 'Aging' in r else 0
        
        if not proj:
            continue
            
        if 'development' in status.lower() or 'dev' in status.lower():
            bullets.append(f"{proj} is in active development with planned deliverables under execution.")
        elif 'uat' in status.lower() or 'testing' in status.lower():
            bullets.append(f"{proj} is progressing in UAT stage with focus on completion of validations.")
        elif 'production' in status.lower() or 'go live' in status.lower():
            bullets.append(f"{proj} is nearing production readiness with deployment activities in progress.")
        elif aging >= 90:
            bullets.append(f"{proj} requires attention due to high aging ({aging} days) and pending dependencies.")
        else:
            bullets.append(f"{proj} is progressing as planned with current focus on {status.lower()}.")
    
    if not bullets:
        bullets = ["Overall portfolio is progressing as planned with key deliveries under active monitoring."]
    
    return bullets


def generate_report(files):
    df=clean(load_files(files))
    status=find_col(df,['Status Code','Status'])
    project=find_col(df,'Project Module')
    module=find_col(df,'Module ID')
    desc=find_col(df,'Description')
    uat=find_col(df,'Actual UAT Start')
    golive=find_col(df,['Actual Go live','Actual Go Live','Go Live Date'])

    today=pd.Timestamp.today().normalize()
    if uat:
        df['Aging']=(today-pd.to_datetime(df[uat], errors='coerce')).dt.days.clip(lower=0)
    else:
        df['Aging']=0

    summary=pd.DataFrame([{
        'Go Live':len(df[df[status]=='Production Cutover']) if status else 0,
        'PO Awaited':len(df[df[status]=='UD signed off']) if status else 0,
        'UAT':len(df[df[status].isin(['UAT','UAT Signed off','UAT Signedoff'])]) if status else 0,
        'Development':len(df[df[status]=='Development']) if status else 0,
        'In UD':len(df[df[status]=='UD submitted']) if status else 0,
        'UD Not Started':len(df[df[status]=='Pre - Engagement']) if status else 0,
        'Dropped / On Hold':len(df[df[status].isin(['Dropped','On Hold'])]) if status else 0
    }])

    if project and 'Aging' in df.columns:
        aging=df[[project,'Aging']].drop_duplicates(subset=[project]).sort_values('Aging', ascending=False).head(10).reset_index(drop=True)
        risks=df[[project,module,status,'Aging']].sort_values('Aging', ascending=False).head(3).reset_index(drop=True) if module and status else pd.DataFrame()
    else:
        aging = pd.DataFrame()
        risks = pd.DataFrame()

    # last 7 day delivery highlights from UAT start
    if uat:
        cutoff=today-timedelta(days=7)
        delivery=df[pd.to_datetime(df[uat], errors='coerce')>=cutoff].copy().head(10).reset_index(drop=True) if project else pd.DataFrame()
    else:
        delivery=df.head(5).reset_index(drop=True) if project else pd.DataFrame()

    outlook = generate_outlook(df, status, uat, project)
    
    comments=[]
    if desc:
        comments=df[desc].astype(str).tail(5).tolist()
    
    bullets = generate_bullets(df, status, project, desc)

    return {
        'raw':df,
        'summary':summary,
        'aging':aging,
        'delivery':delivery,
        'risks':risks,
        'outlook':outlook,
        'comments':comments,
        'bullets':bullets,
        'week_range':f"{today.strftime('%d %b')} - {(today + timedelta(days=4)).strftime('%d %b, %Y')}"
    }