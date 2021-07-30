from django.shortcuts import render
from django.http import HttpResponseRedirect
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
from django.db.models import Sum
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))

def extract_answers(request):
   submitted_anwsers = []
   for key in request.POST:
       if key.startswith('choice'):
           submitted_anwsers.append(int(request.POST[key]))
   return submitted_anwsers

def submit(request, course_id):
    enrollment = Enrollment.objects.get(user=request.user, course=Course.objects.get(pk=course_id))
    submission = Submission.objects.create(enrollment=enrollment)
    submission.choices.set(extract_answers(request))
    return  HttpResponseRedirect(reverse(viewname='onlinecourse:result', args=(course_id, submission.choices.first().question.lesson.pk, submission.pk)))

def show_exam_result(request, course_id, lesson_id, submission_id):
    grade = 0
    
    course = Course.objects.get(pk=course_id)
    lesson = Lesson.objects.get(pk=lesson_id)
    
    submission = Submission.objects.get(pk=submission_id)
    selected_choices = submission.choices.all()

    questions = lesson.question_set.all()
    total_score = round(lesson.question_set.all().aggregate(Sum("grade"))["grade__sum"])
    
    for question in questions:
        if question.is_get_score(selected_choices):
            grade += question.grade

    params = {
        'grade': round(grade),
        'questions': questions,
        'lesson': lesson,
        'total_score': total_score,
        'selected_choices': selected_choices
    }
        
    return render(request , 'onlinecourse/exam_result_bootstrap.html' , params)
