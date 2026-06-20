# ERD (Entity Relationship Diagram)

Sơ đồ này được suy ra trực tiếp từ các Django models trong `main/models.py`.

```mermaid
erDiagram
    STAFFINFO {
        string id_staff PK
        text staff_name
        text email
        text phone
        text address
        date birthday
        text password
        datetime created_at
    }

    ROLE {
        int id PK
        string name UK
    }

    STAFFROLE {
        int id PK
        string staff_id FK
        int role_id FK
    }

    STUDENTINFO {
        string id_student PK
        text student_name
        text email
        text phone
        text address
        date birthday
        text PathImageFolder
        text password
        datetime created_at
    }

    CLASSROOM {
        bigint id_classroom PK
        text name
        date begin_date
        date end_date
        int day_of_week_begin
        time begin_time
        time end_time
        string id_lecturer_id FK  "nullable"
    }

    STUDENTCLASSDETAILS {
        int id PK
        bigint id_classroom_id FK
        string id_student_id FK
    }

    ATTENDANCE {
        bigint id_attendance PK
        datetime check_in_time
        int attendance_status
        bigint id_classroom_id FK "nullable"
        string id_student_id FK
    }

    BLOGPOST {
        int id PK
        string title
        text body
        string type
        datetime created_at
        datetime updated_at
    }

    STAFFINFO ||--o{ STAFFROLE : has
    ROLE ||--o{ STAFFROLE : assigned

    STAFFINFO ||--o{ CLASSROOM : teaches

    CLASSROOM ||--o{ STUDENTCLASSDETAILS : includes
    STUDENTINFO ||--o{ STUDENTCLASSDETAILS : enrolls

    CLASSROOM ||--o{ ATTENDANCE : records
    STUDENTINFO ||--o{ ATTENDANCE : marks
```

## Ghi chú
- `StaffInfo` ↔ `Role` là quan hệ N-N thông qua bảng trung gian `StaffRole`.
- `Classroom` ↔ `StudentInfo` là quan hệ N-N thông qua bảng trung gian `StudentClassDetails`.
- `Attendance.id_classroom` là FK nullable (SET_NULL), nên một bản ghi điểm danh có thể tồn tại ngay cả khi lớp bị xoá/không gán.
