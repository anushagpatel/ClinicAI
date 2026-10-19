import json
from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from fastmcp import Client
from aws_services import extract_with_nova
from mcp_server import mcp

class State(TypedDict, total=False):
    transcript: str
    extraction: dict[str, Any]
    warnings: list[str]
    patient_id: str
    patient: dict

def extract_node(state: State):
    return {'extraction': extract_with_nova(state['transcript'])}

def validate_node(state: State):
    data = state.get("extraction") or {}
    warnings = []

    if not data.get("patient_name"):
        warnings.append(
            "Patient identity missing: select/create patient manually."
        )

    medications = data.get("medications") or []

    for med in medications:
        if not isinstance(med, dict):
            continue

        if not med.get("evidence"):
            warnings.append(
                f"No supporting quote for {med.get('name', 'medication')}; verify manually."
            )

    # FIX: Handle follow_up when Amazon Nova returns null
    follow_up = data.get("follow_up") or {}

    if follow_up.get("requested"):
        warnings.append(
            "Appointments require human confirmation; no automatic booking."
        )

    # FIX: Handle uncertainties when returned as null
    warnings.extend(data.get("uncertainties") or [])

    return {"warnings": warnings}

async def patient_lookup_node(state: State):
    if not state.get('patient_id'):
        return {'patient': {}}
    async with Client(mcp) as client:
        result = await client.call_tool('find_patient', {'patient_id': state['patient_id']})
        # FastMCP result structured_content is preferred when available.
        payload = getattr(result, 'structured_content', None)
        if payload is None:
            texts = [x.text for x in result.content if hasattr(x, 'text')]
            payload = json.loads(texts[0]) if texts else {}
        return {'patient': payload}

def build_graph():
    graph = StateGraph(State)
    graph.add_node('extract', extract_node)
    graph.add_node('validate', validate_node)
    graph.add_node('patient_lookup_mcp', patient_lookup_node)
    graph.add_edge(START, 'extract')
    graph.add_edge('extract', 'validate')
    graph.add_edge('validate', 'patient_lookup_mcp')
    graph.add_edge('patient_lookup_mcp', END)
    return graph.compile()
