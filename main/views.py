from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from main.models import StaffInfo, StudentInfo, BlogPost

import csv


def home(request):
    """
    Chọn trang đăng nhập ban đầu.
    Nếu đã đăng nhập rồi thì tự redirect về dashboard tương ứng.
    """
    if 'id_staff' in request.session:
        if 'Admin' in request.session['staff_role']:
            return redirect('admin_dashboard')
        elif 'Lecturer' in request.session['staff_role']:
            return redirect('lecturer_dashboard')

    if 'id_student' in request.session:
        return redirect('student_dashboard')

    # Lấy các bài viết blog để hiển thị
    blog_posts = BlogPost.objects.all().order_by('-created_at')[:5]  # Lấy 5 bài mới nhất
    
    return render(request, 'choose_login.html', {'blog_posts': blog_posts})


def blog_detail(request, blog_id):
    """
    Hiển thị chi tiết bài viết blog.
    """
    blog_post = get_object_or_404(BlogPost, id=blog_id)
    return render(request, 'blog_detail.html', {'blog_post': blog_post})


def test_admin_login(request):
    """Test admin login without authentication"""
    from main.models import StaffInfo, Role
    
    # Set session manually for testing
    request.session['id_staff'] = 'admin'
    request.session['staff_role'] = ['Admin']
    
    return redirect('admin_dashboard')


# Map role -> dashboard name
role_to_dashboard = {
    'Admin': 'admin_dashboard',
    'Lecturer': 'lecturer_dashboard',
    'Staff': 'staff_dashboard',
}


def login_view(request):
    """
    Đăng nhập cho Staff (Admin/Lecturer/Staff).
    Lưu session:
        - id_staff
        - staff_role: list vai trò
    """
    # Nếu đã login staff rồi thì không cho vào lại trang login
    if 'id_staff' in request.session:
        if 'Admin' in request.session['staff_role']:
            return redirect('admin_dashboard')
        elif 'Lecturer' in request.session['staff_role']:
            return redirect('lecturer_dashboard')

    error_message = None

    if request.method == 'POST':
        id_staff = request.POST.get('id_staff', '').strip()
        password = request.POST.get('password', '')

        print(f"DEBUG: Login attempt - ID: {id_staff}, Password: {password}")  # Debug

        try:
            staff = StaffInfo.objects.get(id_staff=id_staff)
            print(f"DEBUG: Found staff: {staff.staff_name}")  # Debug
            
            if check_password(password, staff.password):
                print("DEBUG: Password correct")  # Debug
                user_roles = staff.roles.all()
                print(f"DEBUG: User roles: {[r.name for r in user_roles]}")  # Debug

                # Lưu thông tin vào session
                request.session['id_staff'] = id_staff
                request.session['staff_role'] = [role.name for role in user_roles]

                # Điều hướng theo vai trò
                for role in user_roles:
                    if role.name in role_to_dashboard:
                        print(f"DEBUG: Redirecting to {role_to_dashboard[role.name]}")  # Debug
                        return redirect(role_to_dashboard[role.name])

                error_message = "Vai trò không hợp lệ."
            else:
                print("DEBUG: Password incorrect")  # Debug
                error_message = "Tên đăng nhập hoặc mật khẩu không đúng."
        except StaffInfo.DoesNotExist:
            print("DEBUG: Staff not found")  # Debug
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


# ============================================================
#        LẤY THÔNG TIN TÀI KHOẢN HIỆN TẠI (STAFF & STUDENT)
# ============================================================

def _get_current_account_info(request):
    """
    Trả về dict thông tin tài khoản hiện tại từ session:
        {
            'type': 'staff' | 'student' | None,
            'username': ...,
            'email': ...,
            'created_time': datetime,
            'display_name': ...,
        }
    Ưu tiên các field:
        - created_at trong model (auto_now_add=True)
    """

    info = {
        'type': None,
        'username': None,
        'email': '',
        'created_time': None,
        'display_name': '',
    }

    # ---------- STAFF ----------
    if 'id_staff' in request.session:
        try:
            staff = StaffInfo.objects.get(id_staff=request.session['id_staff'])

            info['type'] = 'staff'
            info['username'] = staff.id_staff
            info['email'] = staff.email

            created = getattr(staff, 'created_at', None)
            info['created_time'] = created or timezone.now()

            info['display_name'] = staff.staff_name
            return info
        except StaffInfo.DoesNotExist:
            pass

    # ---------- STUDENT ----------
    if 'id_student' in request.session:
        try:
            student = StudentInfo.objects.get(id_student=request.session['id_student'])

            info['type'] = 'student'
            info['username'] = student.id_student
            info['email'] = student.email

            created = getattr(student, 'created_at', None)
            info['created_time'] = created or timezone.now()

            info['display_name'] = student.student_name
            return info
        except StudentInfo.DoesNotExist:
            pass

    return info


def account_created_time(request):
    """
    API JSON nhỏ: trả về mốc thời gian tạo tài khoản đang đăng nhập.
    (nếu muốn gọi AJAX ở dashboard thì dùng cái này)
    """
    info = _get_current_account_info(request)
    if not info['type']:
        return JsonResponse({'ok': False, 'message': 'Chưa đăng nhập'}, status=401)

    return JsonResponse({
        'ok': True,
        'type': info['type'],
        'username': info['username'],
        'created_time': timezone.localtime(info['created_time']).strftime("%Y-%m-%d %H:%M:%S"),
    })


# ============================================================
#            XUẤT FILE CSV ĐÚNG ĐỊNH DẠNG HIỂN THỊ
# ============================================================

def export_my_account_csv(request):
    """
    Tải xuống CSV thông tin tài khoản (tên, email, type, thời gian tạo + thời gian đã hoạt động)
    với format giống như trên giao diện:
    "Tài khoản được tạo lúc: 17:08, 03/11/2025 (Đã hoạt động: 26 ngày 22 giờ 27 phút 54 giây)".
    Hỗ trợ cả staff & student.
    """
    info = _get_current_account_info(request)
    if not info['type']:
        # Nếu chưa đăng nhập, đưa về trang chọn đăng nhập
        return redirect('choose_login')

    # Thời điểm tạo & hiện tại (localtime)
    created_local = timezone.localtime(info['created_time'])
    now_local = timezone.localtime(timezone.now())

    # Tính khoảng thời gian hoạt động
    delta = now_local - created_local
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0

    days = total_seconds // (24 * 3600)
    total_seconds %= (24 * 3600)
    hours = total_seconds // 3600
    total_seconds %= 3600
    minutes = total_seconds // 60
    seconds = total_seconds % 60

    created_str_view = created_local.strftime("%H:%M, %d/%m/%Y")
    lifetime_str = f"{days} ngày {hours} giờ {minutes} phút {seconds} giây"
    full_text = f"Tài khoản được tạo lúc: {created_str_view} (Đã hoạt động: {lifetime_str})"

    filename = f"{info['type']}_account_{info['username']}.csv"

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    # ✅ f-string đã đóng đúng dấu nháy
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)

    # Header
    writer.writerow(["username", "email", "type", "created_time"])

    # Dòng dữ liệu (created_time chứa chuỗi full_text đẹp như trên web)
    writer.writerow([
        info['username'],
        info['email'],
        info['type'],
        full_text,
    ])

    return response
