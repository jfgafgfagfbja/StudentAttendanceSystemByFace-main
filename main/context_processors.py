# main/context_processors.py
from django.utils import timezone
from main.models import StaffInfo, StudentInfo

def account_created_time(request):
    created_time = None

    # staff
    sid = request.session.get('id_staff')
    if sid:
        try:
            staff = StaffInfo.objects.get(id_staff=sid)
            created_time = staff.created_at
        except StaffInfo.DoesNotExist:
            pass

    # student (nếu có dùng)
    if created_time is None:
        sid = request.session.get('id_student')
        if sid:
            try:
                stu = StudentInfo.objects.get(id_student=sid)
                created_time = stu.created_at
            except StudentInfo.DoesNotExist:
                pass

    # fallback
    if created_time is None:
        return {'created_time': None}

    return {'created_time': timezone.localtime(created_time)}
