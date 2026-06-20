# main/view/reg.py

import os
import pickle
import warnings
from datetime import datetime

import cv2
import numpy as np

try:
    import tensorflow as tf
except ImportError:
    tf = None
    
from django.utils import timezone

from main import facenet
from main.models import Classroom, Attendance, StudentInfo

# ==================  TẮT BỚT CẢNH BÁO TF  ==================
with warnings.catch_warnings():
    warnings.simplefilter("ignore")

# ==================  HÀM GHI ĐIỂM DANH  ==================


def insert_attendance(id_classroom, student_id):
    """
    Ghi điểm danh cho sinh viên student_id trong lớp id_classroom
    attendance_status:
        1: vắng
        2: đúng giờ
        3: đi trễ (>15 phút)
    """
    try:
        classroom = Classroom.objects.get(pk=id_classroom)
        
        now = timezone.now()
        # thời gian bắt đầu buổi học (theo ngày hôm nay) - phải dùng aware datetime
        begin_dt = timezone.make_aware(
            datetime.combine(now.date(), classroom.begin_time)
        )

        time_diff = (now - begin_dt).total_seconds()

        if time_diff > 900:  # > 15 phút
            attendance_status = 3  # trễ
        else:
            attendance_status = 2  # đúng giờ

        # Convert student_id to int if it's string
        if isinstance(student_id, str):
            student_id = int(student_id)
        
        try:
            student_info = StudentInfo.objects.get(id_student=student_id)

            attendance, created = Attendance.objects.get_or_create(
                id_student=student_info,
                id_classroom=classroom,
                check_in_time__date=now.date(),
                defaults={
                    'check_in_time': now,
                    'attendance_status': attendance_status,
                },
            )

            # nếu đã có record trước đó thì cập nhật lại
            if not created:
                attendance.check_in_time = now
                attendance.attendance_status = attendance_status
                attendance.save()

            print(
                f"✅ Attendance recorded | Status: {attendance_status} | "
                f"StudentID: {student_id} | Class: {id_classroom}"
            )

        except StudentInfo.DoesNotExist:
            print(f"❌ Student with ID {student_id} does not exist in DB")
        except Exception as e:
            print(f"❌ Error recording attendance: {e}")
            
    except Classroom.DoesNotExist:
        print(f"❌ Classroom with ID {id_classroom} does not exist")
    except Exception as e:
        print(f"❌ Fatal error in insert_attendance: {e}")


# ==================  VẼ THANH TIẾN TRÌNH  ==================


def draw_progress_bar(frame, progress, x, y, w, h, required_frames=3):
    """
    progress: current_frame_count / required_frames (0.0 -> 1.0)
    """
    bar_width = 150
    bar_height = 20
    bar_x = x
    bar_y = y - 25

    # nền đen
    cv2.rectangle(
        frame,
        (bar_x, bar_y),
        (bar_x + bar_width, bar_y + bar_height),
        (0, 0, 0),
        -1,
    )

    filled_width = int(bar_width * min(progress, 1.0))
    cv2.rectangle(
        frame,
        (bar_x, bar_y),
        (bar_x + filled_width, bar_y + bar_height),
        (0, 255, 0),
        -1,
    )

    percent = int(min(progress, 1.0) * 100)
    cv2.putText(
        frame,
        f"{percent}%",
        (bar_x + 5, bar_y + bar_height - 5),
        cv2.FONT_HERSHEY_COMPLEX_SMALL,
        0.7,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )


# ==================  HÀM CHÍNH: NHẬN DIỆN & STREAM VIDEO  ==================


