"""Question structure and literal evidence checks, separate from semantic quality."""
import json
import re
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from .note_contract import compact, ROOT

PROMPT = (Path(ROOT) / 'prompts/question-generation-v1.txt').read_text(encoding='utf-8')


class Citation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    source_id: str = Field(min_length=1, max_length=180)
    quote: str = Field(min_length=1, max_length=4000)


class Question(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['flashcard', 'practice']
    objective: Literal['definition', 'conditions', 'worked_example', 'explanation']
    question: str = Field(min_length=8, max_length=2000)
    answer: str = Field(min_length=8, max_length=6000)
    citations: list[Citation] = Field(min_length=1, max_length=8)


class Output(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    questions: list[Question] = Field(min_length=1, max_length=8)


SCHEMA = Output.model_json_schema()


def provider_grammar(node):
    """Inline references and omit constraints unsupported by Ollama's grammar compiler.

    The complete Pydantic contract is still enforced after generation and at publish.
    """
    if isinstance(node, list): return [provider_grammar(value) for value in node]
    if not isinstance(node, dict): return node
    if '$ref' in node:
        return provider_grammar(SCHEMA['$defs'][node['$ref'].removeprefix('#/$defs/')])
    omit = {'$defs', 'title', 'minLength', 'maxLength', 'minItems', 'maxItems', 'default'}
    return {key: provider_grammar(value) for key, value in node.items() if key not in omit}


GRAMMAR = provider_grammar(SCHEMA)


def messages(evidence):
    return [{'role': 'system', 'content': PROMPT + '\nOUTPUT_SCHEMA:\n' + compact(SCHEMA)},
        {'role': 'user', 'content': 'STUDY_EVIDENCE_JSON:\n' + compact(evidence)}]


def validate_questions(output, evidence):
    result = Output.model_validate(output).model_dump()
    if len(result['questions']) > evidence['count']:
        raise ValueError('too_many_questions')
    sources = {s['id']: s['text'] for s in evidence['sources']}
    seen = set()
    for question in result['questions']:
        normalized = ' '.join(question['question'].casefold().split())
        if not normalized or normalized in seen or not question['answer'].strip():
            raise ValueError('duplicate_or_blank_question')
        seen.add(normalized)
        if evidence['kind'] != 'mixed' and question['kind'] != evidence['kind']:
            raise ValueError('wrong_question_kind')
        for citation in question['citations']:
            if not citation['quote'].strip() or citation['source_id'] not in sources or citation['quote'] not in sources[citation['source_id']]:
                raise ValueError('unsupported_citation')
        # A local-model trial invented numeric exercises despite valid quote links.
        # Refuse new numeric literals, rather than presenting them as lecture evidence.
        def numbers(text):
            return set(re.findall(r'(?<![\w.])[-+]?\d+(?:\.\d+)?', text))
        cited_text = '\n'.join(sources[c['source_id']] for c in question['citations'])
        if not numbers(question['question'] + '\n' + question['answer']) <= numbers(cited_text):
            raise ValueError('unsupported_numeric_literal')
    # IDs are assigned here, never trusted from generated text.
    return [{**question, 'id': f'q{index + 1}'} for index, question in enumerate(result['questions'])]


def parse_questions(raw, evidence):
    return validate_questions(json.loads(raw), evidence)
