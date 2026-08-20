from .base import Base
from .agent_draft import AgentDraft
from .customer import Customer
from .ticket_event import TicketEvent
from .ticket_resolution import TicketResolution
from .ticket import Ticket
from .transaction import Transaction
from .user import User
from .verification_token import VerificationToken

# Why use __init__.py file , what does it do and why make imports into it?

# Thing 1: just existing (marks the folder as a package)

# As we just covered — the file's mere presence tells Python "treat this folder as an importable package." An empty __init__.py does only this, nothing more. Your auth/__init__.py and customers/__init__.py can stay empty forever and still work fine — they don't need imports inside them for auth.router or customers.router to be importable elsewhere.

# Thing 2: putting import statements inside it (re-exporting) — a separate, optional feature

# This is what your models/__init__.py does, and it solves a different problem: convenience of import paths, not package-recognition.

# Without any re-exporting, if models/__init__.py were empty, you'd have to write:

# from models.user import User
# from models.ticket import Ticket
# from models.customer import Customer

# — spelling out the exact file each class lives in, every time, in every file that needs them.

# By instead writing this inside models/__init__.py:

# python
# from .user import User
# from .ticket import Ticket
# from .customer import Customer

# you're pulling those classes "up" to be directly accessible from the package itself, letting anyone elsewhere just write:
    
# from models import User, Ticket, Customer

# — one line, regardless of which specific file each class actually lives in. This is purely a convenience/ergonomics choice — nothing would break if you always used the fully-specified path instead; it's just nicer to read and write.

# Why this specific pattern mattered for Alembic

# This is the actual functional reason it's not purely cosmetic in your project: recall env.py does from models import Base, and 
# target_metadata = Base.metadata. Base.metadata only knows about model classes that have actually been imported somewhere by the time 
# Alembic runs — Python doesn't scan your models/ folder and auto-discover every .py file; it only registers classes that get explicitly 
# imported and executed.

# So if models/__init__.py were empty, and env.py only did from models import Base, none of your actual table classes (User, Ticket, etc.) 
# would ever get imported — meaning Base.metadata would be empty, and Alembic would think you have zero tables, generating a migration that 
# creates nothing. By importing every model class inside models/__init__.py, you guarantee that the moment anyone does 
# from models import Base (which triggers __init__.py to run), every model file gets imported as a side effect too — which is what actually 
# registers them all onto Base.metadata.
