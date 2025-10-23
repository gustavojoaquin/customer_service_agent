import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import tools_condition
from typing_extensions import TypedDict

from tools import flight_safe_tools, flight_sensitive_tools
from agents.main.primary_agent import CompleteOrEscalate, State


llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)

flight_booking_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un asistente especializado en gestionar actualizaciones de vuelos. Confirma los detalles con el cliente. Si la tarea se completa, usa la herramienta CompleteOrEscalate.",
        ),
        ("placeholder", "{messages}"),
    ]
)

flight_runnable = flight_booking_prompt | llm.bind_tools(
    flight_safe_tools + flight_sensitive_tools + [CompleteOrEscalate]
)


def flight_assistant_node(state: State):
    return {"messages": [flight_runnable.invoke(state)]}


def create_skill_router(safe_tools: list):
    def router(state: State):
        route = tools_condition(state)
        if route == END:
            return END
        tool_call = state["messages"][-1].tool_calls[0]
        if tool_call["name"] == CompleteOrEscalate.__name__:
            return "leave_skill"
        safe_tool_names = {t.name for t in safe_tools}
        if tool_call["name"] in safe_tool_names:
            return "safe_tools"
        return "sensitive_tools"

    return router

