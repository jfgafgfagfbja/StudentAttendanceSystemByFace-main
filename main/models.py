"""Các mô hình cho hệ thống điểm danh khuôn mặt.

Module này định nghĩa các mô hình Django cho:
- Thông tin giáo viên/nhân viên
- Vai trò người dùng
- Thông tin sinh viên
- Thông tin lớp học
- Điểm danh
- Bài viết blog
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from ckeditor_uploader.fields import RichTextUploadingField


class StaffInfo(models.Model):
    """Mô hình thông tin giáo viên/nhân viên."""

    id_staff = models.CharField(max_length=10, primary_key=True, verbose_name="Mã giáo viên")
    staff_name = models.TextField(verbose_name="Tên giáo viên")
    email = models.TextField(verbose_name="Email")
    phone = models.TextField(verbose_name="Số điện thoại")
    address = models.TextField(verbose_name="Địa chỉ")
    birthday = models.DateField(verbose_name="Ngày sinh")
    password = models.TextField(verbose_name="Mật khẩu")
    roles = models.ManyToManyField(
        'Role',
        through='StaffRole',
        related_name='staff_role',
        verbose_name="Vai trò"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo tài khoản"
    )

    class Meta:
        verbose_name = "Thông tin giáo viên"
        verbose_name_plural = "Thông tin giáo viên"

    def __str__(self):
        return self.staff_name


class Role(models.Model):
    """Mô hình vai trò người dùng."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20, unique=True, verbose_name="Tên vai trò")

    class Meta:
        verbose_name = "Vai trò"
        verbose_name_plural = "Vai trò"

    def __str__(self):
        return self.name


class StaffRole(models.Model):
    """Mô hình gán vai trò cho giáo viên."""

    staff = models.ForeignKey(
        StaffInfo,
        on_delete=models.CASCADE,
        verbose_name="Giáo viên"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        verbose_name="Vai trò"
    )

    class Meta:
        verbose_name = "Vai trò giáo viên"
        verbose_name_plural = "Vai trò giáo viên"
        unique_together = ('staff', 'role')

    def __str__(self):
        return f"{self.staff.staff_name} - {self.role.name}"


class StudentInfo(models.Model):
    """Mô hình thông tin sinh viên."""

    id_student = models.CharField(max_length=10, primary_key=True, verbose_name="Mã sinh viên")
    student_name = models.TextField(verbose_name="Tên sinh viên")
    email = models.TextField(verbose_name="Email")
    phone = models.TextField(verbose_name="Số điện thoại")
    address = models.TextField(verbose_name="Địa chỉ")
    birthday = models.DateField(verbose_name="Ngày sinh")
    PathImageFolder = models.TextField(verbose_name="Đường dẫn thư mục ảnh")
    password = models.TextField(verbose_name="Mật khẩu")
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo tài khoản"
    )

    class Meta:
        verbose_name = "Thông tin sinh viên"
        verbose_name_plural = "Thông tin sinh viên"

    def __str__(self):
        return self.student_name


class Classroom(models.Model):
    """Mô hình thông tin lớp học."""

    id_classroom = models.BigAutoField(primary_key=True, verbose_name="Mã lớp")
    name = models.TextField(verbose_name="Tên lớp")
    begin_date = models.DateField(verbose_name="Ngày bắt đầu")
    end_date = models.DateField(verbose_name="Ngày kết thúc")
    day_of_week_begin = models.IntegerField(verbose_name="Ngày trong tuần bắt đầu")
    begin_time = models.TimeField(verbose_name="Giờ bắt đầu")
    end_time = models.TimeField(verbose_name="Giờ kết thúc")
    id_lecturer = models.ForeignKey(
        StaffInfo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Giáo viên"
    )
    students = models.ManyToManyField(
        StudentInfo,
        through='StudentClassDetails',
        verbose_name="Sinh viên"
    )

    class Meta:
        verbose_name = "Lớp học"
        verbose_name_plural = "Lớp học"

    def __str__(self):
        return self.name


class StudentClassDetails(models.Model):
    """Mô hình đăng ký lớp học của sinh viên."""

    id_classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        verbose_name="Lớp học"
    )
    id_student = models.ForeignKey(
        StudentInfo,
        on_delete=models.CASCADE,
        verbose_name="Sinh viên"
    )

    class Meta:
        verbose_name = "Chi tiết lớp học"
        verbose_name_plural = "Chi tiết lớp học"
        unique_together = ('id_classroom', 'id_student')

    def __str__(self):
        return f"{self.id_student.student_name} - {self.id_classroom.name}"


class Attendance(models.Model):
    """Mô hình bản ghi điểm danh."""

    id_attendance = models.BigAutoField(primary_key=True, verbose_name="Mã điểm danh")
    check_in_time = models.DateTimeField(verbose_name="Thời gian vào")
    attendance_status = models.IntegerField(verbose_name="Trạng thái điểm danh")
    id_classroom = models.ForeignKey(
        'Classroom',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Lớp học"
    )
    id_student = models.ForeignKey(
        'StudentInfo',
        on_delete=models.CASCADE,
        verbose_name="Sinh viên"
    )

    class Meta:
        verbose_name = "Điểm danh"
        verbose_name_plural = "Điểm danh"
        ordering = ['-check_in_time']

    def __str__(self):
        return f"{self.id_student.student_name} - {self.check_in_time}"


class BlogPost(models.Model):
    """Mô hình bài viết blog."""

    TYPE_CHOICES = [
        ('SV', _('Sinh viên')),
        ('GV', _('Giảng viên')),
        ('ALL', _('Tất cả')),
    ]

    title = models.CharField(
        max_length=250,
        verbose_name="Tiêu đề"
    )
    body = RichTextUploadingField(verbose_name="Nội dung")
    type = models.CharField(
        max_length=15,
        choices=TYPE_CHOICES,
        default='ALL',
        verbose_name="Loại bài viết"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name="Ngày tạo"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ngày cập nhật"
    )

    class Meta:
        verbose_name = "Bài viết blog"
        verbose_name_plural = "Bài viết blog"
        ordering = ['-created_at']

    def __str__(self):
        return self.title
