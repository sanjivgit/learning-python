import json
from tools import get_order_status, create_order
from groq import Groq
from database import GROQ_API_KEY
from fastapi.responses import JSONResponse
from dao.history import create_history, get_last_10_history

client = Groq(
    api_key=GROQ_API_KEY,
)

model = "llama-3.3-70b-versatile"  # or "gpt-4o-mini"

prompt = """
You are a polite and professional order assistant.

Rules:
1. NEVER guess order status.
2. ALWAYS call get_order_status tool when order ID is mentioned.
3. ALWAYS call create_order tool when user wants to create a new order.
4. Respond politely after tool results.
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get the current status of an order using its order ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The ID of the order"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Create a new order with a given status",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "The status of the new order"
                    }
                },
                "required": ["status"]
            }
        }
    }
]

TOOL_MAP = {
    "get_order_status": get_order_status,
    "create_order": create_order
}

# create_order
def run_agent(user_message: str):
    try:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message}
        ]

        response = client.chat.completions.create(
            model= model,
            messages=messages,
            tools=tools,
            tool_choice="auto" 
        )

        message = response.choices[0].message

        # 🔥 If LLM decides to call tool
        if message.tool_calls:
            print("LLM decide to call tools: ", message.tool_calls)
            messages.append(message)


            for tool_call in message.tool_calls:
                print("Tool call details: ", tool_call)
                arguments = json.loads(tool_call.function.arguments)
                function_name = tool_call.function.name

                function = TOOL_MAP.get(function_name)

                if function:
                    print(f"Calling {function} with arguments: ", arguments)
                    result = function(**arguments)

                    # Send tool result back to LLM
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

            final_response = client.chat.completions.create(
                model=model,
                messages=messages
            )

            return final_response.choices[0].message.content    

        # If no tool call
        return message.content
    
    except Exception as err:
        return JSONResponse(
            status_code=500,
            content={"message": f"Oops! {str(err)}"},
        )

    
# Session_based agent
async def session_based_agent(db, session_id: str, user_message: str):
    try:
        # Save the user message to DB with session_id and role=user
        await create_history(db, session_id, "user", user_message)
        
        # Retrieve last 10 history messages for the session
        history = await get_last_10_history(db, session_id)

        messages = [
            {"role": "system", "content": prompt},
        ]
        
        # Append history messages to the messages list
        for item in history:
            messages.append({"role": item.role, "content": item.content})

        response = client.chat.completions.create(
            model= model,
            messages=messages,
            tools=tools,
            tool_choice="auto" 
        )

        message = response.choices[0].message

        # 🔥 If LLM decides to call tool
        if message.tool_calls:
            print("LLM decide to call tools: ", message.tool_calls)
            messages.append(message)


            for tool_call in message.tool_calls:
                print("Tool call details: ", tool_call)
                arguments = json.loads(tool_call.function.arguments)
                function_name = tool_call.function.name

                function = TOOL_MAP.get(function_name)

                if function:
                    print(f"Calling {function} with arguments: ", arguments)
                    result = function(**arguments)

                    # Send tool result back to LLM
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

            final_response = client.chat.completions.create(
                model=model,
                messages=messages
            )

            assistant_reply = final_response.choices[0].message.content

            # Save the final response to DB with session_id and role=assistant
            await create_history(db, session_id, "assistant", assistant_reply)

            return assistant_reply    

        # Save the final response to DB with session_id and role=assistant
        await create_history(db, session_id, "assistant", message.content)

        # If no tool call
        return message.content
    
    except Exception as err:
        return JSONResponse(
            status_code=500,
            content={"message": f"Oops! {str(err)}"},
        )
