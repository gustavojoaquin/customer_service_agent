import os
from datetime import datetime
from typing import Annotated, Literal

from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from tools import fetch_user_flight_information, flight_tools, primary_assistant_tools


def update_dialog_stack(left: list[str], right: str | None) -> list[str]:
    """Update the dialog stack based on the right value."""
    if right is None:
        return left
    if right == "pop":
        return left[:-1]
    return left + [right]


class State(TypedDict):
    """State definition for the conversation graph."""

    messages: Annotated[list[AnyMessage], lambda x, y: x + y]
    user_info: str
    dialog_state: Annotated[
        list[Literal["primary_assistant", "flight_assistant"]], update_dialog_stack
    ]


class CompleteOrEscalate(BaseModel):
    """Mark the current task as completed or escalate control to the primary assistant."""

    reason: str


class ToFlightBookingAssistant(BaseModel):
    """Transfer work to a specialized flight booking assistant."""

    request: str = Field(
        description="Follow-up questions needed to clarify the flight request."
    )


llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0,
)

primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a customer support assistant. Your main role is to answer general questions and delegate flight modification tasks to the specialized assistant. User flight information: <Flights>{user_info}</Flights>. Current time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now)

flight_booking_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a specialized assistant for managing flight updates. The primary assistant delegates work to you. Confirm flight details with the customer. If the task is completed or the user changes their mind, use the CompleteOrEscalate tool. Current time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now)

assistant_runnable = primary_assistant_prompt | llm.bind_tools(
    primary_assistant_tools + [ToFlightBookingAssistant]
)

flight_runnable = flight_booking_prompt | llm.bind_tools(
    flight_tools + [CompleteOrEscalate]
)


def fetch_user_info_node(state: State) -> dict:
    """Fetch user flight information."""
    return {"user_info": fetch_user_flight_information.invoke({})}


def primary_assistant_node(state: State) -> dict:
    """Primary assistant node that handles general queries."""
    return {"messages": [assistant_runnable.invoke(state)]}


def flight_assistant_node(state: State) -> dict:
    """Flight assistant node that handles flight modifications."""
    return {"messages": [flight_runnable.invoke(state)]}


def enter_flight_assistant_node(state: State) -> dict:
    """Entry node for flight assistant."""
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    return {
        "messages": [
            ToolMessage(
                content="Transferring to flight assistant to handle your flight request.",
                tool_call_id=tool_call_id,
            )
        ],
        "dialog_state": "flight_assistant",
    }


def leave_skill_node(state: State) -> dict:
    """Node to return to primary assistant."""
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    return {
        "dialog_state": "pop",
        "messages": [
            ToolMessage(
                content="Returning to primary assistant.", tool_call_id=tool_call_id
            )
        ],
    }


def route_primary_assistant(state: State) -> str:
    """Route from primary assistant based on tool calls."""
    route = tools_condition(state)
    if route == END:
        return END

    # Check if there are tool calls
    if state["messages"][-1].tool_calls:
        tool_call = state["messages"][-1].tool_calls[0]
        if tool_call["name"] == ToFlightBookingAssistant.__name__:
            return "enter_flight_assistant"
        return "primary_tools_node"

    return "primary_assistant"


def route_flight_assistant(state: State) -> str:
    """Route from flight assistant based on tool calls."""
    route = tools_condition(state)
    if route == END:
        return END

    if state["messages"][-1].tool_calls:
        tool_call = state["messages"][-1].tool_calls[0]
        if tool_call["name"] == CompleteOrEscalate.__name__:
            return "leave_skill"
        return "flight_tools_node"

    return "flight_assistant"


builder = StateGraph(State)

builder.add_node("fetch_user_info", fetch_user_info_node)
builder.add_node("primary_assistant", primary_assistant_node)
builder.add_node("flight_assistant", flight_assistant_node)
builder.add_node("primary_tools_node", ToolNode(primary_assistant_tools))
builder.add_node("flight_tools_node", ToolNode(flight_tools))
builder.add_node("enter_flight_assistant", enter_flight_assistant_node)
builder.add_node("leave_skill", leave_skill_node)

builder.add_edge(START, "fetch_user_info")
builder.add_edge("fetch_user_info", "primary_assistant")

builder.add_conditional_edges("primary_assistant", route_primary_assistant)
builder.add_edge("primary_tools_node", "primary_assistant")

builder.add_edge("enter_flight_assistant", "flight_assistant")
builder.add_conditional_edges("flight_assistant", route_flight_assistant)
builder.add_edge("flight_tools_node", "flight_assistant")
builder.add_edge("leave_skill", "primary_assistant")

builder.add_edge("primary_tools_node", "primary_assistant")
builder.add_edge("flight_tools_node", "flight_assistant")

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
