# library/urls.py
from django.urls import path
from .views import (
    RegisterView, LoginView, BookCreateView, BookUpdateDeleteView,
    BorrowBookView, ReturnBookView, BookListView, BookDetailView,trigger_due_books_task
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('books/', BookListView.as_view(), name='book-list'),
    path('books/<int:pk>/', BookDetailView.as_view(), name='book-detail'),
    path('books/create/', BookCreateView.as_view(), name='book-create'),
    path('books/<int:pk>/update/', BookUpdateDeleteView.as_view(), name='book-update'),
    path('borrow/<int:book_id>/', BorrowBookView.as_view(), name='borrow-book'),
    path('return/<int:book_id>/', ReturnBookView.as_view(), name='return-book'),
    path('check_due_books/', trigger_due_books_task, name='check_due_books'),
]
