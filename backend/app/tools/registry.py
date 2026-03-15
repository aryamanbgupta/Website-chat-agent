"""Tool registry — maps tool names to functions and provides Gemini function declarations."""

from google.genai import types

from app.tools.check_compatibility import check_compatibility
from app.tools.diagnose_symptom import diagnose_symptom
from app.tools.installation_guide import get_installation_guide
from app.tools.product_details import get_product_details
from app.tools.search_parts import search_parts

REASONING_DESC = (
    "Your reasoning for calling this tool with these parameters. "
    "Explain why this tool is the right choice and how you determined the input values."
)

# Tool name → function mapping
TOOL_FUNCTIONS = {
    "search_parts": search_parts,
    "check_compatibility": check_compatibility,
    "get_installation_guide": get_installation_guide,
    "diagnose_symptom": diagnose_symptom,
    "get_product_details": get_product_details,
}


def get_tool_declarations() -> list[types.Tool]:
    """Return Gemini function declarations for all tools."""
    declarations = [
        types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="search_parts",
                description=(
                    "Search for refrigerator or dishwasher parts by query. "
                    "Use this when the user wants to find, browse, or look up parts. "
                    "Handles PS numbers, model numbers, part names, symptoms, and natural language queries. "
                    "Returns matching parts with prices and availability, plus relevant knowledge snippets."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "reasoning": types.Schema(type="STRING", description=REASONING_DESC),
                        "query": types.Schema(
                            type="STRING",
                            description="Search query — can be a PS number, model number, part name, symptom, or natural language description.",
                        ),
                        "appliance_type": types.Schema(
                            type="STRING",
                            description="Filter by appliance type: 'refrigerator' or 'dishwasher'. Omit to search all.",
                            enum=["refrigerator", "dishwasher"],
                        ),
                        "max_results": types.Schema(
                            type="INTEGER",
                            description="Maximum number of results to return (default 5).",
                        ),
                    },
                    required=["reasoning", "query"],
                ),
            ),
            types.FunctionDeclaration(
                name="check_compatibility",
                description=(
                    "Check if a specific part is compatible with a specific appliance model number. "
                    "Use this when the user asks 'is X compatible with Y' or 'does X work with Y'. "
                    "Returns compatible (True/False) with confidence 'verified' when both part and model are in our database, "
                    "or 'not_in_data' when the model is unknown."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "reasoning": types.Schema(type="STRING", description=REASONING_DESC),
                        "part_number": types.Schema(
                            type="STRING",
                            description="The PS part number (e.g., 'PS11752778').",
                        ),
                        "model_number": types.Schema(
                            type="STRING",
                            description="The appliance model number (e.g., 'WRS321SDHZ08').",
                        ),
                    },
                    required=["reasoning", "part_number", "model_number"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_installation_guide",
                description=(
                    "Get installation instructions or repair guidance. "
                    "Use for 'how do I install/replace X' or 'how to fix Y' questions. "
                    "Can look up by part number (returns difficulty, time, video) "
                    "or by symptom (returns step-by-step repair guide with causes)."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "reasoning": types.Schema(type="STRING", description=REASONING_DESC),
                        "part_number": types.Schema(
                            type="STRING",
                            description="PS part number to get installation info for.",
                        ),
                        "symptom": types.Schema(
                            type="STRING",
                            description="Symptom to find repair guide for (e.g., 'won't drain').",
                        ),
                        "appliance_type": types.Schema(
                            type="STRING",
                            description="Appliance type: 'refrigerator' or 'dishwasher'.",
                            enum=["refrigerator", "dishwasher"],
                        ),
                    },
                    required=["reasoning"],
                ),
            ),
            types.FunctionDeclaration(
                name="diagnose_symptom",
                description=(
                    "Diagnose an appliance problem from a symptom description. "
                    "Use when the user describes something wrong with their appliance "
                    "(e.g., 'ice maker not working', 'dishwasher won't drain', 'making noise'). "
                    "Returns possible causes, recommended replacement parts, and relevant knowledge. "
                    "If model_number is provided, filters parts to compatible ones."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "reasoning": types.Schema(type="STRING", description=REASONING_DESC),
                        "symptom": types.Schema(
                            type="STRING",
                            description="Description of the symptom or problem.",
                        ),
                        "appliance_type": types.Schema(
                            type="STRING",
                            description="Appliance type: 'refrigerator' or 'dishwasher'.",
                            enum=["refrigerator", "dishwasher"],
                        ),
                        "model_number": types.Schema(
                            type="STRING",
                            description="Optional appliance model number to filter compatible parts.",
                        ),
                    },
                    required=["reasoning", "symptom", "appliance_type"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_product_details",
                description=(
                    "Get full details for a specific part by PS number. "
                    "Use after search_parts to get complete product info for display, "
                    "or when the user asks about a specific part they already know. "
                    "Returns all fields needed for a product card including price, rating, image, and description."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "reasoning": types.Schema(type="STRING", description=REASONING_DESC),
                        "part_number": types.Schema(
                            type="STRING",
                            description="The PS part number (e.g., 'PS11752778').",
                        ),
                    },
                    required=["reasoning", "part_number"],
                ),
            ),
        ]),
    ]
    return declarations


def execute_tool(name: str, args: dict) -> dict:
    """Execute a tool by name with the given arguments."""
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**args)
    except Exception as e:
        return {"error": f"Tool {name} failed: {str(e)}"}
