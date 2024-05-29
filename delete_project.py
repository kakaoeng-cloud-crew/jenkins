import db_utils as db  # db 접근을 위한 모듈
import subprocess
import argparse
from os import getenv
from bson import ObjectId
import boto3

parser = argparse.ArgumentParser()
parser.add_argument('--project_name', type=str, required=True)
parser.add_argument('--project_id', type=str, required=True)
args = parser.parse_args()
project_name = args.project_name
project_id = args.project_id

# 1. 헬름 삭제하기
try:
    result = subprocess.run(
        ["sudo", "helm", "delete", project_name, "--namespace", project_name],
        check=True,
        text=True,
        capture_output=True
    )
    print(f"Helm chart for project '{project_name}' deleted successfully.")
    print("Output:", result.stdout)
except subprocess.CalledProcessError as e:
    # 명령어 실행 중 에러가 발생한 경우
    print(f"Failed to delete Helm chart for project '{project_name}'.")
    print("Error:", e.stderr)
    exit(1)

# 2. k8s 네임스페이스 삭제하기
try:
    result = subprocess.run(
        ["sudo", "kubectl", "delete", 'namespace', project_name],
        check=True,
        text=True,
        capture_output=True
    )
    print(f"kubernetes namespace '{project_name}' deleted successfully.")
    print("Output:", result.stdout)
except subprocess.CalledProcessError as e:
    # 명령어 실행 중 에러가 발생한 경우
    print(f"Failed to delete namespace for k8s '{project_name}'.")
    print("Error:", e.stderr)
    exit(1)

# 3. 데이터베이스 갱신
try:
    client = db.connect_to_db()
    collection = db.get_collection(client, getenv("DB_NAME"), getenv("COL_NAME"))
    # ObjectId로 변환하여 MongoDB에서 프로젝트 삭제
    result = collection.delete_one({"_id": ObjectId(project_id)})
    if result.deleted_count:
        # 프로젝트가 성공적으로 삭제된 경우
        print("Project successfully deleted from database")
    else:
        # 프로젝트가 없는 경우 404 에러 반환
        print("Project not found in database")
        exit(1)
except Exception as e:
    print(f"Error while updating database: {e}")
    exit(1)
    
# 4. s3 서비스에 있는 데이터 삭제하기
s3 = boto3.client('s3')
bucket_name = 'cc-helm-templates'
objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=f"projects/{project_id}/")["Contents"]
for obj in objects:
    key = obj["Key"]
    s3.delete_object(Bucket=bucket_name, Key=key)

s3.delete_object(Bucket=bucket_name, Key=f"projects/{project_id}/")
print(f"Folder '{project_id}' successfully deleted from S3")

# 5. /helm/{project_id} 디렉토리 삭제하기
try:
    path = f"/helm/{project_id}"
    result = subprocess.run(
        ["sudo", "rm", "-rf", path],
        check=True,
        text=True,
        capture_output=True
    )
    print(f"Local directory '{path}' deleted successfully.")
    print("Output:", result.stdout)
except subprocess.CalledProcessError as e:
    print(f"Failed to delete local directory '{local_helm_directory}'.")
    print("Error:", e.stderr)
    exit(1)
