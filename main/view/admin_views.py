import math
import os
import pickle
import logging
import threading
from datetime import datetime
import openpyxl
import traceback

import cv2
import numpy as np

try:
    import tensorflow as tf
except ImportError:
    tf = None
    
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password, make_password
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db import transaction
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404

try:
    from sklearn.svm import SVC
except ImportError:
    SVC = None
    
from django.urls import reverse
from django.views.generic.edit import CreateView
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView

from main.forms import BlogForm, EditBlogForm
from main.models import BlogPost

from main import facenet
from main.decorators import admin_required
from main.models import StaffInfo, StudentInfo, StaffRole, Role, Classroom, StudentClassDetails

try:
    from main.src.anti_spoof_predict import AntiSpoofPredict
except ImportError:
    AntiSpoofPredict = None
    
from main.models import BlogPost
from django.views import View
from django.shortcuts import render, redirect

# ======================== CẤU HÌNH NHẬN DIỆN KHUÔN MẶT ========================

# Setup logging
logger = logging.getLogger(__name__)

color = (255, 0, 0)
thickness = 2
max_images = 300
device_id = 0

CAPTURE_STATUS = 0   # trạng thái chụp ảnh (0=chưa chạy, 1=hoàn tất)
TRAIN_STATUS = 0     # trạng thái train model
CAPTURE_IN_PROGRESS = {}  # Dictionary to track which students are being captured

mode = 'TRAIN'  # 'TRAIN' or 'CLASSIFY'
data_dir = 'main/Dataset/FaceData/processed'
model = 'main/Models/20180402-114759.pb'          # file FaceNet .pb
classifier_filename = 'main/Models/facemodel.pkl' # file SVM sau khi train

# Cấu hình training
batch_size = 128
image_size = 160
min_nrof_images_per_class = 5
nrof_train_images_per_class = 20
use_split_dataset = False
seed = 666
use_split_dataset = False

batch_size = 90
image_size = 160
seed = 666
min_nrof_images_per_class = 20
nrof_train_images_per_class = 10


# ========================== BLOG / THÔNG BÁO ==========================

class AddBlog(SuccessMessageMixin, CreateView, ListView):
    form_class = BlogForm
    model = BlogPost
    template_name = "admin/admin_notification_management.html"
    context_object_name = 'blog_posts'

    def get_success_url(self):
        return reverse('admin_notification_view')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['blog_posts'] = BlogPost.objects.all()
        context['edit_form'] = EditBlogForm()
        return context


class BlogPostDeleteView(View):
    def get(self, request, pk, *args, **kwargs):
        blog_post = get_object_or_404(BlogPost, id=pk)
        blog_post.delete()
        return redirect('admin_notification_view')


class EditBlogView(View):
    template_name = 'admin/admin_edit_notification.html'

    def get(self, request, blog_post_id):
        blog_post_instance = get_object_or_404(BlogPost, id=blog_post_id)
        edit_form = EditBlogForm(instance=blog_post_instance)
        return render(request, self.template_name, {'edit_form': edit_form})

    def post(self, request, blog_post_id):
        blog_post_instance = get_object_or_404(BlogPost, id=blog_post_id)
        edit_form = EditBlogForm(request.POST, instance=blog_post_instance)
        if edit_form.is_valid():
            edit_form.save()
            return redirect('admin_notification_view')
        else:
            return render(request, self.template_name, {'edit_form': edit_form})


@admin_required
def admin_dashboard_view(request):
    blog_posts = BlogPost.objects.all()
    return render(request, 'admin/admin_home.html', {'blog_posts': blog_posts})


@admin_required
def admin_notification_view(request):
    blog_posts = BlogPost.objects.all()
    return render(request, 'admin/admin_notification_management.html', {'blog_posts': blog_posts})


# ========================== HỒ SƠ ADMIN ==========================

@admin_required
def admin_profile_view(request):
    id_admin = request.session['id_staff']
    admin = StaffInfo.objects.get(id_staff=id_admin)
    if request.method == 'POST':
        admin.staff_name = request.POST['admin_name']
        admin.email = request.POST['email']
        admin.phone = request.POST['phone']
        admin.address = request.POST['address']
        admin.birthday = datetime.strptime(request.POST['birthday'], '%d/%m/%Y').date()
        admin.save()
        messages.success(request, 'Thay đổi thông tin thành công.')

    context = {'admin': admin}
    return render(request, 'admin/admin_profile.html', context)


