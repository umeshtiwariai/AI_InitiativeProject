import os
import re
from pathlib import Path

import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from services.report_engine import clean, find_col

BASE_DIR = Path(__file__).resolve().parents[1]


def normalize_text(value):
    if value is None:
        return ''
    text = str(value)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def document_score(text, query):
    query_terms = set(re.findall(r'\w+', query.lower()))
    if not query_terms:
        return 0
    words = set(re.findall(r'\w+', text.lower()))
    return sum(1 for term in query_terms if term in words)


def extract_documents_from_df(df):
    if df is None or df.empty:
        return []

    documents = []
    project_col = find_col(df, ['Project Module', 'Project', 'Project Name'])
    status_col = find_col(df, ['Status Code', 'Status', 'Stage'])
    aging_col = find_col(df, ['Aging', 'Age'])
    desc_col = find_col(df, ['Description', 'Notes', 'Comment', 'Remarks'])

    for _, row in df.head(100).iterrows():
        parts = []
        if project_col:
            parts.append(f'Project: {normalize_text(row.get(project_col))}')
        if status_col:
            parts.append(f'Status: {normalize_text(row.get(status_col))}')
        if aging_col:
            parts.append(f'Aging: {normalize_text(row.get(aging_col))}')
        if desc_col:
            parts.append(f'Description: {normalize_text(row.get(desc_col))}')
        joined = ' | '.join([p for p in parts if p])
        if joined:
            documents.append(joined)

    return documents


def load_text_corpus():
    documents = []
    for folder_name in ['data', 'history']:
        root = BASE_DIR / folder_name
        if not root.exists():
            continue

        for path in root.rglob('*'):
            if not path.is_file():
                continue

            suffix = path.suffix.lower()
            try:
                if suffix in ['.txt', '.md', '.json']:
                    text = path.read_text(encoding='utf-8', errors='ignore')
                    documents.append(f'Source: {path.name}\n{text.strip()[:1600]}')
                elif suffix == '.csv':
                    df = pd.read_csv(path, nrows=20)
                    documents.append(f'Source: {path.name}\n{df.head(5).to_csv(index=False)}')
                elif suffix in ['.xls', '.xlsx']:
                    df = pd.read_excel(path, nrows=20)
                    documents.append(f'Source: {path.name}\n{df.head(5).to_csv(index=False)}')
            except Exception:
                continue

    return documents


def retrieve_context(documents, query, top_k=4):
    if not documents:
        return []

    scored = []
    for document in documents:
        score = document_score(document, query)
        if score > 0:
            scored.append((score, document))

    if not scored:
        return documents[:top_k]

    scored.sort(key=lambda item: item[0], reverse=True)
    return [document for _, document in scored[:top_k]]


def answer_question(df, prompt, api_key='', top_k=4):
    documents = extract_documents_from_df(df)
    documents.extend(load_text_corpus())
    if not documents:
        return 'No context was available for retrieval. Upload a dataset or add files under data/ or history/ and try again.'

    context = retrieve_context(documents, prompt, top_k=top_k)
    context_text = '\n\n---\n\n'.join(context)
    system_prompt = (
        'You are a smart status report assistant. Use only the context provided below to answer the question. '
        'If the information is not available in the context, say that you could not find the answer.'
    )
    user_prompt = f'{system_prompt}\n\nContext:\n{context_text}\n\nQuestion: {prompt}\n\nAnswer concisely.'

    llm = ChatGoogleGenerativeAI(model='gemini-3-flash-preview', google_api_key=api_key, temperature=0.2)
    response = llm.invoke([HumanMessage(content=user_prompt)])
    return str(response.content)
