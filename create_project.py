import boto3
import db_utils as db  # db 접근을 위한 모듈
import subprocess
import argparse
from os import getenv
from bson import ObjectId

# S3에서 파일 다운로드
def download_from_s3(url, local_path):
    try:
        s3 = boto3.client('s3')
        bucket_name = url.split('/')[2]
        key = '/'.join(url.split('/')[3:])
        s3.download_file(bucket_name, key, local_path)
        print(f"Downloaded {url} to {local_path}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('--project_name', type=str, required=True)
parser.add_argument('--project_id', type=str, required=True)
args = parser.parse_args()
project_name = args.project_name
project_id = args.project_id

# 1. 네임스페이스 생성
try:
    # kubectl create namespace 명령어를 실행
    result = subprocess.run(
        ["sudo", "kubectl", "create", "namespace", project_name],
        check=True,
        text=True,
        capture_output=True
    )
    # 명령어 실행 결과 출력
    print(f"Namespace '{project_name}' created successfully.")
    print("Output:", result.stdout)
except subprocess.CalledProcessError as e:
    # 명령어 실행 중 에러가 발생한 경우
    print(f"Failed to create namespace '{project_name}'.")
    print("Error:", e.stderr)
    exit(1)

# 2. 헬름 템플릿 불러와서 가져오기
client = db.connect_to_db()
collection = db.get_collection(client, os.getenv("DB_NAME"), os.getenv("COL_NAME"))

# MongoDB에서 ObjectId로 조회
try:
    project_data = collection.find_one({"_id": ObjectId(project_id)})
    if not project_data:
        print(f"No project found with id '{project_id}'.")
        exit(1)
except Exception as e:
    print(f"Error while fetching project data: {e}")
    exit(1)

template_url = project_data.get('template_url')
values_url = project_data.get('values_url')

if not template_url or not values_url:
    print("Template URL or Values URL is missing in the project data.")
    exit(1)

# 저장 경로 설정
template_file = f"/tmp/{project_name}_template.tgz"
values_file = f"/tmp/{project_name}_values.yaml"

# s3 서비스로 부터 저장된 데이터 다운
download_from_s3(template_url, template_file)
download_from_s3(values_url, values_file)

# 4. 헬름 설치 명령어 실행
try:
    result = subprocess.run(
        ["sudo", "helm", "install", project_name, template_file, "--values", values_file],
        check=True,
        text=True,
        capture_output=True
    )
    # 명령어 실행 결과 출력
    print(f"Helm chart for project '{project_name}' installed successfully.")
    print("Output:", result.stdout)
except subprocess.CalledProcessError as e:
    # 명령어 실행 중 에러가 발생한 경우
    print(f"Failed to install Helm chart for project '{project_name}'.")
    print("Error:", e.stderr)
    exit(1)
