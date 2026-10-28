from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin

import datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.forms import inlineformset_factory
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from catalog.forms import RenewBookForm
from catalog.models import BookInstance

# Create your views here.
from .models import Book, Author, BookInstance, Genre, BookAuthor

def index(request):
    """View function for home page of site."""

    # Generate counts of some of the main objects
    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()

    # Available books (status = 'a')
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()

    # The 'all()' is implied by default.
    num_authors = Author.objects.count()
    
    # Number of visits to this view, as counted in the session variable.
    num_visits = request.session.get('num_visits', 0)
    num_visits += 1
    request.session['num_visits'] = num_visits
    
    num_genres = Genre.objects.filter().count()
    num_books_with_the = Book.objects.filter(title__icontains='the').count()

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_genres': num_genres,
        'num_books_with_the': num_books_with_the,
        'num_visits': num_visits,
    }

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context=context)

from django.views import generic

class BookListView(generic.ListView):
    model = Book
    paginate_by = 10
    
class BookDetailView(generic.DetailView):
    model = Book
    
class AuthorListView(generic.ListView):
    model = Author
    
class AuthorDetailView(generic.DetailView):
    model = Author
    
class LoanedBooksByUserListView(LoginRequiredMixin,generic.ListView):
    """Generic class-based view listing books on loan to current user."""
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return (
            BookInstance.objects.filter(borrower=self.request.user)
            .filter(status__exact='o')
            .order_by('due_back')
        )

class LoanedBooksAllListView(PermissionRequiredMixin, generic.ListView):
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_all.html'
    context_object_name = 'bookinstance_list'
    permission_required = 'catalog.can_mark_returned'

    def get_queryset(self):
        return BookInstance.objects.filter(status__exact='o').order_by('due_back')


@login_required
@permission_required('catalog.can_mark_returned', raise_exception=True)
def renew_book_librarian(request, pk):
    """Renew a specific borrowed book."""

    book_instance = get_object_or_404(BookInstance, pk=pk)

    if request.method == 'POST':
        form = RenewBookForm(request.POST)

        if form.is_valid():
            book_instance.due_back = form.cleaned_data['renewal_date']
            book_instance.save()

            return HttpResponseRedirect(reverse('all-borrowed'))

    else:
        proposed_renewal_date = (
            datetime.date.today() + datetime.timedelta(weeks=3)
        )
        form = RenewBookForm(
            initial={'renewal_date': proposed_renewal_date}
        )

    context = {
        'form': form,
        'book_instance': book_instance,
    }

    return render(
        request,
        'catalog/book_renew_librarian.html',
        context
    )

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Author

class AuthorCreate(PermissionRequiredMixin, CreateView):
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']
    initial = {'date_of_death': '11/11/2023'}
    permission_required = 'catalog.add_author'

class AuthorUpdate(PermissionRequiredMixin, UpdateView):
    model = Author
    # Not recommended (potential security issue if more fields added)
    fields = '__all__'
    permission_required = 'catalog.change_author'

class AuthorDelete(PermissionRequiredMixin, DeleteView):
    model = Author
    success_url = reverse_lazy('authors')
    permission_required = 'catalog.delete_author'

    def form_valid(self, form):
        try:
            self.object.delete()
            return HttpResponseRedirect(self.success_url)
        except Exception as e:
            return HttpResponseRedirect(
                reverse("author-delete", kwargs={"pk": self.object.pk})
            )

BookAuthorFormSet = inlineformset_factory(
    Book, BookAuthor, fields=['author', 'author_order'], extra=2)

class BookAuthorFormSetMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == 'POST':
            if 'author_formset' not in context:
                context['author_formset'] = BookAuthorFormSet(self.request.POST, instance=self.object)                
        
        else:
            context['author_formset'] = BookAuthorFormSet(instance=self.object)
        
        return context

    def form_valid(self, form):
        author_formset = BookAuthorFormSet(self.request.POST, instance=form.instance)
        if not author_formset.is_valid():
            return self.render_to_response(self.get_context_data( form=form, author_formset=author_formset))
        self.object = form.save()
        author_formset.instance = self.object
        author_formset.save()
        return HttpResponseRedirect(self.get_success_url())

class BookCreate(PermissionRequiredMixin, BookAuthorFormSetMixin, CreateView):
    model = Book
    fields = ['title', 'summary', 'isbn', 'genre', 'language']
    permission_required = 'catalog.add_book'


class BookUpdate(PermissionRequiredMixin, BookAuthorFormSetMixin, UpdateView):
    model = Book
    fields = ['title', 'summary', 'isbn', 'genre', 'language']
    permission_required = 'catalog.change_book'


class BookDelete(PermissionRequiredMixin, DeleteView):
    model = Book
    permission_required = 'catalog.delete_book'

    def get_success_url(self):
        return reverse('books')

    def form_valid(self, form):
        try:
            self.object.delete()
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            return HttpResponseRedirect(
                reverse('book-delete', kwargs={'pk': self.object.pk})
            )