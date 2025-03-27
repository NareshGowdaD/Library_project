from celery import shared_task
from datetime import datetime
from .models import BorrowedBook

@shared_task
def check_due_books():
    """
    Background task to check for overdue books
    and mark them as overdue if not returned.
    """
    due_books = BorrowedBook.objects.filter(returned=False, due_date__lt=datetime.now())
    for book in due_books:
        print(f"Book '{book.book.title}' is overdue!")
    return f"{due_books.count()} overdue books found."
