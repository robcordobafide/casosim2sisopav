import os
import datetime
import tarfile
import paramiko
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time

# Configuración de correo
SMTP_SERVER = "smtp.example.com"
EMAIL_ADDRESS = "your_email@example.com"
EMAIL_PASSWORD = "your_email_password"
TO_EMAIL = "recipient@example.com"

# Configuración de SSH
SSH_HOST = "192.168.162.141"
SSH_PORT = 22
SSH_USER = "user"
SSH_PASSWORD = "avc1234"
REMOTE_DIR = "/home/user/casosim2"
DAYS_OLD = 7

# Configuración local
LOCAL_BACKUP_DIR = "/home/user/backupB"

def create_backup_directory():
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    backup_path = os.path.join(LOCAL_BACKUP_DIR, f"backup_{now}")
    os.makedirs(backup_path, exist_ok=True)
    return backup_path

def get_old_files(sftp, remote_dir, days_old):
    old_files = []
    threshold = datetime.datetime.now() - datetime.timedelta(days=days_old)

    for entry in sftp.listdir_attr(remote_dir):
        if entry.filename.endswith(".log") or entry.filename.endswith(".txt"):
            file_time = datetime.datetime.fromtimestamp(entry.st_mtime)
            if file_time < threshold:
                old_files.append((entry.filename, file_time))

    return old_files

def compress_files(sftp, old_files, backup_path):
    with tarfile.open(os.path.join(backup_path, "backup.tar.gz"), "w:gz") as tar:
        for filename, file_time in old_files:
            remote_file_path = os.path.join(REMOTE_DIR, filename)
            local_file_path = os.path.join(backup_path, filename)
            sftp.get(remote_file_path, local_file_path)
            tar.add(local_file_path, arcname=filename)

def remove_old_files(sftp, old_files):
    for filename, _ in old_files:
        sftp.remove(os.path.join(REMOTE_DIR, filename))

def send_email(report):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL
    msg["Subject"] = "Informe de respaldo"
    msg.attach(MIMEText(report, "plain"))

    with smtplib.SMTP_SSL(SMTP_SERVER) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, TO_EMAIL, msg.as_string())

def backup_task():
    try:
        backup_path = create_backup_directory()

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD)
        sftp = ssh.open_sftp()

        old_files = get_old_files(sftp, REMOTE_DIR, DAYS_OLD)
        compress_files(sftp, old_files, backup_path)
        remove_old_files(sftp, old_files)

        sftp.close()
        ssh.close()

        report = f"Respaldo exitoso. {len(old_files)} archivos respaldados y eliminados."
        send_email(report)
        print(report)

    except Exception as e:
        error_message = f"Error en el respaldo: {str(e)}"
        send_email(error_message)
        print(error_message)

# Programar la tarea de respaldo

def main():
    schedule.every().day.at("02:00").do(backup_task)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
