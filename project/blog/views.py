from django.conf import settings
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from .models import Post
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import *
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity


from taggit.models import Tag
from django.db.models import Count


def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])

    # Постраничная разбивка с 3 постами на страницу
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        #  Если page_number не целое число, то выдать первую страницу
        posts = paginator.page(1)
    except EmptyPage:
        # Если page_number находится вне диапазона, то выдать последнюю страницу
        posts = paginator.page(paginator.num_pages)

    return render(request, 'blog/post/list.html', {'posts': posts, 'tag': tag})



def post_detail(request, day, month, year, post):
    post = get_object_or_404(Post, status=Post.Status.PUBLISHED, 
                             slug=post, 
                             publish__year=year, 
                             publish__month=month,
                             publish__day=day)
    # Список активных комментариев к этому посту
    comments = post.comments.filter(active=True).order_by('-created')
    # Форма для комментирования пользователями
    form = CommentForm()

    # Список схожих постов
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags','-publish')[:4]

    context = {
        'post': post, 
        'form': form,
        'comments': comments,
        'similar_posts': similar_posts
    }
    return render(request, 'blog/post/detail.html', context)


def post_share(request, post_id):
    # Извлечь пост по идентификатору id
    post = get_object_or_404(Post, pk=post_id, status=Post.Status.PUBLISHED)
    
    sent = False
    
    if request.method == 'POST':
        # Форма была передана на обработку
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Поля формы успешно прошли валидацию
            cd = form.cleaned_data
            # отправляем электронное письмо
            post_url = request.build_absolute_uri(post.get_absolute_url)
            subject = f"{cd['name']}  recommends you read {post.title}"
            message = f"Read {post.title} at {post_url} {cd['name']}\'s comments: {cd['comments']}"
            # send_mail(subject, message, form.cleaned_data['email'], [cd['to']]) 
            send_mail(
                subject=subject, 
                message=message, 
                from_email=settings.EMAIL_HOST_USER, 
                recipient_list=[cd['to']], 
                fail_silently=False
            )
            sent = True
    else:
        form = EmailPostForm()
    context = {
        'post': post, 
        'form': form,
        'sent': sent
    }
    return render(request, 'blog/post/share.html', context)


@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id, status=Post.Status.PUBLISHED)

    comment = None
    # Комментарий был отправлен
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Создать объект класса Comment, не сохраняя его в базе данных
        comment = form.save(commit=False)
        # Назначить пост комментарию
        comment.post = post
        # Сохранить комментарий в базе данных
        comment.save()

    context = {
        'post': post, 
        'form': form,
        'comment': comment
    }
    return render(request, 'blog/post/comment.html', context)
        


def post_search(request):
    form = SeachForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SeachForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            search_vector = SearchVector('title', 'body')
            serch_query = SearchQuery(query)
            results = Post.published.annotate(similarity=TrigramSimilarity('title', query)).filter(similarity__gt=0.1).order_by('-similarity')

    # if 'query' in request.GET:
    #     form = SeachForm(request.GET)
    #     if form.is_valid():
    #         query = form.cleaned_data['query']
    #         search_vector = SearchVector('title', 'body')
    #         serch_query = SearchQuery(query)
    #         results = Post.published.annotate(search=search_vector, 
    #                                           rank=SearchRank(search_vector, serch_query)).filter(search=serch_query).order_by('-rank')

    context = {
        'form': form,
        'query': query,
        'results': results
        }
    return render(request, 'blog/post/search.html', context)



