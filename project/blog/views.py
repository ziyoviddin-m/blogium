from django.conf import settings
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from .models import Post
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import EmailPostForm
from django.core.mail import send_mail


def post_list(request):
    posts_list = Post.published.all()
    # Постраничная разбивка с 3 постами на страницу
    paginator = Paginator(posts_list, 3)
    page_number = request.GET.get('page', 1)

    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        #  Если page_number не целое число, то выдать первую страницу
        posts = paginator.page(1)
    except EmptyPage:
        # Если page_number находится вне диапазона, то выдать последнюю страницу
        posts = paginator.page(paginator.num_pages)

    return render(request, 'blog/post/list.html', {'posts': posts})



def post_detail(request, day, month, year, post):
    post = get_object_or_404(Post, status=Post.Status.PUBLISHED, slug=post, publish__year=year, publish__month=month, publish__day=day)
    return render(request, 'blog/post/detail.html', {'post': post})



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





