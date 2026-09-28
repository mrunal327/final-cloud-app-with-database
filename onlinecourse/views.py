from django.shortcuts import render
from django.http import HttpResponseRedirect
from .models import Course, Enrollment, Submission, Choice
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging

logger = logging.getLogger(__name__)


def registration_request(request):
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html')

    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        login(request, user)

        return HttpResponseRedirect(
            reverse('onlinecourse:index')
        )


def login_request(request):
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_login_bootstrap.html')

    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(
                reverse('onlinecourse:index')
            )

        return render(
            request,
            'onlinecourse/user_login_bootstrap.html',
            {
                'message': 'Invalid username or password.'
            }
        )


def logout_request(request):
    logout(request)

    return HttpResponseRedirect(
        reverse('onlinecourse:index')
    )


def check_if_enrolled(user, course):
    if user.is_authenticated:
        return Enrollment.objects.filter(
            user=user,
            course=course
        ).exists()

    return False


class CourseListView(generic.ListView):
    model = Course
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course = self.object

        if self.request.user.is_authenticated:
            course.is_enrolled = check_if_enrolled(
                self.request.user,
                course
            )

        return context


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    if request.user.is_authenticated:
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course
        )

        if created:
            course.total_enrollment += 1
            course.save()

    return redirect(
        'onlinecourse:course_details',
        course_id
    )


def extract_answers(request):
    submitted_answers = []

    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_answers.append(choice_id)

    return submitted_answers


def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    if request.method == 'POST':
        submitted_answers = extract_answers(request)

        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=course
        ).first()

        if enrollment is None:
            return redirect(
                'onlinecourse:course_details',
                course_id=course.id
            )

        submission = Submission.objects.create(
            enrollment=enrollment
        )

        for choice_id in submitted_answers:
            try:
                choice = Choice.objects.get(pk=choice_id)
                submission.choices.add(choice)
            except Choice.DoesNotExist:
                pass

        return redirect(
            'onlinecourse:show_exam_result',
            course_id=course.id,
            submission_id=submission.id
        )

    return redirect(
        'onlinecourse:course_details',
        course_id=course.id
    )


def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)

    submission = get_object_or_404(
        Submission,
        pk=submission_id
    )

    questions = course.question_set.all()

    total_questions = questions.count()

    correct_answers = 0

    for question in questions:
        correct_choice = question.choice_set.filter(
            is_correct=True
        ).first()

        if correct_choice and submission.choices.filter(
            pk=correct_choice.id
        ).exists():
            correct_answers += 1

    if total_questions > 0:
        grade = (correct_answers / total_questions) * 100
    else:
        grade = 0

    return render(
        request,
        'onlinecourse/exam_result_bootstrap.html',
        {
            'course': course,
            'submission': submission,
            'grade': grade,
            'correct_answers': correct_answers,
            'total_questions': total_questions,
        }
    )