def main(id_subject):
    """
    id_subject: id_classroom truyền từ view
    Dùng Facenet + SVM (KHÔNG dùng Anti-Spoof vì nó bị hang).
    Chỉ cần REQUIRED_FRAMES frame liên tiếp nhận cùng 1 tên => điểm danh.
    """
    print(f"\n{'='*60}")
    print(f"🎬 Starting Face Recognition for Classroom ID: {id_subject}")
    print(f"{'='*60}\n")

    INPUT_IMAGE_SIZE = 160
    CLASSIFIER_PATH = 'main/Models/facemodel.pkl'
    FACENET_MODEL_PATH = 'main/Models/20180402-114759.pb'
    REQUIRED_FRAMES = 3  # chỉ cần 3 frame liên tiếp

    # ----- Load classifier -----
    try:
        with open(CLASSIFIER_PATH, 'rb') as file:
            model, class_names = pickle.load(file)
        print(f"✅ Custom Classifier loaded successfully")
        print(f"📊 Trained for {len(class_names)} students: {class_names}\n")
    except FileNotFoundError:
        print("❌ Model file not found! Please train the model first.")
        return None

    # ----- Load Facenet model -----
    facenet.load_model(FACENET_MODEL_PATH)
    graph = tf.compat.v1.get_default_graph()
    images_placeholder = graph.get_tensor_by_name("input:0")
    embeddings = graph.get_tensor_by_name("embeddings:0")
    phase_train_placeholder = graph.get_tensor_by_name("phase_train:0")

    # ----- Load Haar Cascade (THAY THẾ anti-spoof) -----
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    # ----- Camera -----
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    current_face_name = ""
    current_face_progress = 0  # số frame liên tiếp cùng tên
    recognized_names = []      # đã điểm danh rồi thì không điểm nữa

    sess = tf.compat.v1.Session(graph=graph)

    try:
        while cap.isOpened():
            isSuccess, frame = cap.read()
            if not isSuccess:
                break

            # Resize for faster processing
            frame = cv2.resize(frame, (640, 480))
            
            # Detect faces using Haar Cascade (KHÔNG DÙNG anti-spoof)
            faces = face_cascade.detectMultiScale(frame, 1.3, 5)

            if len(faces) > 0:
                x, y, w, h = faces[0]
                face_width = w
                face_height = h
                
                # Crop face region
                cropped = frame[y:y+face_height, x:x+face_width]
                if cropped is not None and cropped.size > 1600:
                    try:
                        # Resize và prewhiten
                        scaled = cv2.resize(
                            cropped,
                            (INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE),
                            interpolation=cv2.INTER_CUBIC,
                        )
                        scaled = facenet.prewhiten(scaled)
                        scaled_reshape = scaled.reshape(
                            -1, INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE, 3
                        )
                        feed_dict = {
                            images_placeholder: scaled_reshape,
                            phase_train_placeholder: False,
                        }
                        emb_array = sess.run(embeddings, feed_dict=feed_dict)
                        predictions = model.predict_proba(emb_array)
                        best_class_indices = np.argmax(predictions, axis=1)
                        best_class_probabilities = predictions[
                            np.arange(len(best_class_indices)), best_class_indices
                        ]
                        best_name = class_names[best_class_indices[0]]

                        # ----- NGƯỠNG TIN CẬY -----
                        if best_class_probabilities > 0.9:
                            # Nếu sv này chưa điểm danh
                            if best_name not in recognized_names:
                                # Đếm số frame liên tiếp có cùng tên
                                if current_face_name == best_name:
                                    current_face_progress += 1
                                else:
                                    current_face_name = best_name
                                    current_face_progress = 1

                                progress_ratio = current_face_progress / REQUIRED_FRAMES
                                draw_progress_bar(
                                    frame,
                                    progress_ratio,
                                    x, y, x+face_width, y+face_height,
                                    required_frames=REQUIRED_FRAMES,
                                )

                                # Vẽ khung + text (dùng ASCII để tránh encoding issue)
                                cv2.rectangle(frame, (x, y), (x+face_width, y+face_height), (0, 255, 0), 2)
                                text_x = x
                                text_y = y + face_height + 20
                                
                                # Display student ID (không dùng unicode)
                                display_text = f"ID: {best_name}"
                                confidence_text = f"Conf: {best_class_probabilities[0]:.2f}"
                                
                                cv2.putText(
                                    frame,
                                    display_text,
                                    (text_x, text_y),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.9,
                                    (0, 255, 0),
                                    2,
                                    cv2.LINE_AA,
                                )
                                cv2.putText(
                                    frame,
                                    confidence_text,
                                    (text_x, text_y + 25),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7,
                                    (0, 255, 0),
                                    1,
                                    cv2.LINE_AA,
                                )

                                # ĐỦ 3 FRAME LIÊN TIẾP => ĐIỂM DANH
                                if current_face_progress >= REQUIRED_FRAMES:
                                    recognized_names.append(best_name)
                                    print(f"\n{'='*60}")
                                    print(f"✅ RECOGNITION CONFIRMED!")
                                    print(f"   Student ID: {best_name}")
                                    print(f"   Classroom ID: {id_subject}")
                                    print(f"   Confidence: {best_class_probabilities[0]:.4f}")
                                    print(f"   Frames matched: {current_face_progress}")
                                    print(f"{'='*60}\n")
                                    
                                    # Ghi điểm danh
                                    insert_attendance(id_subject, best_name)
                                    print(f"✅ INSERT ATTENDANCE COMPLETED FOR {best_name}\n")
                            else:
                                # Đã điểm danh rồi
                                message = f"ID {best_name}: Already checked"
                                cv2.rectangle(frame, (x, y), (x+face_width, y+face_height), (0, 0, 255), 2)
                                cv2.putText(
                                    frame,
                                    message,
                                    (x, y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7,
                                    (0, 0, 255),
                                    2,
                                    cv2.LINE_AA,
                                )
                        else:
                            # Không đủ tin cậy => UNKNOWN
                            current_face_name = "UNKNOWN"
                            current_face_progress = 0
                            cv2.rectangle(frame, (x, y), (x+face_width, y+face_height), (0, 165, 255), 2)
                            text_x = x
                            text_y = y + face_height + 20
                            cv2.putText(
                                frame,
                                "UNKNOWN (Low Confidence)",
                                (text_x, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (0, 165, 255),
                                2,
                                cv2.LINE_AA,
                            )
                    except Exception as e:
                        print(f"Error processing face: {e}")
                        continue

            # ----- ENCODE & STREAM -----
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame_bytes = buffer.tobytes()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
            )

    finally:
        sess.close()
        cap.release()
        cv2.destroyAllWindows()
