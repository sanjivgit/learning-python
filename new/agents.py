import json
from tools import get_order_status, create_order
from groq import Groq
from database import GROQ_API_KEY
from fastapi.responses import JSONResponse

client = Groq(
    api_key=GROQ_API_KEY,
)


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

prompt = """
You are a polite and professional order assistant.

Rules:
1. NEVER guess order status.
2. ALWAYS call get_order_status tool when order ID is mentioned.
3. ALWAYS call create_order tool when user wants to create a new order.
4. Respond politely after tool results.
"""

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
            model= "llama-3.3-70b-versatile",  #"gpt-4o-mini",
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
                model="llama-3.3-70b-versatile",
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

    
