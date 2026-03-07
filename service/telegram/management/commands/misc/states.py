from aiogram.fsm.state import StatesGroup, State


class Onboarding(StatesGroup):
    waiting_terms = State()
    waiting_newsletter = State()
    waiting_info_ack = State()
    waiting_ai_agent_choice = State()  # NEW

class AgentDialog(StatesGroup):
    chat = State()

class QuizStates(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()
    q6 = State()
