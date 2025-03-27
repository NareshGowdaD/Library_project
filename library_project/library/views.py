from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Book, BorrowedBook
from .serializers import UserSerializer, BookSerializer, BorrowedBookSerializer
from .tasks import check_due_books
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

# Configure logging
logger = logging.getLogger(__name__)


#  USER REGISTRATION

class RegisterView(generics.CreateAPIView):
    """
    Register a new user with basic details.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        try:
            logger.info("User registration initiated.")
            response = super().create(request, *args, **kwargs)
            logger.info(f"User '{response.data['username']}' registered successfully.")
            return response
        except Exception as e:
            logger.error(f"Error during user registration: {str(e)}")
            return Response({'error': 'User registration failed!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#  USER LOGIN
class LoginView(APIView):
    """
    Authenticate user and return JWT token.
    """
    def post(self, request):
        try:
            username = request.data.get('username')
            password = request.data.get('password')
            user = authenticate(username=username, password=password)

            if user:
                refresh = RefreshToken.for_user(user)
                logger.info(f"User '{username}' logged in successfully.")
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                })
            logger.warning(f"Invalid login attempt for user '{username}'.")
            return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return Response({'error': 'Login failed!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ADD A BOOK
class BookCreateView(generics.CreateAPIView):
    """
    Create a new book entry. Only admin/librarian can add.
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            if self.request.user.role not in ['admin', 'librarian']:
                logger.warning(f"Permission denied: User '{self.request.user.username}' tried to add a book.")
                return Response({'error': 'Permission Denied'}, status=status.HTTP_403_FORBIDDEN)
            serializer.save()
            logger.info(f"Book '{serializer.validated_data['title']}' added successfully by '{self.request.user.username}'.")
        except Exception as e:
            logger.error(f"Error adding book: {str(e)}")
            return Response({'error': 'Book creation failed!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# UPDATE/DELETE A BOOK
class BookUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Update or delete a book. Only admin/librarian can modify.
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        try:
            if self.request.user.role not in ['admin', 'librarian']:
                logger.warning(f"Permission denied: User '{self.request.user.username}' tried to update book.")
                return Response({'error': 'Permission Denied'}, status=status.HTTP_403_FORBIDDEN)
            serializer.save()
            logger.info(f"Book '{serializer.validated_data['title']}' updated successfully by '{self.request.user.username}'.")
        except Exception as e:
            logger.error(f"Error updating book: {str(e)}")
            return Response({'error': 'Book update failed!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_destroy(self, instance):
        try:
            if self.request.user.role not in ['admin', 'librarian']:
                logger.warning(f"Permission denied: User '{self.request.user.username}' tried to delete a book.")
                return Response({'error': 'Permission Denied'}, status=status.HTTP_403_FORBIDDEN)
            instance.delete()
            logger.info(f"Book '{instance.title}' deleted successfully by '{self.request.user.username}'.")
        except Exception as e:
            logger.error(f"Error deleting book: {str(e)}")
            return Response({'error': 'Book deletion failed!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# BORROW A BOOK
class BorrowBookView(APIView):
    """
    Borrow a book if copies are available. Members only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, book_id):
        try:
            book = Book.objects.get(id=book_id)
            if book.available_copies <= 0:
                logger.warning(f"Book '{book.title}' is out of stock for user '{request.user.username}'.")
                return Response({'error': 'No copies available'}, status=status.HTTP_400_BAD_REQUEST)

            borrowed_book = BorrowedBook.objects.create(
                user=request.user,
                book=book
            )
            book.available_copies -= 1
            book.save()
            logger.info(f"Book '{book.title}' borrowed successfully by '{request.user.username}'.")
            return Response({'message': 'Book borrowed successfully'}, status=status.HTTP_201_CREATED)
        except Book.DoesNotExist:
            logger.error(f"Book with ID '{book_id}' not found.")
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error borrowing book: {str(e)}")
            return Response({'error': 'Borrowing failed!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# RETURN A BOOK
class ReturnBookView(APIView):
    """
    Return a borrowed book. Members only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, book_id):
        try:
            borrowed_book = BorrowedBook.objects.get(book_id=book_id, user=request.user, returned=False)
            borrowed_book.returned = True
            borrowed_book.save()

            book = borrowed_book.book
            book.available_copies += 1
            book.save()
            logger.info(f"Book '{book.title}' returned successfully by '{request.user.username}'.")
            return Response({'message': 'Book returned successfully'}, status=status.HTTP_200_OK)
        except BorrowedBook.DoesNotExist:
            logger.warning(f"No borrowed book found for book ID '{book_id}' by user '{request.user.username}'.")
            return Response({'error': 'Borrowed book not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error returning book: {str(e)}")
            return Response({'error': 'Return failed!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#  LIST ALL BOOKS
class BookListView(generics.ListAPIView):
    """
    List all available books in the library.
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def list(self, request, *args, **kwargs):
        try:
            logger.info("Book list retrieved successfully.")
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error retrieving book list: {str(e)}")
            return Response({'error': 'Failed to retrieve book list!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# GET BOOK DETAILS
class BookDetailView(generics.RetrieveAPIView):
    """
    Retrieve details of a specific book.
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            logger.info(f"Book detail viewed for book ID '{self.get_object().id}'.")
            return super().retrieve(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error retrieving book details: {str(e)}")
            return Response({'error': 'Failed to retrieve book details!'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#  TRIGGER BACKGROUND TASK
@csrf_exempt
def trigger_due_books_task(request):
    """
    Triggers the check_due_books Celery task manually.
    """
    if request.method == "POST":
        try:
            logger.info("Triggering the check_due_books task...")
            task = check_due_books.delay()
            logger.info(f"Task triggered successfully! Task ID: {task.id}")
            return JsonResponse({'status': 'Task triggered successfully!', 'task_id': task.id})
        except Exception as e:
            logger.error(f"Error while triggering the task: {str(e)}")
            return JsonResponse({'error': 'Task triggering failed!'}, status=500)
    else:
        logger.warning("Invalid request method used to trigger task.")
        return JsonResponse({'error': 'Invalid request method'}, status=400)
