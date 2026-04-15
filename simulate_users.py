import sys
sys.stdout.reconfigure(encoding='utf-8')
from rag_system import RAGSystem

rag = RAGSystem()

print("\n--- Simulating User 1 (Alice) ---")
print("Alice:", "Can I work from home on Mondays?")
alice_response1 = rag.ask("Can I work from home on Mondays?", user_id="alice_123")
print("Bot:", alice_response1)

print("\n--- Simulating User 2 (Bob) ---")
print("Bob:", "What ingredients do I need for Avocado Toast?")
bob_response1 = rag.ask("What ingredients do I need for Avocado Toast?", user_id="bob_456")
print("Bot:", bob_response1)

print("\n--- Returning to Simulating User 1 (Alice) ---")
print("Alice:", "What days did you say were mandatory again?")
alice_response2 = rag.ask("What days did you say were mandatory again?", user_id="alice_123")
print("Bot:", alice_response2)

print("\n--- Checking User 2 (Bob) Summary ---")
print(rag.summarize_history("bob_456"))
