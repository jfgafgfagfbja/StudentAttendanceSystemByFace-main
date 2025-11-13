# main/models.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from ckeditor_uploader.fields import RichTextUploadingField


class StaffInfo(models.Model):
    id_staff = models.CharField(max_length=10, primary_key=True)
    staff_name = models.TextField()
    email = models.TextField()
    phone = models.TextField()
    address = models.TextField()
    birthday = models.DateField()
    password = models.TextField()
    roles = models.ManyToManyField('Role', through='StaffRole', related_name='staff_role')
    # NEW: mốc tạo tài khoản
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # FIX: đúng tên field
        return self.staff_name


class Role(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class StaffRole(models.Model):
    staff = models.ForeignKey(StaffInfo, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    def __str__(self):
        # FIX: đúng tên field
        return f"{self.staff.staff_name} - {self.role.name}"


class StudentInfo(models.Model):
    id_student = models.CharField(max_length=10, primary_key=True)
    student_name = models.TextField()
    email = models.TextField()
    phone = models.TextField()
    address = models.TextField()
    birthday = models.DateField()
    PathImageFolder = models.TextField()
    password = models.TextField()
    # OPTIONAL: nếu muốn cũng hiện thời gian tạo cho SV
    created_at = models.DateTimeField(auto_now_add=True)


class Classroom(models.Model):
    id_classroom = models.BigAutoField(primary_key=True)
    name = models.TextField()
    begin_date = models.DateField()
    end_date = models.DateField()
    day_of_week_begin = models.IntegerField()
    begin_time = models.TimeField()
    end_time = models.TimeField()
    id_lecturer = models.ForeignKey(StaffInfo, on_delete=models.SET_NULL, null=True, blank=True)
    students = models.ManyToManyField(StudentInfo, through='StudentClassDetails')


class StudentClassDetails(models.Model):
    id_classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    id_student = models.ForeignKey(StudentInfo, on_delete=models.CASCADE)


class Attendance(models.Model):
    id_attendance = models.BigAutoField(primary_key=True)
    check_in_time = models.DateTimeField()
    attendance_status = models.IntegerField()
    id_classroom = models.ForeignKey('Classroom', on_delete=models.SET_NULL, null=True)
    id_student = models.ForeignKey('StudentInfo', on_delete=models.CASCADE)


class BlogPost(models.Model):
    TYPE_CHOICES = [
        ('SV', _('Sinh viên')),
        ('GV', _('Giảng viên')),
        ('ALL', _('Tất cả')),
    ]
    title = models.CharField(_("Blog Title"), max_length=250)
    body = RichTextUploadingField()
    type = models.CharField(_("Type"), max_length=15, choices=TYPE_CHOICES, default='ALL')

    def __str__(self):
        return self.title
