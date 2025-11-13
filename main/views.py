from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from main.models import StaffInfo
# Nếu bạn có StudentInfo, bỏ comment dòng dưới:
# from main.models import StudentInfo

import csv


def home(request):
    if 'id_staff' in request.session:
        if 'Admin' in request.session['staff_role']:
            return redirect('admin_dashboard')
        elif 'Lecturer' in request.session['staff_role']:
            return redirect('lecturer_dashboard')

    if 'id_student' in request.session:
        return redirect('student_dashboard')

    return render(request, 'choose_login.html')


# Map role -> dashboard name
role_to_dashboard = {
    'Admin': 'admin_dashboard',
    'Lecturer': 'lecturer_dashboard',
    'Staff': 'staff_dashboard'
}


def login_view(request):
    """
    Đăng nhập cho Staff (Admin/Lecturer/Staff). Lưu session:
        - id_staff
        - staff_role: list vai trò
    """
    if 'id_staff' in request.session:
        if 'Admin' in request.session['staff_role']:
            return redirect('admin_dashboard')
        elif 'Lecturer' in request.session['staff_role']:
            return redirect('lecturer_dashboard')

    error_message = None

    if request.method == 'POST':
        id_staff = request.POST.get('id_staff', '').strip()
        password = request.POST.get('password', '')

        try:
            lecturer = StaffInfo.objects.get(id_staff=id_staff)
            if check_password(password, lecturer.password):
                user_roles = lecturer.roles.all()
                request.session['id_staff'] = id_staff
                request.session['staff_role'] = [role.name for role in user_roles]

                # Điều hướng theo vai trò
                for role in user_roles:
                    if role.name in role_to_dashboard:
                        return redirect(role_to_dashboard[role.name])

                error_message = "Vai trò không hợp lệ."
            else:
                error_message = "Tên đăng nhập hoặc mật khẩu không đúng."
        except StaffInfo.DoesNotExist:
            error_message = "Tên đăng nhập hoặc mật khẩu không đúng."

    return render(request, 'login.html', {'error_message': error_message})


def logout_view(request):
    request.session.clear()
    return redirect('choose_login')


def error_403_view(request):
    return render(request, 'error/error-403.html')


def hash_password(request):
    """
    Công cụ băm mật khẩu thủ công (phục vụ tạo tài khoản).
    """
    if request.method == 'POST':
        password = request.POST.get('password', '')
        hashed = make_password(password)
        return render(request, 'hash_password.html', {'hash_password': hashed})
    return render(request, 'hash_password.html')


# =========================
#  PHẦN BỔ SUNG CHỨC NĂNG
# =========================

def _get_current_account_info(request):
    """
    Trả về dict thông tin tài khoản hiện tại từ session:
        {
            'type': 'staff'|'student'|None,
            'username': ...,
            'email': ... (nếu có),
            'created_time': datetime,
            'display_name': ... (nếu cần),
        }
    Ưu tiên dùng các field:
        - created_at (DateTimeField(auto_now_add=True)) nếu model có
        - user.date_joined nếu có user OneToOne
        - fallback timezone.now()
    """
    info = {
        'type': None,
        'username': None,
        'email': '',
        'created_time': None,
        'display_name': ''
    }

    # ---- Staff đăng nhập ----
    if 'id_staff' in request.session:
        try:
            staff = StaffInfo.objects.select_related().get(id_staff=request.session['id_staff'])
            info['type'] = 'staff'
            # Sửa các field dưới nếu model của bạn khác tên:
            info['username'] = getattr(staff, 'id_staff', '')
            info['email'] = getattr(staff, 'email', '') if hasattr(staff, 'email') else ''

            # created_at ưu tiên
            created = getattr(staff, 'created_at', None)

            # nếu có liên kết User (OneToOne) thì dùng date_joined
            if not created and hasattr(staff, 'user') and getattr(staff, 'user', None):
                created = getattr(staff.user, 'date_joined', None)

            info['created_time'] = created or timezone.now()

            # hiển thị tên nếu có
            full_name = ''
            if hasattr(staff, 'full_name'):
                full_name = staff.full_name
            elif hasattr(staff, 'first_name') or hasattr(staff, 'last_name'):
                fn = getattr(staff, 'first_name', '') or ''
                ln = getattr(staff, 'last_name', '') or ''
                full_name = (fn + ' ' + ln).strip()
            info['display_name'] = full_name or info['username']

            return info
        except StaffInfo.DoesNotExist:
            pass

    # ---- Student đăng nhập (nếu bạn có model StudentInfo) ----
    if 'id_student' in request.session:
        try:
            # Bỏ comment nếu có StudentInfo:
            # student = StudentInfo.objects.select_related().get(id_student=request.session['id_student'])
            # info['type'] = 'student'
            # info['username'] = getattr(student, 'id_student', '')
            # info['email'] = getattr(student, 'email', '') if hasattr(student, 'email') else ''
            # created = getattr(student, 'created_at', None)
            # if not created and hasattr(student, 'user') and getattr(student, 'user', None):
            #     created = getattr(student.user, 'date_joined', None)
            # info['created_time'] = created or timezone.now()
            # full_name = getattr(student, 'full_name', '') if hasattr(student, 'full_name') else ''
            # info['display_name'] = full_name or info['username']
            # return info
            pass
        except Exception:
            pass

    # Không có session hợp lệ
    return info


def account_created_time(request):
    """
    API nho nhỏ (JSON): trả về mốc thời gian tạo tài khoản đang đăng nhập.
    Có thể gọi để hiển thị ở dashboard bằng AJAX nếu muốn.
    """
    info = _get_current_account_info(request)
    if not info['type']:
        return JsonResponse({'ok': False, 'message': 'Chưa đăng nhập'}, status=401)

    return JsonResponse({
        'ok': True,
        'type': info['type'],
        'username': info['username'],
        'created_time': timezone.localtime(info['created_time']).strftime("%Y-%m-%d %H:%M:%S")
    })


def export_my_account_csv(request):
    """
    Tải xuống CSV thông tin tài khoản (tên, email, vai trò, thời gian tạo).
    Dùng được cho cả staff và student (nếu có model StudentInfo).
    """
    info = _get_current_account_info(request)
    if not info['type']:
        # Nếu chưa đăng nhập, chuyển về trang chọn đăng nhập
        return redirect('choose_login')

    filename = f"{info['type']}_account_{info['username']}.csv"
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)

    # Header
    writer.writerow(["username", "email", "type", "created_time"])

    # created_time định dạng localtime
    created_str = timezone.localtime(info['created_time']).strftime("%Y-%m-%d %H:%M:%S")

    writer.writerow([
        info['username'],
        info['email'],
        info['type'],
        created_str
    ])
    return response
