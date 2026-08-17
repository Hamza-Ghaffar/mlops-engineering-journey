import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))

from AI_System_Project_v1_Trip_planner.backend import run_travel_agent
from AI_System_Project_v1_Trip_planner.tools.tavily_tool import tavily_search
from AI_System_Project_v1_Trip_planner.tools.flight_tool import search_flights
from backend import run_travel_agent
#query_search = tavily_search("flights to Paris")

#print(query_search)


#res = search_flights("Plan a 7 days Austria trip from Pakistan")
#print(res)

user_input = input("Enter travel request: ")

response = run_travel_agent(
    user_input=user_input,
    thread_id="test_user"
)

print("\nFINAL RESPONSE:\n")
print(response["answer"])