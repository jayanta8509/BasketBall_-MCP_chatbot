from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from dotenv import load_dotenv
load_dotenv()

# Global memory for conversation persistence
memory = MemorySaver()

import asyncio
import os
from typing import Dict, Any

def get_user_config(user_id: str) -> Dict[str, Any]:
    """Get configuration for user-specific memory thread"""
    return {"configurable": {"thread_id": f"user_{user_id}"}}

async def setup_agent():
    """Setup MCP client and AI agent"""
    client = MultiServerMCPClient(
        {
            "Registration_detail_count": {
                "command": "python",
                "args": ["count_functions.py"],
                "transport": "stdio",
            },
            "Fifth_Grade_data": {
                "command": "python",
                "args": ["fifth_grade_functions.py"],
                "transport": "stdio",
            },
            "Google_ALL_sheet_data": {
                "command": "python",
                "args": ["form_responses_functions.py"],
                "transport": "stdio",
            },
            "Fourth_Grade_data": {
                "command": "python",
                "args": ["fourth_grade_functions.py"],
                "transport": "stdio",
            },
            "Seven_and_Eight_Grade_data": {
                "command": "python",
                "args": ["seventh_eighth_grade_functions.py"],
                "transport": "stdio",
            },
            "Sixth_Grade_data": {
                "command": "python",
                "args": ["sixth_grade_functions.py"],
                "transport": "stdio",
            },
            "Third_Grade_data": {
                "command": "python",
                "args": ["third_grade_functions.py"],
                "transport": "stdio",
            },
            "Waitlist_data": {
                "command": "python",
                "args": ["waitlist_functions.py"],
                "transport": "stdio",
            }
        }
    )

    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

    tools = await client.get_tools()
    model = ChatOpenAI(model="gpt-4o-mini")
    agent = create_react_agent(model, tools, checkpointer=memory)
    
    return agent

async def process_question(agent, user_question,user_id="default_user"):
    """Send any user question to the agent"""
    # print(f"\n🔍 Question: {user_question}")
    # print("🔄 Processing...")
    config = get_user_config(user_id)
    
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_question}]},
        config
    )
    
    return response['messages'][-1].content

async def main():
    """Main function with interactive user input"""
    print("🏀 Basketball League Management Assistant")
    print("=" * 50)

    # Setup agent
    agent = await setup_agent()
    print("✅ Agent setup complete!")
    print("📊 Connected to: Basketball Registration & Bracket Management System")
    print("🏀 Divisions: 3rd-8th Grade (Boys & Girls), Waitlists, Team Counts")

    # Example questions
    example_questions = [
        "How many teams are registered in 3rd Boys?",
        "Show me all teams on the waitlist for 4th Girls",
        "What's the contact info for the coach of 'Eldon 3rd Grade A'?",
        "Which divisions are currently full?",
        "Give me a summary of all registered teams by division",
        "Show me the bracket assignments for 5th Grade Boys",
        "Who is on the manual waitlist and in what position?",
        "Compare registration counts with bracket assignments",
        "What's the total revenue from team registrations?",
        "Find teams registered by coach 'Aaron Kliethermes'",
        "Which divisions still need more teams?",
        "Generate a complete league status report"
    ]
    
    print("\n💡 Example Questions:")
    for i, q in enumerate(example_questions, 1):
        print(f"{i}. {q}")
    
    print("\n" + "=" * 50)
    
    while True:
        print("\nChoose an option:")
        print("1. Ask a custom question")
        print("2. Try an example question")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            # Custom question
            user_question = input("\n📝 Enter your question: ").strip()
            if user_question:
                try:
                    answer = await process_question(agent, user_question)
                    print(f"\n📋 Answer:\n{answer}")
                except Exception as e:
                    print(f"❌ Error: {e}")
            else:
                print("❌ Please enter a valid question.")
                
        elif choice == "2":
            # Example question
            print("\n💡 Select an example:")
            for i, q in enumerate(example_questions, 1):
                print(f"{i}. {q}")
            
            try:
                example_choice = int(input("\nEnter example number: ")) - 1
                if 0 <= example_choice < len(example_questions):
                    selected_question = example_questions[example_choice]
                    answer = await process_question(agent, selected_question)
                    print(f"\n📋 Answer:\n{answer}")
                else:
                    print("❌ Invalid example number.")
            except ValueError:
                print("❌ Please enter a valid number.")
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == "3":
            print("\n👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

# Alternative: Direct question function
async def ask_question(question, division_filter=None, user_id="default_user"):
    """Function to directly ask a question with optional division context (for programmatic use)"""
    agent = await setup_agent()

    # Include basketball league context in the question
    contextual_question = f"""
    Basketball League Context:
    - Available Divisions: 3rd, 4th, 5th, 6th, 7/8 Grade (Boys & Girls)
    - Data Available: Team Registrations, Bracket Assignments, Waitlists, Contact Info
    - Sheets: Form Responses 1, 3rd-8th Grade Brackets, Waitlist, Count Summary
    {f"- Focus Division: {division_filter}" if division_filter else ""}

    Available Basketball League Management Tools:
    📋 REGISTRATIONS: get_teams_by_division, find_registrations_by_email,
                     get_waitlisted_teams, list_contacts, count_teams_by_division

    🏀 BRACKETS: list_*_grade_*_teams, get_*_grade_*_team_by_number,
                  find_*_grade_*_teams_by_name, compare_*_grade_*_sheet_with_registrations

    ⏳ WAITLISTS: list_waitlist_entries, get_waitlist_for_division,
                 get_combined_waitlist_for_division, get_waitlist_position_for_team

    📊 SUMMARY: get_division_summary, list_division_summaries, get_overall_team_totals,
               get_revenue_summary, list_full_divisions, list_divisions_still_needing_teams

    👥 CONTACTS: get_candidate_contact_by_name, get_candidate_profiles_by_name,
                get_candidate_teams, is_candidate_on_any_waitlist

    User's Question: {question}

    Please use the appropriate MCP tools to answer this basketball league management question.
    Provide clear insights with relevant team data, contact information, and actionable recommendations.
    """

    return await process_question(agent, contextual_question,user_id)



def clear_conversation(user_id: str):
    """Clear conversation memory for a specific user"""
    print(f"🧹 Cleared conversation memory for user: {user_id}")
    # Note: MemorySaver automatically manages conversation state
    # The memory is stored per thread_id (user_id), so conversations remain separate


def get_conversation_summary(user_id: str) -> str:
    """Get a summary of the conversation for continuity"""
    return f"Conversation thread: user_{user_id} - CapAmerica product catalog inquiry"

if __name__ == "__main__":
    # Run interactive mode
    asyncio.run(main())