@admin_required
def admin_change_password_view(request):
    id_admin = request.session['id_staff']
    admin = StaffInfo.objects.get(id_staff=id_admin)

    if request.method == 'POST':
        old_password = request.POST['old_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        if check_password(old_password, admin.password):
            if new_password == confirm_password:
                admin.password = make_password(new_password)
                admin.save()
                update_session_auth_hash(request, admin)
                messages.success(request, 'Đổi mật khẩu thành công.')
            else:
                messages.error(request, 'Mật khẩu mới không khớp.')
        else:
            messages.error(request, 'Mật khẩu cũ không đúng.')

    return render(request, 'admin/admin_change_password.html')


# ========================== QUẢN LÝ SINH VIÊN ==========================

@admin_required
def admin_student_management_view(request):
    students = StudentInfo.objects.all()
    student_per_page = 10
    paginator = Paginator(students, student_per_page)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context = {
        'list_students': page,
    }
    return render(request, 'admin/admin_student_management.html', context)


@admin_required
def admin_student_add(request):
    if request.method == 'POST':
        id_student = request.POST['id_student']
        student_name = request.POST['student_name']
        email = request.POST['email']
        phone = request.POST['phone']
        address = request.POST['address']
        birthday = datetime.strptime(request.POST['birthday'], '%d/%m/%Y').date()

        PathImageFolder = request.POST['PathImageFolder']
        password = make_password(request.POST['id_student'])
        student = StudentInfo(
            id_student=id_student,
            student_name=student_name,
            email=email,
            phone=phone,
            address=address,
            birthday=birthday,
            PathImageFolder=PathImageFolder,
            password=password
        )
        student.save()
        messages.success(request, 'Thêm sinh viên thành công.')
        return redirect('admin_student_management')
    return render(request, 'admin/modal-popup/popup_add_student.html')


@admin_required
def admin_student_edit(request, id_student):
    student = StudentInfo.objects.get(id_student=id_student)
    context = {'student': student}
    if request.method == 'POST':
        student.student_name = request.POST['student_name_edit']
        student.email = request.POST['email_edit']
        student.phone = request.POST['phone_edit']
        student.address = request.POST['address_edit']
        student.birthday = datetime.strptime(request.POST['birthday_edit'], '%d/%m/%Y').date()
        student.PathImageFolder = request.POST['PathImageFolder_edit']
        student.save()
        messages.success(request, 'Thay đổi thông tin thành công.')
        return redirect('admin_student_management')
    return render(request, 'admin/modal-popup/popup_edit_student.html', context)


@admin_required
def admin_student_capture(request, id_student):
    student = StudentInfo.objects.get(id_student=id_student)
    context = {'student': student}
    if request.method == 'POST':
        student.student_name = request.POST['student_name_capture']
        student.email = request.POST['email_capture']
        student.phone = request.POST['phone_capture']
        student.address = request.POST['address_capture']
        student.birthday = datetime.strptime(request.POST['birthday_capture'], '%d/%m/%Y').date()
        student.PathImageFolder = request.POST['PathImageFolder_capture']
        student.save()
        
        messages.success(request, '✅ Chụp ảnh và lưu thông tin thành công. Vui lòng click "Train Model" để cập nhật mô hình nhận dạng.')
        return redirect('admin_student_management')
    return render(request, 'admin/modal-popup/popup_capture_student.html', context)


@admin_required
def admin_student_delete(request, id_student):
    StudentInfo.objects.filter(id_student=id_student).delete()

    # Xóa folder ảnh nếu có
    folder_path = f"./main/Dataset/FaceData/processed/{id_student}"
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        import shutil
        shutil.rmtree(folder_path)
        print(f"Folder '{folder_path}' and its contents deleted.")
    else:
        print(f"Folder '{folder_path}' does not exist.")

    return redirect('admin_student_management')


@admin_required
def admin_student_get_info(request, id_student):
    try:
        student = StudentInfo.objects.get(id_student=id_student)
        student_data = {
            'id_student': student.id_student,
            'student_name': student.student_name,
            'email': student.email,
            'phone': student.phone,
            'address': student.address,
            'birthday': student.birthday.strftime('%d/%m/%Y'),
            'PathImageFolder': student.PathImageFolder,
        }
        return JsonResponse({'student': student_data})
    except StudentInfo.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy học sinh'}, status=404)


# ========================== QUẢN LÝ GIẢNG VIÊN ==========================

@admin_required
def admin_lecturer_management_view(request):
    lecturer = StaffInfo.objects.filter(roles__name='Lecturer')
    per_page = 10
    paginator = Paginator(lecturer, per_page)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context = {
        'list_lecturers': page,
    }
    return render(request, 'admin/admin_lecturer_management.html', context)


@admin_required
def admin_lecturer_add(request):
    if request.method == 'POST':
        id_lecturer = request.POST['id_lecturer']
        staff_name = request.POST['lecturer_name']
        email = request.POST['email']
        phone = request.POST['phone']
        address = request.POST['address']
        birthday = datetime.strptime(request.POST['birthday'], '%d/%m/%Y').date()
        password = make_password(request.POST['id_lecturer'])
        lecturer = StaffInfo(
            id_staff=id_lecturer,
            staff_name=staff_name,
            email=email,
            phone=phone,
            address=address,
            birthday=birthday,
            password=password
        )
        lecturer.save()
        lecturer_role_obj, created = Role.objects.get_or_create(name='Lecturer')
        lecturer_role = StaffRole(staff=lecturer, role=lecturer_role_obj)
        lecturer_role.save()
        messages.success(request, 'Thêm giảng viên thành công.')
        return redirect('admin_lecturer_management')
    return render(request, 'admin/admin_add_lecturer.html')


@admin_required
def admin_lecturer_delete(request, id_staff):
    StaffInfo.objects.filter(id_staff=id_staff).delete()
    return redirect('admin_lecturer_management')


@admin_required
def admin_lecturer_edit(request, id_staff):
    lecturer = StaffInfo.objects.get(id_staff=id_staff)
    context = {'staff': lecturer}
    if request.method == 'POST':
        lecturer.staff_name = request.POST['lecturer_name']
        lecturer.email = request.POST['email']
        lecturer.phone = request.POST['phone']
        lecturer.address = request.POST['address']
        lecturer.birthday = datetime.strptime(request.POST['birthday'], '%d/%m/%Y').date()
        lecturer.save()
        messages.success(request, 'Thay đổi thông tin thành công.')
        return redirect('admin_lecturer_management')
    return render(request, 'admin/modal-popup/popup_edit_lecturer.html', context)


@admin_required
def admin_lecturer_get_info(request, id_staff):
    try:
        lecturer = StaffInfo.objects.get(id_staff=id_staff)
        staff_data = {
            'id_staff': lecturer.id_staff,
            'staff_name': lecturer.staff_name,
            'email': lecturer.email,
            'phone': lecturer.phone,
            'address': lecturer.address,
            'birthday': lecturer.birthday.strftime('%d/%m/%Y'),
        }
        return JsonResponse({'lecturer': staff_data})
    except StaffInfo.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy giảng viên'}, status=404)


# ========================== QUẢN LÝ LỊCH HỌC ==========================

@admin_required
def admin_schedule_management_view(request):
    schedule = Classroom.objects.all()
    schedule_per_page = 10
    paginator = Paginator(schedule, schedule_per_page)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    
    # Thêm danh sách giảng viên cho dropdown
    lecturers = StaffInfo.objects.filter(roles__name='Lecturer').distinct().order_by('id_staff')
    
    context = {
        'list_schedules': page,
        'lecturers': lecturers,
    }

    return render(request, 'admin/admin_schedule_management.html', context)


@admin_required
def admin_schedule_add(request):
    lecturers = StaffInfo.objects.filter(roles__name='Lecturer').distinct().order_by('id_staff')
    context = {'lecturers': lecturers}
    
    if request.method == 'POST':
        try:
            name = request.POST['name']
            begin_date = datetime.strptime(request.POST['begin_date'], '%d/%m/%Y').date()
            end_date = datetime.strptime(request.POST['end_date'], '%d/%m/%Y').date()
            day_of_week_begin = request.POST['day_of_week_begin']
            begin_time = request.POST['begin_time']
            end_time = request.POST['end_time']
            
            # Sửa lỗi: xử lý giảng viên đúng cách
            lecturer_id = request.POST.get('id_lecturer')
            lecturer = None
            if lecturer_id:
                try:
                    lecturer = StaffInfo.objects.get(id_staff=lecturer_id)
                except StaffInfo.DoesNotExist:
                    messages.error(request, f'Không tìm thấy giảng viên với ID: {lecturer_id}')
                    return render(request, 'admin/modal-popup/popup_add_schedule.html', context)
            
            schedule = Classroom(
                name=name,
                begin_date=begin_date,
                end_date=end_date,
                day_of_week_begin=day_of_week_begin,
                begin_time=begin_time,
                end_time=end_time,
                id_lecturer=lecturer  # Sửa: dùng lecturer object, không phải id_lecturer_id
            )
            schedule.save()
            messages.success(request, 'Thêm Thời Khóa Biểu thành công.')
            return redirect('admin_schedule_management')
            
        except ValueError as e:
            messages.error(request, f'Lỗi định dạng dữ liệu: {e}')
            return render(request, 'admin/modal-popup/popup_add_schedule.html', context)
        except Exception as e:
            messages.error(request, f'Lỗi khi thêm lớp học: {e}')
            return render(request, 'admin/modal-popup/popup_add_schedule.html', context)
            
    return render(request, 'admin/modal-popup/popup_add_schedule.html', context)


@admin_required
def admin_schedule_edit(request, id_classroom):
    schedule = Classroom.objects.get(id_classroom=id_classroom)
    lecturers = StaffInfo.objects.filter(roles__name='Lecturer').distinct().order_by('id_staff')
    
    context = {
        'schedule': schedule,
        'lecturers': lecturers,
    }
    
    if request.method == 'POST':
        try:
            schedule.name = request.POST['name']
            schedule.begin_date = datetime.strptime(request.POST['begin_date'], '%d/%m/%Y').date()
            schedule.end_date = datetime.strptime(request.POST['end_date'], '%d/%m/%Y').date()
            schedule.day_of_week_begin = request.POST['day_of_week_begin']
            schedule.begin_time = request.POST['begin_time']
            schedule.end_time = request.POST['end_time']
            
            # Sửa lỗi: phải là id_lecturer, không phải id_lecturer_id
            lecturer_id = request.POST.get('lecturer_name')
            if lecturer_id:
                try:
                    lecturer = StaffInfo.objects.get(id_staff=lecturer_id)
                    schedule.id_lecturer = lecturer
                except StaffInfo.DoesNotExist:
                    messages.error(request, f'Không tìm thấy giảng viên với ID: {lecturer_id}')
                    return render(request, 'admin/modal-popup/popup_edit_schedule.html', context)
            else:
                schedule.id_lecturer = None
            
            schedule.save()
            messages.success(request, 'Thay đổi thông tin thành công.')
            return redirect('admin_schedule_management')
            
        except ValueError as e:
            messages.error(request, f'Lỗi định dạng dữ liệu: {e}')
            return render(request, 'admin/modal-popup/popup_edit_schedule.html', context)
        except Exception as e:
            messages.error(request, f'Lỗi khi cập nhật: {e}')
            return render(request, 'admin/modal-popup/popup_edit_schedule.html', context)
            
    return render(request, 'admin/modal-popup/popup_edit_schedule.html', context)


@admin_required
def admin_schedule_delete(request, id_classroom):
    Classroom.objects.filter(id_classroom=id_classroom).delete()
    return redirect('admin_schedule_management')


@admin_required
def admin_schedule_get_info(request, id_classroom):
    try:
        schedule = Classroom.objects.get(id_classroom=id_classroom)
        if schedule.id_lecturer is None:
            lecturer_name = 'Hiện chưa có giảng viên phụ trách (Vui lòng thêm giảng viên)'
        else:
            lecturer_name = schedule.id_lecturer.staff_name
        schedule_data = {
            'id_classroom': schedule.id_classroom,
            'name': schedule.name,
            'begin_date': schedule.begin_date.strftime('%d/%m/%Y'),
            'end_date': schedule.end_date.strftime('%d/%m/%Y'),
            'day_of_week_begin': schedule.day_of_week_begin,
            'begin_time': schedule.begin_time,
            'end_time': schedule.end_time,
            'lecturer_name': lecturer_name,
        }
        return JsonResponse({'schedule': schedule_data})
    except Classroom.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy lớp học'}, status=404)


# ========================== QUẢN LÝ SV TRONG LỚP ==========================

@admin_required
def admin_list_classroom_student_view(request):
    classroom_per_page = 10
    page_number = request.GET.get('page')
    search_query = request.GET.get('q', '')
    list_classrooms = Classroom.objects.filter(
        Q(id_classroom__icontains=search_query) | Q(name__icontains=search_query)
    ).annotate(student_count=Count('studentclassdetails__id_student'))
    paginator = Paginator(list_classrooms, classroom_per_page)
    page = paginator.get_page(page_number)
    context = {'list_classrooms': page, 'search_query': search_query}
    return render(request, 'admin/admin_list_classroom_student_management.html', context)


@admin_required
def admin_list_student_in_classroom_view(request, classroom_id):
    classroom = Classroom.objects.get(pk=classroom_id)
    students_in_class = StudentClassDetails.objects.filter(id_classroom=classroom)
    student_per_page = 10
    page_number = request.GET.get('page')
    paginator = Paginator(students_in_class, student_per_page)
    page = paginator.get_page(page_number)
    context = {'students_in_class': page, 'classroom_id': classroom_id}
    return render(request, 'admin/admin_list_student_classroom_management.html', context)


@admin_required
def admin_list_student_in_class_add_list(request, classroom_id):
    if request.method == 'POST':
        file_path = request.FILES['file_path']
        try:
            classroom = Classroom.objects.get(id_classroom=classroom_id)
        except Classroom.DoesNotExist:
            return render(request, 'error/error_template.html', {'error_message': 'Lớp học không tồn tại.'})

        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
        list_id_student = [row[0].value for row in sheet.iter_rows(min_row=2, max_col=1)]

        with transaction.atomic():
            for id_student in list_id_student:
                try:
                    student = StudentInfo.objects.get(id_student=id_student)
                except StudentInfo.DoesNotExist:
                    student = StudentInfo(id_student=id_student)
                    student.save()

                if not StudentClassDetails.objects.filter(id_classroom=classroom, id_student=student).exists():
                    student_class_detail = StudentClassDetails(id_classroom=classroom, id_student=student)
                    student_class_detail.save()
        return redirect('admin_list_student_in_classroom', classroom_id)
    return render(request, 'admin/admin_list_student_classroom_management.html')


@admin_required
def admin_list_student_in_class_add(request, classroom_id):
    if request.method == 'POST':
        id_student = request.POST.get('id_student')
        if StudentClassDetails.objects.filter(id_classroom_id=classroom_id, id_student_id=id_student).exists():
            messages.warning(request, 'Sinh viên đã tồn tại trong lớp học.')
        else:
            student_in_class = StudentClassDetails(
                id_classroom_id=classroom_id,
                id_student_id=id_student
            )
            student_in_class.save()
            messages.success(request, 'Thêm sinh viên vào lớp học thành công.')
        return redirect('admin_list_student_in_classroom', classroom_id)
    return render(request, 'admin/modal-popup/popup_add_student_in_class.html')


@admin_required
def admin_list_student_in_class_delete(request, id_student, id_classroom):
    StudentClassDetails.objects.filter(id_student_id=id_student, id_classroom_id=id_classroom).delete()
    return redirect('admin_list_student_in_classroom', id_classroom)


@admin_required
def admin_list_student_in_class_delete_all(request, id_classroom):
    StudentClassDetails.objects.filter(id_classroom_id=id_classroom).delete()
    return redirect('admin_list_student_in_classroom', id_classroom)


# ========================== CHỤP ẢNH DỮ LIỆU ==========================

def capture(id, request):
    global CAPTURE_STATUS, CAPTURE_IN_PROGRESS
    
    # Đánh dấu rằng capture đang chạy cho student này
    if id not in CAPTURE_IN_PROGRESS:
        CAPTURE_IN_PROGRESS[id] = {'status': 0, 'count': 0}
    
    CAPTURE_IN_PROGRESS[id]['status'] = 0
    CAPTURE_IN_PROGRESS[id]['count'] = 0
    
    image_count = 0
    color = (0, 0, 255)
    thickness = 2
    frame_count = 0
    use_anti_spoof = False  # BẢO DÙNG ANTI-SPOOF VÌ NÓ BỊ HANG - CHỈ DÙNG CASCADE
    
    try:
        logger.info(f"Bắt đầu chụp ảnh cho sinh viên {id} - Chế độ: Haar Cascade (skip anti-spoof)")
        
        # Load Haar Cascade
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        if face_cascade.empty():
            logger.error("Lỗi load Haar Cascade")
            CAPTURE_IN_PROGRESS[id]['status'] = 0
            yield b"Error: Cannot load Haar Cascade"
            return
        
        capture = cv2.VideoCapture(0)
        if not capture.isOpened():
            logger.error("Không thể mở webcam")
            CAPTURE_IN_PROGRESS[id]['status'] = 0
            yield b"Error: Cannot open webcam"
            return
        
        # Set camera properties
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Giảm buffer để tránh delay
        capture.set(cv2.CAP_PROP_FPS, 30)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        output_dir = f"./main/Dataset/FaceData/processed/{id}"
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Output dir: {output_dir}")
        
        while image_count < 300:
            ret, frame = capture.read()
            frame_count += 1
            
            if not ret or frame is None:
                logger.debug(f"Frame {frame_count} invalid")
                continue
            
            try:
                # Resize frame for faster processing
                frame = cv2.resize(frame, (640, 480))
                
                # Detect face using Haar Cascade - KHÔNG BỊ HANG
                faces = face_cascade.detectMultiScale(frame, 1.3, 5)
                
                # Save face if detected
                if len(faces) > 0:
                    x, y, w, h = faces[0]
                    
                    # Validate coordinates
                    x = max(0, min(x, frame.shape[1]))
                    y = max(0, min(y, frame.shape[0]))
                    w = max(x, min(x + w, frame.shape[1]))
                    h = max(y, min(y + h, frame.shape[0]))
                    
                    if x < w and y < h:
                        cropped_face = frame[y:h, x:w]
                        
                        if cropped_face.size > 1600:  # 40x40 minimum
                            try:
                                cropped_face = cv2.resize(cropped_face, (160, 160))
                                image_filename = os.path.join(output_dir, f"{id}_{image_count}.jpg")
                                
                                if cv2.imwrite(image_filename, cropped_face):
                                    image_count += 1
                                    CAPTURE_IN_PROGRESS[id]['count'] = image_count
                                    
                                    if image_count % 100 == 0:
                                        logger.info(f"Chụp được {image_count}/300 ảnh")
                            except Exception as e:
                                logger.debug(f"Error saving face: {e}")
                                continue
                
                # Encode and send frame
                try:
                    display_frame = frame.copy()
                    cv2.putText(display_frame, f"Images: {image_count}/300", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # Draw detected faces
                    for (x, y, w, h) in faces:
                        cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    cv2.putText(display_frame, "[Haar Cascade Mode]", (10, 70),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                    
                    _, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if buffer is not None:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n\r\n')
                except Exception as e:
                    logger.debug(f"Error encoding frame: {e}")
                    continue
            
            except Exception as e:
                logger.error(f"Unexpected error in capture loop: {e}")
                continue
            
            if image_count >= 300:
                CAPTURE_IN_PROGRESS[id]['status'] = 1
                CAPTURE_STATUS = 1
                logger.info("✅ Hoàn thành chụp 300 ảnh")
                
                # Gửi frame cuối cùng để báo hoàn thành
                try:
                    display_frame = frame.copy()
                    cv2.putText(display_frame, "COMPLETED: 300/300", (50, 150),
                               cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
                    cv2.putText(display_frame, "Dang tren tac....", (50, 250),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
                    _, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if buffer is not None:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n\r\n')
                except:
                    pass
                
                break
    
    except Exception as e:
        logger.error(f"Fatal error in capture: {e}", exc_info=True)
        CAPTURE_IN_PROGRESS[id]['status'] = 0
        CAPTURE_STATUS = 0
    
    finally:
        try:
            if 'capture' in locals() and capture is not None:
                capture.release()
            cv2.destroyAllWindows()
            logger.info(f"✅ Capture hoàn tất. Tổng ảnh: {image_count}")
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")


# ========================== TRAIN MODEL FACENET + SVM ==========================

def split_dataset(dataset, min_nrof_images_per_class, nrof_train_images_per_class):
    train_set = []
    test_set = []
    for cls in dataset:
        paths = cls.image_paths
        if len(paths) >= min_nrof_images_per_class:
            np.random.shuffle(paths)
            train_set.append(facenet.ImageClass(cls.name, paths[:nrof_train_images_per_class]))
            test_set.append(facenet.ImageClass(cls.name, paths[nrof_train_images_per_class:]))
    return train_set, test_set


def main():
    """
    Train model FaceNet + SVM.
    Trả về (status, message) để hiển thị lên giao diện.
    """
    global TRAIN_STATUS
    TRAIN_STATUS = 0

    try:
        logger.info("=== Bắt đầu huấn luyện model ===")
        
        # 1. Kiểm tra file / thư mục
        logger.info("Kiểm tra dữ liệu...")
        if not os.path.exists(model):
            raise FileNotFoundError(f"Không tìm thấy file model pb: {model}")

        if not os.path.isdir(data_dir):
            raise FileNotFoundError(f"Không tìm thấy thư mục dữ liệu: {data_dir}")

        with tf.Graph().as_default():
            with tf.compat.v1.Session() as sess:
                np.random.seed(seed)

                if use_split_dataset:
                    dataset_tmp = facenet.get_dataset(data_dir)
                    train_set, test_set = split_dataset(
                        dataset_tmp,
                        min_nrof_images_per_class,
                        nrof_train_images_per_class
                    )
                    if mode == 'TRAIN':
                        dataset = train_set
                    elif mode == 'CLASSIFY':
                        dataset = test_set
                else:
                    dataset = facenet.get_dataset(data_dir)

                # Kiểm tra dữ liệu
                if not dataset:
                    raise ValueError(f"Không có dữ liệu trong thư mục: {data_dir}")

                for cls in dataset:
                    if len(cls.image_paths) == 0:
                        raise ValueError(f"Lớp '{cls.name}' không có ảnh")
                    if len(cls.image_paths) < min_nrof_images_per_class:
                        logger.warning(f"Lớp '{cls.name}' chỉ có {len(cls.image_paths)} ảnh (tối thiểu: {min_nrof_images_per_class})")

                paths, labels = facenet.get_image_paths_and_labels(dataset)

                num_classes = len(dataset)
                num_images = len(paths)
                logger.info(f"Số lớp: {num_classes}, Số ảnh: {num_images}")

                # 2. Load FaceNet
                logger.info("Load FaceNet model...")
                facenet.load_model(model)

                images_placeholder = tf.compat.v1.get_default_graph().get_tensor_by_name("input:0")
                embeddings = tf.compat.v1.get_default_graph().get_tensor_by_name("embeddings:0")
                phase_train_placeholder = tf.compat.v1.get_default_graph().get_tensor_by_name("phase_train:0")
                embedding_size = embeddings.get_shape()[1]
                logger.info(f"Embedding size: {embedding_size}")

                # 3. Tính embedding
                logger.info("Tính embedding cho ảnh...")
                nrof_images = len(paths)
                nrof_batches_per_epoch = int(math.ceil(1.0 * nrof_images / batch_size))
                emb_array = np.zeros((nrof_images, embedding_size))
                
                for i in range(nrof_batches_per_epoch):
                    start_index = i * batch_size
                    end_index = min((i + 1) * batch_size, nrof_images)
                    paths_batch = paths[start_index:end_index]
                    
                    try:
                        images = facenet.load_data(paths_batch, False, False, image_size)
                        feed_dict = {images_placeholder: images, phase_train_placeholder: False}
                        emb_array[start_index:end_index, :] = sess.run(embeddings, feed_dict=feed_dict)
                        
                        progress = (i + 1) / nrof_batches_per_epoch * 100
                        if (i + 1) % max(1, nrof_batches_per_epoch // 10) == 0:
                            logger.info(f"  [{progress:.1f}%] {end_index}/{nrof_images}")
                    except Exception as e:
                        logger.error(f"Lỗi xử lý ảnh {start_index}-{end_index}: {e}")
                        raise

                logger.info("Embedding hoàn tất!")

                # 4. Train SVM
                classifier_filename_exp = os.path.expanduser(classifier_filename)
                
                if mode == 'TRAIN':
                    logger.info("Huấn luyện SVM classifier...")
                    clf = SVC(kernel='linear', probability=True, verbose=1)
                    clf.fit(emb_array, labels)
                    logger.info("SVM training hoàn tất!")

                    class_names = [cls.name.replace('_', ' ') for cls in dataset]

                    # Tạo thư mục nếu chưa có
                    os.makedirs(os.path.dirname(classifier_filename_exp), exist_ok=True)
                    
                    with open(classifier_filename_exp, 'wb') as outfile:
                        pickle.dump((clf, class_names), outfile)
                    
                    logger.info(f"Model đã lưu: {classifier_filename_exp}")

        TRAIN_STATUS = 1
        output_string = (
            f'✅ Huấn luyện thành công!\n\n'
            f'📊 Tóm tắt:\n'
            f'  • Số lớp: {num_classes}\n'
            f'  • Số ảnh: {num_images}\n'
            f'  • Embedding size: {embedding_size}\n'
            f'  • Model: {classifier_filename}\n\n'
            f'🎉 Sẵn sàng sử dụng!'
        )
        logger.info("=== Huấn luyện model thành công ===")
        return TRAIN_STATUS, output_string

    except Exception as e:
        logger.error("LỖI KHI TRAIN MODEL:", exc_info=True)
        print("LỖI KHI TRAIN MODEL:")
        traceback.print_exc()
        TRAIN_STATUS = 0
        error_msg = f'❌ Lỗi khi train model: {str(e)}\n\nVui lòng kiểm tra:\n' \
                   f'  • Có đủ ảnh trong thư mục {data_dir} không?\n' \
                   f'  • File model {model} có tồn tại không?\n' \
                   f'  • Xem chi tiết lỗi ở terminal'
        return 0, error_msg


@admin_required
def train(request):
    status, message = main()
    # Luôn trả về JSON hợp lệ để JS không bị lỗi "Unexpected token <"
    return JsonResponse({'status': status, 'message': message})


# ========================== STREAM VIDEO / TRẠNG THÁI ==========================

@admin_required
def live_video_feed(request, id_student):
    return StreamingHttpResponse(
        capture(id_student, request),
        content_type="multipart/x-mixed-replace;boundary=frame"
    )


@admin_required
def check_capture_status(request):
    print("CAPTURE_STATUS =", CAPTURE_STATUS)
    return JsonResponse({'capture_status': CAPTURE_STATUS})

# ========================== QUẢN LÝ MẬT KHẨU ==========================

@admin_required
def admin_student_password_view(request, id_student):
    """Xem và đổi mật khẩu sinh viên"""
    student = get_object_or_404(StudentInfo, id_student=id_student)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        print(f"DEBUG: Password change request for student {id_student}, action: {action}")
        
        if action == 'change_password':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            print(f"DEBUG: New password length: {len(new_password) if new_password else 0}")
            print(f"DEBUG: Passwords match: {new_password == confirm_password}")
            
            if not new_password:
                messages.error(request, 'Vui lòng nhập mật khẩu mới.')
                return redirect('admin_student_password', id_student=id_student)
            
            if new_password != confirm_password:
                messages.error(request, 'Mật khẩu xác nhận không khớp.')
                return redirect('admin_student_password', id_student=id_student)
            
            if len(new_password) < 6:
                messages.error(request, 'Mật khẩu phải có ít nhất 6 ký tự.')
                return redirect('admin_student_password', id_student=id_student)
            
            # Cập nhật mật khẩu
            old_password = student.password
            student.password = make_password(new_password)
            student.save()
            
            print(f"DEBUG: Password updated for student {id_student}")
            print(f"DEBUG: Old password hash: {old_password[:20]}...")
            print(f"DEBUG: New password hash: {student.password[:20]}...")
            
            messages.success(request, f'Đã cập nhật mật khẩu cho sinh viên {student.student_name}.')
            return redirect('admin_student_management')
    
    context = {
        'student': student,
        'current_password_display': '••••••••'  # Không hiển thị mật khẩu thật
    }
    return render(request, 'admin/student_password.html', context)


@admin_required
def admin_lecturer_password_view(request, id_staff):
    """Xem và đổi mật khẩu giảng viên"""
    lecturer = get_object_or_404(StaffInfo, id_staff=id_staff)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        print(f"DEBUG: Password change request for lecturer {id_staff}, action: {action}")
        
        if action == 'change_password':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            print(f"DEBUG: New password length: {len(new_password) if new_password else 0}")
            print(f"DEBUG: Passwords match: {new_password == confirm_password}")
            
            if not new_password:
                messages.error(request, 'Vui lòng nhập mật khẩu mới.')
                return redirect('admin_lecturer_password', id_staff=id_staff)
            
            if new_password != confirm_password:
                messages.error(request, 'Mật khẩu xác nhận không khớp.')
                return redirect('admin_lecturer_password', id_staff=id_staff)
            
            if len(new_password) < 6:
                messages.error(request, 'Mật khẩu phải có ít nhất 6 ký tự.')
                return redirect('admin_lecturer_password', id_staff=id_staff)
            
            # Cập nhật mật khẩu
            old_password = lecturer.password
            lecturer.password = make_password(new_password)
            lecturer.save()
            
            print(f"DEBUG: Password updated for lecturer {id_staff}")
            print(f"DEBUG: Old password hash: {old_password[:20]}...")
            print(f"DEBUG: New password hash: {lecturer.password[:20]}...")
            
            messages.success(request, f'Đã cập nhật mật khẩu cho giảng viên {lecturer.staff_name}.')
            return redirect('admin_lecturer_management')
    
    context = {
        'lecturer': lecturer,
        'current_password_display': '••••••••'  # Không hiển thị mật khẩu thật
    }
    return render(request, 'admin/lecturer_password.html', context)


@admin_required
def admin_reset_password(request):
    """Reset mật khẩu hàng loạt"""
    if request.method == 'POST':
        user_type = request.POST.get('user_type')
        user_ids = request.POST.getlist('user_ids')
        default_password = request.POST.get('default_password', '123456')
        
        if not user_ids:
            messages.error(request, 'Vui lòng chọn ít nhất một người dùng.')
            return redirect('admin_reset_password')
        
        hashed_password = make_password(default_password)
        updated_count = 0
        
        try:
            if user_type == 'student':
                updated_count = StudentInfo.objects.filter(
                    id_student__in=user_ids
                ).update(password=hashed_password)
                
            elif user_type == 'lecturer':
                updated_count = StaffInfo.objects.filter(
                    id_staff__in=user_ids
                ).update(password=hashed_password)
            
            messages.success(request, 
                f'Đã reset mật khẩu cho {updated_count} {user_type}. '
                f'Mật khẩu mới: {default_password}'
            )
            
        except Exception as e:
            messages.error(request, f'Lỗi khi reset mật khẩu: {str(e)}')
    
    # Lấy danh sách sinh viên và giảng viên
    students = StudentInfo.objects.all().order_by('id_student')
    lecturers = StaffInfo.objects.filter(roles__name='Lecturer').order_by('id_staff')
    
    context = {
        'students': students,
        'lecturers': lecturers
    }
    return render(request, 'admin/reset_password.html', context)


@admin_required
def test_password_form(request, id_student):
    """Test password form for debugging"""
    student = get_object_or_404(StudentInfo, id_student=id_student)
    
    if request.method == 'POST':
        print(f"DEBUG TEST: POST request received")
        print(f"DEBUG TEST: POST data: {request.POST}")
        
        action = request.POST.get('action')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        print(f"DEBUG TEST: action={action}, new_password={new_password}, confirm_password={confirm_password}")
        
        if action == 'change_password' and new_password:
            student.password = make_password(new_password)
            student.save()
            messages.success(request, f'TEST: Password changed successfully for {student.student_name}!')
        else:
            messages.error(request, 'TEST: Invalid form data')
    
    context = {
        'student': student
    }
    return render(request, 'admin/test_password_form.html', context)


@admin_required
def get_student_password(request, id_student):
    """API endpoint để lấy mật khẩu thực của sinh viên"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    try:
        student = get_object_or_404(StudentInfo, id_student=id_student)
        
        # Tìm mật khẩu gốc từ database
        # Vì mật khẩu đã được hash, chúng ta cần tìm cách lấy mật khẩu gốc
        # Thông thường, mật khẩu gốc không thể được khôi phục từ hash
        # Nhưng nếu có lưu trữ riêng hoặc có pattern, chúng ta có thể thử
        
        # Giả sử mật khẩu mặc định là ID sinh viên hoặc một pattern cố định
        # Bạn có thể thay đổi logic này theo yêu cầu
        default_passwords = [
            id_student,  # Thử ID sinh viên
            '123456',    # Mật khẩu mặc định
            'password',  # Mật khẩu phổ biến
            f'sv{id_student}',  # Pattern sv + ID
            student.student_name.lower().replace(' ', ''),  # Tên không dấu
        ]
        
        from django.contrib.auth.hashers import check_password
        
        actual_password = None
        for pwd in default_passwords:
            if check_password(pwd, student.password):
                actual_password = pwd
                break
        
        if actual_password:
            return JsonResponse({
                'success': True, 
                'password': actual_password,
                'note': 'Mật khẩu được tìm thấy từ pattern phổ biến'
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'Không thể xác định mật khẩu gốc',
                'password_hash': student.password[:50] + '...',
                'note': 'Mật khẩu đã được hash và không thể khôi phục'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def get_lecturer_password(request, id_staff):
    """API endpoint để lấy mật khẩu thực của giảng viên"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    try:
        lecturer = get_object_or_404(StaffInfo, id_staff=id_staff)
        
        # Tương tự như sinh viên, thử các pattern phổ biến
        default_passwords = [
            id_staff,    # Thử ID giảng viên
            '123456',    # Mật khẩu mặc định
            'password',  # Mật khẩu phổ biến
            f'gv{id_staff}',  # Pattern gv + ID
            lecturer.staff_name.lower().replace(' ', ''),  # Tên không dấu
        ]
        
        from django.contrib.auth.hashers import check_password
        
        actual_password = None
        for pwd in default_passwords:
            if check_password(pwd, lecturer.password):
                actual_password = pwd
                break
        
        if actual_password:
            return JsonResponse({
                'success': True, 
                'password': actual_password,
                'note': 'Mật khẩu được tìm thấy từ pattern phổ biến'
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'Không thể xác định mật khẩu gốc',
                'password_hash': lecturer.password[:50] + '...',
                'note': 'Mật khẩu đã được hash và không thể khôi phục'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@admin_required
def demo_password_view(request):
    """Demo page for password viewing feature"""
    return render(request, 'admin/demo_password_view.html')